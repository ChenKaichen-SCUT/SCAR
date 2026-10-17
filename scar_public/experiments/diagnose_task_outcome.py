"""Explain actual exposure and unresolved task bridges from public run records."""
import argparse,json
from collections import Counter
from pathlib import Path


def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args();out={}
    for game in ('remnant','mark','metropolis'):
        run=a.root/'corrected'/game/'v15';state=json.loads((run/'current.json').read_text())
        memory=json.loads((run/'checkpoints'/state['checkpoint']/'agent.json').read_text())
        decisions=memory.get('outcome_decisions',[]);unique={}
        for d in decisions:
            for c in d.get('candidates',[]):
                unique.setdefault((c['task'],c['endpoint']),dict(task=c['task'],endpoint=c['endpoint'],support=c['support'],
                    first_step=d['step'],candidate_cost=c['cost'],material_status=c['reserve']['status']))
        endpoints={c['endpoint'] for c in unique.values()}
        descriptions=list(dict.fromkeys(line for obs in memory['observations'] for line in obs.splitlines()
            if line.startswith('I inspected ') and any('I inspected '+n+':' in line for n in endpoints)))
        actions=[json.loads(path.read_text()) for path in sorted((run/'trace').glob('*.json'))[-20:]]
        out[game]=dict(status=state,last_frame=memory['frame'],task_endpoint_pairs=list(unique.values()),
            observed_endpoint_descriptions=descriptions,last_actions=[dict(step=r['step'],action=r['action']) for r in actions],
            late_action_counts=dict(Counter(r['action'].split()[0] for r in actions)),
            late_failure_feedback=list(dict.fromkeys(line for r in actions for line in r['next_observation'].splitlines() if line.startswith(('Cannot ','I was attacked','I died')))),
            latest_reports=[line for line in actions[-1]['next_observation'].splitlines() if line.startswith(('Stage completed','[','Main goal'))])
    (a.root/'diagnosis.json').write_text(json.dumps(out,indent=2))
    print(json.dumps({g:{'pairs':x['task_endpoint_pairs'],'descriptions':x['observed_endpoint_descriptions'],'last_frame':x['last_frame']} for g,x in out.items()}))


if __name__=='__main__':main()
