"""Public-only fixed coverage rules. No case IDs, native labels, model calls or engine.

Inputs are whitelisted in prepare.py. A public unknown leaf is NOT evidence of a
hidden recipe. Costs are conservative planning estimates, not actual branch costs.
"""
from scar.io import digest
from scar_stage12.public import controller, confirmed, next_action, primitive_candidate
from scar_v3.state import parse_action

DROUGHT = 3
COOLDOWN = 4
RESERVE = 2
LIMIT = 4


def intent(c):
    # Travel is preparation for inspecting the same named object. Primitive
    # transport stays distinct. Craft batch aliases share an exploration intent,
    # but their native outcomes are never merged or substituted.
    if c['kind'] in {'visit', 'inspect'}:
        return ('inspect', c['target'])
    if c['kind'] == 'craft':
        return ('craft_then_inspect', c['target'])
    return (c['kind'], c.get('first_action', c['target']))


def entries(ctrl, menu, history):
    t = ctrl.table; nodes = confirmed(ctrl)
    stations = {n for r in t.recipes.values() for n in r.get('stations', [])}
    rows = []
    for order, c in enumerate(menu):
        name = c['target']; records = [h for h in history if parse_action(h['action']).target == name]
        inspected = name in t.inspected
        produced = name in ctrl.quantity_facts.produced
        raw = (c['kind'] in {'inspect', 'visit'} and name not in nodes and not produced
               and not t.recipes.get(name, {}).get('ingredients')
               and name not in stations and name not in t.containers)
        states = []
        if inspected:
            inspection_records = [h for h in records if parse_action(h['action']).verb == 'inspect']
            states.append('inspected_with_public_information' if any(h['new_recipes'] for h in inspection_records) else 'inspected_no_new_public_recipe' if inspection_records else 'inspected_prior_information_unknown')
        if produced and not inspected: states.append('produced_uninspected')
        if any(h['blocked'] for h in records): states.append('previous_blocked_attempt')
        if raw and not inspected: states.append('unconnected_uninspected_entry')
        if name in nodes: states.append('public_necessary_node')
        if not states: states.append('other_public_direction')
        action = next_action(ctrl, c)
        status = ctrl.assess(action)['status'] if action else 'REJECT'
        # Bounded estimate: inspect1; historical route+inspect; craft2 plus one
        # acquisition per missing input and known station route. Unknown route
        # has no finite estimate, never guessed from native state.
        cost = None
        if c['kind'] == 'inspect': cost = 1
        if c['kind'] == 'visit':
            path = t.path(c['location'])
            cost = len(path)+1 if path else (1 if c['location'] == t.state['location'] else None)
        if c['kind'] == 'craft' and t.recipes.get(name, {}).get('ingredients'):
            recipe = t.recipes[name]; required = recipe.get('stations')
            if required:
                paths = [([] if loc == t.state['location'] else t.path(loc)) for loc, data in t.places.items()
                         if all(data['objects'].get(n, 0) for n in required)]
                paths = [p for p in paths if p is not None]
                if paths:
                    missing = sum(ctrl.ownership(n)['lower_bound'] <= 0 for n in recipe['ingredients'])
                    cost = 2 + missing + min(map(len, paths))
        rows.append({'candidate_id': c['id'], 'intent': list(intent(c)), 'target': name,
            'entry_states': states, 'last_attempt_index': records[-1]['index'] if records else None,
            'last_feedback': records[-1]['feedback'] if records else None,
            'attempts': len(records), 'inspected': inspected, 'produced': produced,
            'unconnected_entry': raw and not inspected, 'confirmed_necessary': name in nodes,
            'public_recipe_support': bool(t.recipes.get(name, {}).get('ingredients')),
            'station': name in stations, 'container': name in t.containers,
            'first_action': action, 'condition': status, 'estimated_actions': cost,
            'estimate_is_not_native_cost_or_guaranteed_upper_bound': True, 'menu_order': order})
    return rows


def suffix_count(history, key):
    n = 0
    for h in reversed(history):
        if h[key]: break
        n += 1
    return n


def same_known_component(ctrl, history):
    if len(history) < DROUGHT: return False
    targets = [parse_action(h['action']).target for h in history[-DROUGHT:]]
    graph = {}
    for product, recipe in ctrl.table.recipes.items():
        for dep in recipe.get('ingredients', []):
            graph.setdefault(product, set()).add(dep); graph.setdefault(dep, set()).add(product)
    if not targets or targets[0] not in graph: return False
    seen = set(); todo = [targets[0]]
    while todo:
        x = todo.pop()
        if x in seen: continue
        seen.add(x); todo.extend(graph.get(x, ()))
    return all(x in seen for x in targets)


def decide(public):
    ctrl = controller(public['controller'], public['observation'])
    menu = public['candidates']; history = public['history']; t = ctrl.table
    nodes = confirmed(ctrl); baseline = primitive_candidate(public['s1_action'])['id']
    assert baseline in {c['id'] for c in menu}
    ledger = entries(ctrl, menu, history); by = {r['candidate_id']: r for r in ledger}
    incomplete = any(not t.recipes.get(n, {}).get('ingredients') and n not in t.inspected for n in nodes)
    # Even an inspected final/intermediate can have no disclosed own recipe.
    unresolved_goal = not t.recipes.get(parse_action(ctrl.target).target, {}).get('ingredients')
    incomplete = incomplete or unresolved_goal
    drought = suffix_count(history, 'new_public_necessary_recipes')
    stalled = suffix_count(history, 'progress')
    recent_coverage = any(h['unconnected_inspection'] for h in history[-COOLDOWN:])
    budget = min(LIMIT, public['remaining_actions']-RESERVE)
    feasible = [r for r in ledger if r['condition'] != 'REJECT' and not r['inspected']
                and r['estimated_actions'] is not None and r['estimated_actions'] <= budget
                and not r['station'] and not r['container']
                and (r['last_attempt_index'] is None or not any(h['blocked'] for h in history if parse_action(h['action']).target == r['target']))]
    def first(rows):
        return min(rows, key=lambda r: (r['attempts'], r['estimated_actions'], r['menu_order']))['candidate_id'] if rows else baseline
    gate1 = incomplete and drought >= DROUGHT and same_known_component(ctrl, history) and not recent_coverage
    gate2 = incomplete and stalled >= DROUGHT and not recent_coverage
    c1 = first([r for r in feasible if r['unconnected_entry']]) if gate1 else baseline
    c2 = first([r for r in feasible if r['unconnected_entry'] or r['produced'] or r['public_recipe_support']]) if gate2 else baseline
    p = parse_action(public['s1_action']); target = parse_action(ctrl.target).target
    # Reuse S1's public progress predicate; it accepts UNKNOWN quantities but
    # requires disclosed ingredients/positive ownership and no known rejection.
    protect = (ctrl.base_progress(public['s1_action'])
               or (p.verb == 'inspect' and p.target not in t.inspected
                   and (p.target in nodes or p.target in ctrl.quantity_facts.produced))
               or (p.target == target and p.verb in {'craft','pick up','store','take out'}
                   and ctrl.assess(public['s1_action'])['status'] != 'REJECT'))
    c3 = baseline if protect else (c1 if c1 != baseline else c2)
    j3 = public['j3_selected']; j = by[j3]
    # One predeclared LLM supplement; no learned/hand-fitted fusion.
    llm_gate = (gate2 and j['last_attempt_index'] is None and not j['inspected']
                and j['public_recipe_support'] and j['condition'] != 'REJECT'
                and j['estimated_actions'] is not None and j['estimated_actions'] <= budget and not protect)
    features = {'incomplete_public_dependencies': bool(incomplete),
        'unknown_goal_recipe': unresolved_goal, 'public_necessary_knowledge_drought': drought,
        'no_public_progress_streak': stalled, 'same_known_component_last3': same_known_component(ctrl, history),
        'recent_unconnected_inspection_last4': recent_coverage,
        'uninspected_independent_entry_intents': len({tuple(r['intent']) for r in ledger if r['unconnected_entry']}),
        'fresh_uninspected_product': any(r['produced'] and not r['inspected'] for r in ledger),
        'j3_previously_attempted': j['last_attempt_index'] is not None,
        'j3_repeat_inspection_or_station': j['station'] or j['inspected'],
        'j3_public_recipe_support': j['public_recipe_support'],
        'j3_estimated_actions': j['estimated_actions'], 's1_estimated_actions': by[baseline]['estimated_actions'],
        's1_public_execution_protected': bool(protect), 'C1_trigger': bool(gate1), 'C2_trigger': bool(gate2),
        'L_trigger': bool(llm_gate), 'remaining_actions': public['remaining_actions']}
    return {'choices': {'C0': baseline, 'C1': c1, 'C2': c2, 'C3': c3, 'L': j3 if llm_gate else baseline},
            'features': features, 'entry_ledger': ledger,
            'public_input_digest': digest(public), 'single_supplement_max_actions': LIMIT}
