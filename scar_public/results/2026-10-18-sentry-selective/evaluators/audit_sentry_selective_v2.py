"""Full reconstruction and all replacements' evaluation-only counterfactuals."""
import argparse,contextlib,json,sys
from pathlib import Path
from scar.environment import AGENT_ID,restore,snapshot,state_digest
from scar_public.continuation import feedback_lines
p=argparse.ArgumentParser();p.add_argument('--game',required=True);a=p.parse_args()
root=Path('/root/scar_sentry_selective_20261018_v2');base=Path('/root/scar_sentry_foundation_20261018/evaluation')
old=Path('/root/scar_sentry_persistent_20261018_v2/evaluation')
folder=root/'evaluation'/a.game/'selective';assert (folder/'result.json').exists()
state=(base/a.game/'initial.pkl').read_bytes();records=[];count=0;paired_prefix=0;prefix=True
same_action_reason_changes=0;first_divergence=None
for path in sorted((folder/'trace').glob('*.json')):
    row=json.loads(path.read_text());advice=json.loads((old/a.game/'advice/trace'/path.name).read_text())
    if prefix:
        assert row['before_digest']==advice['before_digest'] and row['observation']==advice['observation']
        # Until the first override, keep must preserve the entire actor output.
        assert row['proposed']==advice['proposed']
        if row['action']!=advice['action']:prefix=False;first_divergence=row['step']
        else:
            assert row['response']==advice['response'] and row['after_digest']==advice['after_digest']
            paired_prefix+=1
    same_action_reason_changes+=row['action']==row['proposed']['action'] and row['response']!=row['proposed']
    with contextlib.redirect_stdout(sys.stderr):
        env=restore(state,root/'private_audit'/a.game)
        assert state_digest(env)==row['before_digest']
        if row['action']!=row['proposed']['action']:
            score0=env.scores.get(AGENT_ID,{}).get('quest',0)
            po,pr,pd,_=env.step({AGENT_ID:row['proposed']['action']});env.update_scores(pr)
            records.append(dict(step=row['step'],observation=row['observation'],proposed=row['proposed'],executed=row['response'],
                actual_observation=row['next_observation'],proposed_observation=po[AGENT_ID]['text'],
                actual_feedback_error=bool(feedback_lines(row['next_observation'])),proposed_feedback_error=bool(feedback_lines(po[AGENT_ID]['text'])),
                actual_quest_gain=row['scores']['quest']-score0,proposed_quest_gain=env.scores[AGENT_ID]['quest']-score0))
        env=restore(state,root/'private_audit'/a.game)
        obs,reward,done,_=env.step({AGENT_ID:row['action']});env.update_scores(reward)
        assert state_digest(env)==row['after_digest'] and obs[AGENT_ID]['text']==row['next_observation']
        state=snapshot(env);count+=1
assert same_action_reason_changes==0
result=dict(game=a.game,reconstructed_transitions=count,shared_advice_prefix=paired_prefix,first_action_divergence=first_divergence,
    same_action_response_changes=same_action_reason_changes,counterfactuals=len(records),records=records)
(root/(a.game+'_audit.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in result.items() if k!='records'}))
