"""Separate full runs, selected continuations, frozen gates and their costs."""
import argparse,hashlib,json
from collections import Counter
from pathlib import Path

def usage(path,start=0,end=300):
    rows=[json.loads(line) for line in path.read_text().splitlines() if line]
    rows=[r for r in rows if start<=r['step']<end]
    began={r['id'] for r in rows if r['event']=='started'};ended={r['id'] for r in rows if r['event']!='started'}
    done=[r for r in rows if r['event']=='completed']
    return dict(requests=len(began),estimated_usd=sum(r.get('peak_usd',0) for r in done),
        summed_request_seconds=sum(r.get('elapsed_s',0) for r in done),
        unknown_charge_attempts=sum(bool(r.get('charge_unknown')) for r in rows)+len(began-ended))

def analyze(run,start=0):
    manifest=json.loads((run/'manifest.json').read_text());status=json.loads((run/'current.json').read_text())
    state=json.loads((run/'checkpoints'/status['checkpoint']/'agent.json').read_text())
    rows=[json.loads(p.read_text()) for p in sorted((run/'trace').glob('*.json')) if start<int(p.stem)<=status['steps']]
    parsed=[json.loads(r['response']) for r in rows]
    tasks=[dict(step=r['step'],report=l.removeprefix('Stage completed: '),action=r['action'])
           for r in rows for l in r['next_observation'].splitlines() if l.startswith('Stage completed: ')]
    weapon=next((e['step'] for e in tasks if e['report']=='Obtain and equip a weapon before engaging enemies.'),None)
    reviews=[r for r in state.get('method_reviews',[]) if r.get('step',0)>=start]
    return dict(game=manifest['game'],stage=manifest['stage'],source_manifest=manifest,status=status,
        public_completions=tasks,weapon_completion_step=weapon,
        usage=usage(run/'api/attempts.jsonl',start,status['steps']),
        usage_to_weapon_completion=usage(run/'api/attempts.jsonl',start,weapon) if weapon else None,
        method_reviews=reviews,method_outcomes=state.get('method_outcomes',[]),
        review_counts=dict(Counter(r['status'] for r in reviews)),
        decision_sources=dict(Counter(p.get('decision_source','llm') for p in parsed)),
        enabling=state.get('method_enabling',[]),
        craft_failures=sum(r['action'].startswith('craft ') and 'Cannot craft ' in r['next_observation'] for r in rows),
        quest_events=[dict(step=r['step'],score=r['scores'].get('quest'),action=r['action']) for i,r in enumerate(rows)
                      if r['scores'].get('quest')!=(rows[i-1]['scores'].get('quest') if i else None)],
        last_actions=[r['action'] for r in rows[-10:]])

def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('old',type=Path)
    p.add_argument('--partial',action='store_true');a=p.parse_args()
    rows=[analyze(p.parent,93 if 'selected' in p.parts else 0) for p in sorted((a.root/'runtime').glob('*/*/*/current.json'))]
    all_done=len(rows)==4 and all(r['status']['complete'] for r in rows)
    if not a.partial:assert all_done
    controls=[analyze(a.old/'runtime/structured/evidence_repair_v11'/game) for game in ('remnant','mark','metropolis')]
    selected_control=analyze(a.old/'runtime/attributes_structured/evidence_repair_v11/metropolis',93)
    comparisons=[]
    for row in rows:
        control=selected_control if row['stage']=='selected' else next(c for c in controls if c['game']==row['game'])
        assert row['source_manifest']['initial_snapshot_sha256']==control['source_manifest']['initial_snapshot_sha256']
        comparisons.append(dict(stage=row['stage'],game=row['game'],new_score=row['status']['scores']['quest'],
            frozen_control_score=control['status']['scores']['quest'],new_completion=row['status']['termination']=='environment',
            frozen_control_completion=control['status']['termination']=='environment',
            new_weapon_step=row['weapon_completion_step'],control_weapon_step=control['weapon_completion_step'],
            new_usage=row['usage'],frozen_control_usage=control['usage'],
            new_reviews=row['review_counts'],new_decision_sources=row['decision_sources']))
    source=json.loads((a.root/'code/source_manifest.json').read_text())
    assert all(hashlib.sha256((a.root/'code'/name).read_bytes()).hexdigest()==sha for name,sha in source.items())
    result=dict(all_complete=all_done,scope='Development single samples, reused worlds, no new baseline calls',
        comparisons=comparisons,runs=rows,controls=controls,selected_control=selected_control,
        api_requests=sum(r['usage']['requests'] for r in rows),estimated_usd=sum(r['usage']['estimated_usd'] for r in rows),
        unknown_charge_attempts=sum(r['usage']['unknown_charge_attempts'] for r in rows),source_files_verified=len(source))
    (a.root/('analysis_partial.json' if a.partial else 'analysis.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k not in ('runs','controls','selected_control')},ensure_ascii=False))

if __name__=='__main__':main()
