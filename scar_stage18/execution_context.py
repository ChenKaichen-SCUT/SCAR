"""PublicRuleState queries, candidate checks and the bounded model fact view."""
import copy
import json
from scar_stage16.state import PublicRuleState
from scar_v3.state import parse_action
from .config import SUMMARY_CHARACTERS, SUMMARY_RECORDS


def build(controller):
    view = PublicRuleState(controller.legacy_copy())
    goal = parse_action(controller.target).target
    pending, seen, recipes, execution = [goal], set(), {}, {}
    while pending:
        node = pending.pop(0)
        if node in seen:
            continue
        seen.add(node)
        recipes[node] = view.get_recipe(node)
        execution[node] = view.get_execution_status(node)
        pending.extend(view.get_known_dependencies(node)['dependencies'])
    return dict(goal=view.get_goal_status(), recipes=recipes, execution=execution,
        available=view.get_available_materials(),
        failures=copy.deepcopy(controller.attempt_log[-8:]),
        consequence_evidence=copy.deepcopy(controller.consequences.records[-12:]),
        scope='disclosed dependency chain only; unknown leaves are not certified raw materials',
        current_step=controller.table.state.get('step'))


def assess(controller, action, context=None):
    # Deliberately call the inherited condition query, not this overlay again.
    from scar_stage10.controller import ResourceController
    result = copy.deepcopy(ResourceController.assess(controller, action))
    p = parse_action(action or '')
    if p.verb == 'craft':
        rule = controller.table.recipes.get(p.target, {})
        public_rule = (context or {}).get('recipes', {}).get(p.target)
        quantities = (public_rule['quantities']['value'] if public_rule and public_rule['quantities']['status'] == 'KNOWN'
                      else rule.get('quantities'))
        result['execution_context_consulted'] = bool(public_rule)
        for item, nominal in (quantities or {}).items():
            own = controller.ownership(item)
            status = 'SUPPORTED' if own['lower_bound'] >= nominal else 'REJECT' if own['exact'] else 'UNKNOWN'
            result['conditions'].append(dict(kind='nominal_single_craft_material', item=item, status=status,
                evidence=dict(nominal=nominal, owned=own, evidence_ids=rule.get('evidence_ids', [])),
                scope='single nominal prerequisite only; batch consumption UNKNOWN'))
        result['conditions'].append(dict(kind='station_completeness_and_batch', status='UNKNOWN',
            evidence='P1 only knows disclosed station subset; unchanged S1 crafting batch'))
    risk = controller.consequences.check(controller, action)
    if risk['evidence']:
        result['conditions'].append(dict(kind='observed_consequence', status=risk['status'], evidence=risk))
    result['status'] = ('REJECT' if any(c['status'] == 'REJECT' for c in result['conditions']) else
                        'UNKNOWN' if any(c['status'] == 'UNKNOWN' for c in result['conditions']) else 'SUPPORTED')
    result['risk'] = risk
    goal = parse_action(controller.target).target
    relevant = p.target in controller._all_needed(goal)
    positive = False
    if result['status'] != 'REJECT' and relevant:
        if p.verb == 'craft':
            r = controller.table.recipes.get(p.target, {})
            positive = bool(r.get('ingredients') and r.get('quantities')) and all(
                controller.ownership(n)['lower_bound'] >= v for n, v in r['quantities'].items())
        elif p.verb in ('pick up', 'take out', 'store'):
            positive = controller.ownership(p.target)['lower_bound'] < (controller.amount if p.target == goal else controller.queue_needs.get(p.target, 1))
    result['known_goal_progress'] = bool(positive)
    result['complete_feasibility_certified'] = False
    return result


def render(facts, controller, obs):
    """Keep the STM5/system prompt contract and 48/6000 ceiling.

    Deterministic ordering of already-known execution evidence only; this does
    not assign scores to unknown objects or choose exploration destinations.
    """
    old_text, old = facts.render(obs)
    context = build(controller)
    available = facts.records(obs)
    related = set(context['recipes'])
    priority = []
    goal = context['goal']['goal']
    now = context['current_step']
    def add(kind, key, value, step=now, scope='current public evidence; unknown is not false'):
        priority.append(dict(id=kind+':'+key, kind=kind, key=key, value=value, step=step, scope=scope))
    add('goal', goal, {k: context['goal'][k] for k in ('goal','required','owned','completion_status')})
    # Show current blockers before a long collection of unrelated recipes.
    for node, ex in context['execution'].items():
        if node == goal or ex['blockers']:
            compact=[]
            for b in ex['blockers']:
                compact.append({k:b[k] for k in ('kind','material','item','nominal_required','owned','status') if k in b})
            add('execution', node, dict(blockers=compact, retry_allowed=ex['retry_allowed'],
                unknown_conditions=ex['unknown_conditions']))
    risks = [r for r in controller.consequences.records if r.get('explicit_carrying_damage')]
    distinct=[];risk_keys=set()
    for r in risks[::-1]:
        key=(r.get('risk_item'),r['after']['location'])
        if key not in risk_keys:
            risk_keys.add(key);distinct.append(r)
    for r in distinct[:3]:
        excerpt='\n'.join(line for line in r['feedback'].splitlines() if 'draining ' in line or 'Carrying ' in line)
        add('consequence', r['id'], dict(item=r.get('risk_item'), attribution=r['item_attribution'],
            location=r['after']['location'], equipment=r['after']['equipment'],
            observed_count=r['observed_affected_count'], threshold=r['threshold'],
            hp_loss=r['health_loss'], evidence=excerpt, cessation_step=(r.get('cessation_evidence') or {}).get('step'),
            invalidation=r['invalidation']), r['step'], 'conditional observed carrying state, not a universal item ban')
    # Pull relevant P1 records from the full public view even if the original
    # auxiliary facts table evicted them. Evidence remains in controller state.
    for node, r in context['recipes'].items():
        if r['materials']['status'] == 'KNOWN':
            add('recipe', node, dict(ingredients=r['materials']['value'], quantities=r['quantities'],
                stations=r['stations'], evidence_ids=r['evidence_ids'],
                unknown_conditions=r['missing_conditions']), r['first_observed_step'],
                'P1 public recipe; station completeness and batch consumption UNKNOWN')
    priority.extend(r for r in available if r['kind'] in ('current','container','failure','uncertainty'))
    priority.extend(r for r in available if r['key'] in related)
    priority.extend(available)
    # A long chain or a verbose failure cannot push out the target recipe.
    def rank(r):
        if r['kind']=='goal':return 0
        if r['kind']=='recipe' and r['key']==goal:return 1
        if r['kind']=='execution' and r['key']==goal:return 2
        if r['kind']=='consequence':return 3
        if r['kind']=='execution' and r['key'] in controller.queue[:1]:return 4
        if r['kind'] in ('current','container'):return 5
        if r['kind']=='failure':return 6
        if r['kind']=='recipe' and r['key'] in related:return 7
        if r['kind']=='uncertainty':return 8
        return 9
    priority.sort(key=rank)
    prefix = old_text.split('\n', 1)[0]+'\n'
    chosen, seen = [], set()
    for record in priority:
        if record['id'] in seen:
            continue
        line = json.dumps(record, ensure_ascii=False, separators=(',', ':'))
        text = prefix+'\n'.join(json.dumps(r, ensure_ascii=False, separators=(',', ':')) for r in chosen)
        if len(chosen) < SUMMARY_RECORDS and len(text)+len(line)+1 <= SUMMARY_CHARACTERS:
            chosen.append(record); seen.add(record['id'])
    text = prefix+'\n'.join(json.dumps(r, ensure_ascii=False, separators=(',', ':')) for r in chosen)
    old_ids = [r['id'] for r in old['records']]
    return text, dict(records=chosen, characters=len(text), utf8_bytes=len(text.encode()),
        available_record_ids=list(dict.fromkeys(r['id'] for r in priority)),
        capacity_records=SUMMARY_RECORDS, capacity_characters=SUMMARY_CHARACTERS, extra_model_calls=0,
        old_summary=old, old_text=old_text, added_record_ids=sorted(seen-set(old_ids)),
        omitted_old_record_ids=sorted(set(old_ids)-seen), new_order=[r['id'] for r in chosen],
        scope='bounded evidence selection changes input; proposals need not match Stage17'), context
