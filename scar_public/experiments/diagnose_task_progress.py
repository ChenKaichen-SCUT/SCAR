"""Public-trajectory failure and intervention evidence, without evaluator internals."""
import argparse,json
from collections import Counter
from pathlib import Path


def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args();out={}
    for group in ('selected','selected_v2','full','ablation','corrected'):
        for manifest in sorted((a.root/group).glob('*/manifest.json')):
            m=json.loads(manifest.read_text());run=manifest.parent
            for arm in m['arms']:
                status=json.loads((run/arm/'current.json').read_text());assert status['complete']
                rows=[json.loads(f.read_text()) for f in sorted((run/arm/'trace').glob('*.json'))]
                counts=Counter(); longest=0;length=0;previous=None;reports=[];probes=[]
                for r in rows:
                    response=json.loads(r['response']); action=r['action'];counts[action]+=1
                    length=length+1 if action==previous else 1;longest=max(longest,length);previous=action
                    if response.get('decision_source')=='task_outcome_observation':probes.append(dict(step=r['step'],action=action))
                    for l in r['next_observation'].splitlines():
                        if l.startswith(('Stage completed','I successfully crafted','I have died')):reports.append(dict(step=r['step'],line=l))
                key='/'.join([group,m['game'],arm])
                out[key]=dict(status=status,last_frame=json.loads(rows[-1]['response']).get('frame'),
                    longest_identical_action_run=longest,most_common_actions=counts.most_common(8),
                    outcome_probes=probes,public_reports=reports,
                    last_actions=[dict(step=r['step'],action=r['action']) for r in rows[-12:]],
                    last_observation=rows[-1]['next_observation'])
    (a.root/'diagnosis.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:dict(probes=len(v['outcome_probes']),longest_repeat=v['longest_identical_action_run']) for k,v in out.items()}))


if __name__=='__main__':main()
