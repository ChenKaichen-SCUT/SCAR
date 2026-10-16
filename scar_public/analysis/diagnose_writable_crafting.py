"""OFFLINE engine diagnosis, zero API calls; never imported by an online policy."""
import json
from pathlib import Path

from scar.environment import restore, state_digest, AGENT_ID


def diagnose(root):
    root=Path(root)
    source=root/'v6diag_c_cp178/obligation_v6/metropolis'
    env=restore(source/'checkpoints/0203/environment.pkl',root/'offline_v6_writable_diagnosis')
    trace=json.loads((source/'trace/0204.json').read_text())
    assert state_digest(env)==trace['before_digest']
    agent=env.agents[0]
    rule=agent._action_rules_module.CraftRule
    output_id=env.world.auxiliary['obj_name_to_id']['legal_brief']
    # The analysis intentionally examines privileged rule data. It is not agent input.
    from games.generated.metropolis.rules.action_rules import get_def_id
    definition=env.world.objects[get_def_id(output_id)]
    hands=dict(agent.items_in_hands)
    index=dict(rule.build_writable_index(hands))
    result={'classification':'offline source-informed diagnostic, not autonomous performance',
        'upstream_revision':'248430692a9d4a61d38c6c03ab2126287faaf450',
        'source_checkpoint':str(source/'checkpoints/0203'),'public_before':env.obs[AGENT_ID]['text'],
        'output_usage':definition.usage,'engine_recipe':definition.craft_ingredients,
        'raw_hand_counts':hands,'writable_index_used_for_all_ingredients':index}
    obs,reward,done,info=env.step({AGENT_ID:'craft 1 legal_brief'})
    env.update_scores(reward)
    assert state_digest(env)==trace['after_digest']
    result.update(public_after=obs[AGENT_ID]['text'],original_failure_reproduced=True,
        conclusion='The writable-output branch reads ingredient counts only from suffixed instance indexes; ordinary material IDs are omitted. The public sufficient-input prediction is contradicted. No engine changes or object-specific policy exceptions were made.')
    return result


if __name__=='__main__':
    root=Path('/root/scar_research_20261015/runtime')
    result=diagnose(root)
    (root.parent/'writable_diagnosis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({k:result[k] for k in ('output_usage','engine_recipe','raw_hand_counts',
        'writable_index_used_for_all_ingredients','original_failure_reproduced')},indent=2))
