"""Real-engine replay of every rejected proposal, separated from agent inputs."""
import argparse
import json
from pathlib import Path

from scar.environment import AGENT_ID,restore
from scar_public.resource_trial import fresh,public_outcome
from scar_public.experiments.replay_real_reuse import execute

def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=True);checks=[];repairs=[]
    for status_path in sorted((a.root/'runtime').glob('*/*/*/current.json')):
        run=status_path.parent;status=json.loads(status_path.read_text())
        if not status['complete']:raise RuntimeError('Wait for all trajectories to finish')
        manifest=json.loads((run/'manifest.json').read_text())
        agent=json.loads((run/'checkpoints'/status['checkpoint']/'agent.json').read_text())
        seen=set()
        for review in agent.get('resource_decision_rejections',[]):
            step=review['step']+1;action=review['action']
            if (step,action) in seen:continue
            seen.add((step,action));prior=step-1
            if prior==0:cp=a.root/'runtime/initial'/manifest['game']/'initial.pkl'
            elif manifest.get('diagnostic_fork',{}).get('start_step')==prior:
                cp=Path(manifest['diagnostic_fork']['path'])/'environment.pkl'
            else:cp=run/'checkpoints'/f'{prior:04d}'/'environment.pkl'
            out=a.output/manifest['stage']/manifest['game']/str(step)/str(len(seen));out.mkdir(parents=True,exist_ok=True)
            env=restore(cp,out);before=env.obs[AGENT_ID]['text'];scores=json.loads(json.dumps(env.scores))
            actual,done=execute(env,action)
            row=json.loads((run/'trace'/f'{step:04d}.json').read_text())
            assert row['observation']==before
            checks.append(dict(stage=manifest['stage'],game=manifest['game'],step=step,rejected=action,
                executed=row['action'],actual_status=public_outcome(actual,action),
                same_visible_physical_state=fresh(before)==fresh(actual),same_scores=scores==env.scores,
                observation=before,shadow_observation=actual,review=review))
        for repair in agent.get('evidence_repairs',[]):
            if repair['status']!='VERIFIED_STRONG_LOCAL_REPAIR':continue
            trials=[r for r in agent.get('resource_trials',[]) if r.get('fingerprint')==repair['fingerprint'] and r.get('status')]
            repairs.append(dict(stage=manifest['stage'],game=manifest['game'],repair=repair,outcomes=trials))
    result=dict(validation_actions=len(checks),agent_received_validation=False,checks=checks,repairs=repairs,
        all_rejections_failed_without_visible_progress=all(r['actual_status']=='failure' and
            r['same_visible_physical_state'] and r['same_scores'] for r in checks))
    (a.output/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k not in ('checks','repairs')}))

if __name__=='__main__':main()
