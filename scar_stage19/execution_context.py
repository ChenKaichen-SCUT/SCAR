"""Present only attested public evidence; no negative-consequence memory."""
import copy
import json
from scar_stage10.controller import ResourceController
from scar_v3.state import parse_action
from .config import SUMMARY_RECORDS, SUMMARY_CHARACTERS


def assess(controller, action):
    result = copy.deepcopy(ResourceController.assess(controller, action))
    p = parse_action(action or '')
    if p.verb == 'craft':
        rule = controller.table.recipes.get(p.target, {})
        for item, nominal in (rule.get('quantities') or {}).items():
            own = controller.ownership(item)
            status = 'SUPPORTED' if own['lower_bound'] >= nominal else 'REJECT' if own['exact'] else 'UNKNOWN'
            result['conditions'].append(dict(kind='nominal_single_craft_material', item=item, status=status,
                evidence=dict(nominal=nominal, owned=own, evidence_ids=rule.get('evidence_ids', []))))
        result['conditions'].append(dict(kind='station_completeness_and_batch', status='UNKNOWN',
            evidence='disclosed requirements are a subset; inherited batch rule unchanged'))
    result['status'] = ('REJECT' if any(c['status'] == 'REJECT' for c in result['conditions']) else
                        'UNKNOWN' if any(c['status'] == 'UNKNOWN' for c in result['conditions']) else 'SUPPORTED')
    return result


def render(controller, facts, obs, memory):
    relevant = controller.needed()
    records = facts.records(obs)
    priority = [dict(id='goal19', kind='goal', value=controller.objective),
                dict(id='blocker19', kind='blocker', value=controller.blocker19),
                dict(id='intent19', kind='intent', value=controller.intent19),
                dict(id='frontiers19', kind='public_map', value=controller.public_entries())]
    for name in sorted(relevant | set(controller.table.recipes)):
        if name not in controller.table.recipes:
            continue
        priority.append(dict(id='recipe19:'+name, kind='recipe', key=name,
            value=controller.table.recipes[name], scope='public nominal rule; actual batch semantics UNKNOWN'))
    priority += [dict(id='intent_history19', kind='previous_intents', value=controller.intent_log19[-5:])]
    priority += sorted(records, key=lambda r: (r.get('kind') not in ('current','container','failure'), r.get('key') not in relevant))
    kept, seen, size = [], set(), 0
    for record in priority:
        line = json.dumps(record, ensure_ascii=False, separators=(',', ':'))
        if record['id'] in seen or len(kept) >= SUMMARY_RECORDS or size + len(line)+1 > SUMMARY_CHARACTERS:
            continue
        kept.append(record); seen.add(record['id']); size += len(line)+1
    fact_text = '\n'.join(json.dumps(r, ensure_ascii=False, separators=(',', ':')) for r in kept)
    user = ('FINAL TASK: '+controller.objective+'\nTRIGGER: '+json.dumps(controller.blocker19, ensure_ascii=False)
            +'\nCURRENT PUBLIC OBSERVATION:\n'+obs['text']+'\nRECENT PUBLIC TRANSITIONS:\n'
            +'\n'.join(memory[-5:])+'\nSTRUCTURED PUBLIC EVIDENCE:\n'+fact_text)
    return user, dict(records=kept, characters=len(fact_text), capacity_characters=SUMMARY_CHARACTERS,
                     capacity_records=SUMMARY_RECORDS, prompt_characters=len(user))
