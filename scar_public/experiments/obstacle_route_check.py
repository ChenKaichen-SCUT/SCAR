"""Evaluator-only replay of old rejected routes; no outcome enters any policy."""
import argparse,contextlib,json,os,sys
from pathlib import Path
from scar.environment import AGENT_ID,restore,snapshot,state_digest
from scar.io import atomic_json
from scar_public.continuation import feedback_lines


def main():
    p=argparse.ArgumentParser();p.add_argument('--audit',type=Path,required=True)
    p.add_argument('--block',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();audit=json.loads(a.audit.read_text());old=Path(audit['old'])
    assert os.environ['PYTHONHASHSEED']==json.loads((a.block/'manifest.json').read_text())['hash_seed']
    selected={r['step']:r for r in audit['records'] if r['old_changed'] and r['old_selected_route_blockers']}
    state=(a.block/'initial.pkl').read_bytes();checks=0;results=[]
    for path in sorted((old/'trace').glob('*.json')):
        row=json.loads(path.read_text())
        with contextlib.redirect_stdout(sys.stderr):
            if row['step'] in selected:
                record=selected[row['step']];plan=record['old_selected_route_blockers'][0]['plan'];moves=[]
                candidate=restore(state,a.output/'candidate_environment')
                for action in plan:
                    observation,reward,done,_=candidate.step({AGENT_ID:action});candidate.update_scores(reward)
                    text=observation[AGENT_ID]['text'];failure=feedback_lines(text)
                    moves.append(dict(action=action,feedback=text,failures=failure,scores=candidate.scores[AGENT_ID]))
                    if failure or done:break
                results.append(dict(step=row['step'],before_digest=row['before_digest'],plan=plan,moves=moves))
            env=restore(state,a.output/'prefix_environment');assert state_digest(env)==row['before_digest']
            observation,reward,done,_=env.step({AGENT_ID:row['action']});env.update_scores(reward)
            assert state_digest(env)==row['after_digest'] and observation[AGENT_ID]['text']==row['next_observation']
            state=snapshot(env);checks+=1
    atomic_json(a.output/'route_check.json',dict(prefix_replays=checks,new_api_requests=0,results=results,
        qualification='Selected old states; fixed old candidate route rollout. No alternative policy or final score claim.'))
    print(json.dumps(dict(prefix_replays=checks,cases=len(results),failed_routes=sum(bool(r['moves'][-1]['failures']) for r in results))))


if __name__=='__main__':main()
