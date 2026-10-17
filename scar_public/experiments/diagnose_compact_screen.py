import argparse,json
from pathlib import Path
parser=argparse.ArgumentParser()
parser.add_argument('--root',type=Path,required=True)
root=parser.parse_args().root/'evaluation'
assert (root.parent/'pipeline_complete.json').exists()
out={}
for b in sorted(root.iterdir()):
    out[b.name]={}
    for phase,arms in [('main',['checked','continuation_generic','sentry']),('scheduled',['continuation_scheduled'])]:
        for arm in arms:
            folder=b/phase/arm/'trace'
            if not folder.exists():continue
            rows=[json.loads(p.read_text()) for p in sorted(folder.glob('*.json'))]
            milestones=[];last=0;changes=[]
            for r in rows:
                if r['scores']['quest']!=last:
                    milestones.append(dict(step=r['step'],score=r['scores']['quest'],action=r['action'],
                        stage_feedback=[l for l in r['next_observation'].splitlines() if l.startswith(('Stage completed','Task completed','Tutorial Step'))]))
                    last=r['scores']['quest']
                e=json.loads(r['response']).get('continuation',{})
                if e.get('changed'):
                    changes.append(dict(step=r['step'],original=e['original'],action=r['action'],trigger=e['trigger']['kind'],
                        goal=e['packet']['goals'],model_first_choice=e['proposal']['action'],rejected=e['rejected'],
                        rationale=e['proposal'].get('reasoning',''),
                        next_feedback=[l for l in r['next_observation'].splitlines() if l.startswith(('Cannot','I entered','I talked','I inspected','Stage completed'))]))
            out[b.name][arm]=dict(steps=len(rows),milestones=milestones,changes=changes)
(root.parent/'final_trace_diagnosis.json').write_text(json.dumps(out,indent=2))
for game,arms in out.items():
    print(game)
    for arm,r in arms.items():
        print(arm,[(m['step'],m['score'],m['action']) for m in r['milestones']])
        for c in r['changes']:print(json.dumps({k:v for k,v in c.items() if k!='rationale'},ensure_ascii=False))
