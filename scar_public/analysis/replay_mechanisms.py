"""Offline mechanistic replay; no model calls, not an agent benchmark."""
import json
from pathlib import Path
from scar.environment import restore, AGENT_ID, state_digest

root=Path('/root/scar_research_20261015/runtime')
source=root/'round3/viability_v3/metropolis'
results=[]
for step in (62,255):
    for phrase in ('RESTITUERE-LEGEM-PRIMAM','AURUM-NOCTIS'):
        env=restore(source/'checkpoints'/f'{step:04d}'/'environment.pkl',root/'mechanistic_replay'/f'{step}-{phrase}')
        before=state_digest(env)
        score=env.scores[AGENT_ID]['quest']
        action=f'write {phrase} legal_brief_0'
        obs,reward,done,info=env.step({AGENT_ID:action})
        env.update_scores(reward)
        results.append({'checkpoint':step,'before_digest':before,'action':action,
                        'quest_before':score,'quest_after':env.scores[AGENT_ID]['quest'],
                        'public_feedback':obs[AGENT_ID]['text']})
(root/'phase2_mechanistic_replay.json').write_text(json.dumps(results,indent=2))
for r in results:
    print(r['checkpoint'],r['action'],r['quest_before'],r['quest_after'],r['before_digest'])

source=root/'round2/evidence_v2/metropolis'
alternatives={
    'original': [json.loads((source/'trace'/f'{i:04d}.json').read_text())['action'] for i in range(207,215)],
    'container_arrangement': ['drop gavel_timber','pick up docket_satchel_0','equip docket_satchel_0',
        'store 1 gavel_timber docket_satchel_0','pick up gavel_timber','pick up binding_thread',
        'craft 1 gavel_club','pick up gavel_club']}
capacity=[]
for label,actions in alternatives.items():
    env=restore(source/'checkpoints/0206/environment.pkl',root/'mechanistic_replay'/label)
    case={'label':label,'checkpoint':206,'before_digest':state_digest(env),
          'quest_before':env.scores[AGENT_ID]['quest'],'trace':[]}
    for action in actions:
        obs,reward,done,info=env.step({AGENT_ID:action})
        env.update_scores(reward)
        case['trace'].append({'action':action,'quest':env.scores[AGENT_ID]['quest'],
                              'public_feedback':obs[AGENT_ID]['text']})
    case['quest_after']=env.scores[AGENT_ID]['quest']
    capacity.append(case)
    print(label,case['quest_before'],case['quest_after'])
(root/'phase2_capacity_replay.json').write_text(json.dumps(capacity,indent=2))
