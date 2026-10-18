"""Offline same-state one-action counterfactuals, never fed to the policy."""
import argparse,contextlib,json,sys
from pathlib import Path
from scar.environment import AGENT_ID,restore,snapshot,state_digest
from scar_public.continuation import feedback_lines
p=argparse.ArgumentParser();p.add_argument('--game',required=True);a=p.parse_args()
root=Path('/root/scar_sentry_persistent_20261018_v2');old=Path('/root/scar_sentry_foundation_20261018/evaluation')
records=[];count=0
for mode in ('advice','execute'):
    folder=root/'evaluation'/a.game/mode;assert (folder/'result.json').exists()
    state=(old/a.game/'initial.pkl').read_bytes()
    for path in sorted((folder/'trace').glob('*.json')):
        row=json.loads(path.read_text())
        with contextlib.redirect_stdout(sys.stderr):
            env=restore(state,root/'private_counterfactual'/a.game/mode)
            assert state_digest(env)==row['before_digest']
            if row['action']!=row['proposed']['action']:
                initial_score=env.scores.get(AGENT_ID,{}).get('quest',0)
                po,pr,pd,_=env.step({AGENT_ID:row['proposed']['action']});env.update_scores(pr)
                records.append(dict(mode=mode,step=row['step'],observation=row['observation'],
                    proposed=row['proposed'],executed=row['response'],actual_observation=row['next_observation'],
                    proposed_observation=po[AGENT_ID]['text'],actual_feedback_error=bool(feedback_lines(row['next_observation'])),
                    proposed_feedback_error=bool(feedback_lines(po[AGENT_ID]['text'])),
                    actual_quest_gain=row['scores']['quest']-initial_score,
                    proposed_quest_gain=env.scores[AGENT_ID]['quest']-initial_score))
            env=restore(state,root/'private_counterfactual'/a.game/mode)
            obs,reward,done,_=env.step({AGENT_ID:row['action']});env.update_scores(reward)
            assert state_digest(env)==row['after_digest'] and obs[AGENT_ID]['text']==row['next_observation']
            state=snapshot(env);count+=1
result=dict(game=a.game,prefix_transition_checks=count,counterfactuals=len(records),records=records,
    qualification='All changed actions, paired same-state one-action replay. Feedback errors are heuristic; no long-horizon counterfactual claim. Evaluation-only, zero API calls.')
(root/(a.game+'_action_audit.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in result.items() if k!='records'}))
