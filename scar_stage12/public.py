"""Public candidate construction and a common, bounded execution procedure.

No engine, evaluation labels, case IDs, hidden recipes or future rows enter here.
Hypotheses are text annotations only and are never accepted by ResourceTable.
"""
import copy

from scar.io import digest
from scar_sequence.planner import q
from scar_stage10.controller import REJECT
from scar_stage11.controller import adapted
from scar_v3.state import parse_action

CANDIDATE_LIMIT = 16
PLAN_LIMIT = 4
KINDS = ['unconnected_visible', 'fresh_product', 'confirmed_inspect',
         'known_craft', 'known_location', 'other_inspect', 'general_exploration', 'primitive']


def controller(state, obs):
    obj = adapted(copy.deepcopy(state), 'E0')
    obj.table.observe(obs)
    return obj


def confirmed(ctrl):
    pending = [parse_action(ctrl.target).target]; seen = set()
    while pending and len(seen) < 64:
        name = pending.pop(0)
        if not name or name in seen:
            continue
        seen.add(name)
        pending.extend(ctrl.table.recipes.get(name, {}).get('ingredients', []))
    return seen


def descriptor(kind, target, category, first_action=None, **fields):
    obj = dict(kind=kind, target=target, category=category, **fields)
    if first_action:
        obj['first_action'] = first_action
    obj['id'] = 'c_'+digest([kind, target, first_action, fields.get('location')])[:12]
    return obj


def next_action(ctrl, candidate, completed=()):
    """Up to one public-supported primitive; caller caps the whole chain at4.

    Existing S1 acquisition, station search and batch rules are reused. No
    recursive production planner, guessed dependency or quantity optimiser.
    """
    t = ctrl.table; name = candidate['target']; kind = candidate['kind']
    if not completed and candidate.get('first_action'):
        return candidate['first_action']
    visible = ctrl.visible()
    if kind == 'inspect':
        return None if completed else 'inspect '+q(name)
    if kind == 'primitive':
        return None if completed else candidate['first_action']
    if kind == 'visit':
        if t.state.get('location') != candidate['location']:
            return ctrl._move(candidate['location'])
        if name in visible and name not in t.inspected:
            return 'inspect '+q(name)
        return None
    if kind == 'general':
        if not completed:
            return ctrl._move(name)
        options = sorted(visible-set(t.inspected), key=lambda x: digest(['general', x]))
        return 'inspect '+q(options[0]) if options else None
    if kind != 'craft':
        return None
    # A successful production must be witnessed; never infer it from intent.
    made = any(parse_action(r['action']).verb == 'craft' and
               'successfully crafted' in r['feedback'] for r in completed)
    if made:
        return 'inspect '+q(name) if name in visible and name not in t.inspected else None
    if name in visible:
        return 'inspect '+q(name) if name not in t.inspected else None
    recipe = t.recipes.get(name, {}); deps = recipe.get('ingredients', [])
    if not deps:
        return None
    protect = confirmed(ctrl) | set(deps)
    for dep in deps:
        need = (recipe.get('quantities') or {}).get(dep, ctrl.quotas.get(name, 1))
        if (t.count(dep) or 0) < need:
            return ctrl._acquire(dep, need, protect)
    # _station may reuse S1's bounded broad exploration if location is unknown.
    station = ctrl._station(name)
    if station:
        return station
    action = ctrl._batch_action('craft 1 '+q(name))
    return action if ctrl.assess(action)['status'] != REJECT else None


def primitive_candidate(action):
    """The same adapter is used for rule choices and free LLM proposals.

    A craft proposal may be followed by inspection of its actual product.
    Other primitive proposals get no invented intent or oracle suffix.
    """
    p = parse_action(action)
    kind = 'craft' if p.verb == 'craft' else 'inspect' if p.verb == 'inspect' else 'primitive'
    return descriptor(kind, p.target, 'primitive', first_action=action,
                      evidence='public method proposal; exact first action retained')


def candidate_set(state, obs, rule_actions=()):
    ctrl = controller(state, obs); t = ctrl.table; nodes = confirmed(ctrl)
    visible = ctrl.visible(); produced = set(ctrl.quantity_facts.produced)
    pool = {}
    def add(c):
        c['confirmed_connection'] = c['target'] in nodes
        # Evaluate feasibility using public information only; UNKNOWN is allowed.
        a = next_action(controller(state, obs), c)
        if a is None:
            return
        c['next_action'] = a
        c['public_condition'] = ctrl.assess(a)['status']
        pool[c['id']] = c
    for name in sorted(visible):
        if name in t.inspected:
            continue
        category = ('fresh_product' if name in produced else 'confirmed_inspect' if name in nodes
                    else 'unconnected_visible')
        add(descriptor('inspect', name, category, evidence='currently observed, not previously inspected'))
    # Goal/necessary items visible now may be re-inspected if their relation is
    # still unknown; repeated inspection is explicitly marked, not concealed.
    for name in sorted(nodes & visible & set(t.inspected)):
        if not t.recipes.get(name, {}).get('ingredients'):
            add(descriptor('inspect', name, 'other_inspect', evidence='visible unresolved public prerequisite; repeat'))
    supplies = set(visible)
    for location, data in t.places.items():
        if location == t.state.get('location') or t.path(location):
            supplies.update(n for n, count in data['objects'].items() if count > 0)
    for name, recipe in sorted(t.recipes.items()):
        deps = recipe.get('ingredients', [])
        if not deps or name in produced or name in visible:
            continue
        if not all(dep in supplies or (t.count(dep) or 0) > 0 for dep in deps):
            continue
        add(descriptor('craft', name, 'known_craft', ingredients=deps,
                       stations=recipe.get('stations', 'UNKNOWN'),
                       evidence='observed recipe and potentially accessible inputs; downstream connection may be unknown'))
    for location, data in sorted(t.places.items()):
        if location == t.state.get('location') or not t.path(location):
            continue
        for name, amount in sorted(data['objects'].items()):
            if amount > 0 and name not in t.inspected:
                add(descriptor('visit', name, 'known_location', location=location,
                               evidence='historically seen object; current presence requires reconfirmation'))
    for location in t.state.get('neighbors') or []:
        if location not in t.places:
            add(descriptor('general', location, 'general_exploration', evidence='public neighbor not yet visited'))
    # Keep exact frozen rule actions in the common menu; do not expose which
    # method proposed them. They receive exactly the same branch executor.
    anchors = []
    for action in rule_actions:
        c = primitive_candidate(action); add(c); anchors.append(c['id'])
    if not pool:
        add(primitive_candidate('wait'))
    kept = list(dict.fromkeys(anchors))
    buckets = {kind: sorted((c for c in pool.values() if c['category'] == kind and c['id'] not in kept),
                           key=lambda c: digest(['crop12', c['kind'], c['target'], c.get('location')])) for kind in KINDS}
    # Round-robin representation, without goal/name similarity scoring.
    for i in range(max(map(len, buckets.values()), default=0)):
        for kind in KINDS:
            if i < len(buckets[kind]) and len(kept) < CANDIDATE_LIMIT:
                kept.append(buckets[kind][i]['id'])
    # Presentation order is unrelated to rank/type; identical for all queries.
    retained = sorted((pool[k] for k in kept), key=lambda c: digest(['show12', c['id']]))
    dropped = sorted((c for k, c in pool.items() if k not in kept), key=lambda c: c['id'])
    return retained, dropped


def public_view(ctrl):
    t = ctrl.table; nodes = confirmed(ctrl)
    return {'objective': ctrl.objective, 'target_action': ctrl.target,
            'current': {k: t.state.get(k) for k in ['location', 'hands', 'ground', 'equipment', 'neighbors']},
            'confirmed_recipe_relations': {n: {'ingredients': r.get('ingredients') or 'UNKNOWN',
                                             'stations': r.get('stations', 'UNKNOWN')} for n, r in t.recipes.items()},
            'containers': t.containers, 'known_locations': t.places,
            'inspected': t.inspected, 'produced': ctrl.quantity_facts.produced,
            'recent_attempts': ctrl.attempt_log[-8:],
            'unresolved_public_nodes': sorted(n for n in nodes if not t.recipes.get(n, {}).get('ingredients')),
            'uncertainty': 'Missing relations are UNKNOWN, not impossible. Production history is not possession. No semantic hypothesis is a confirmed recipe.'}
