"""Audit the predeclared first-failure probes; never select worlds by score."""
import json
from pathlib import Path
root=Path('/root/scar_sentry_persistent_20261018_v2');old=Path('/root/scar_sentry_foundation_20261018/evaluation')
read=lambda p:json.loads(p.read_text());summary=[]
for game in ('remnant','mark','metropolis'):
    block=root/'evaluation'/game;choices=[];rows=[]
    for mode in ('advice','execute'):
        r=read(block/mode/'probe_result.json');c=read(block/mode/'first_choice.json');choices.append(c)
        baseline=read(old/game/'sentry/trace'/f"{r['steps']:04d}.json")
        events=[e for p in sorted((block/mode/'trace').glob('*.json')) for e in read(p)['persistent_events'] if e['type']=='persistent_card']
        rows.append(dict(mode=mode,result=r,baseline_score_same_step=baseline['scores']['quest'],
            first_choice=c,cards=[dict(step=e['step'],errors=e['structural_errors'],card=e['card']) for e in events]))
    assert choices[0]['before_digest']==choices[1]['before_digest'] and choices[0]['observation']==choices[1]['observation']
    assert choices[0]['card']==choices[1]['card'] and choices[0]['proposed']==choices[1]['proposed']
    summary.append(dict(game=game,paired_first_choice=True,rows=rows))
(root/'probe_audit.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
print(json.dumps([dict(game=x['game'],paired=True,rows=[dict(mode=r['mode'],step=r['result']['steps'],
    score=r['result']['scores']['quest'],baseline=r['baseline_score_same_step'],first_action=r['first_choice']['chosen']['action'],
    cards=[dict(step=c['step'],errors=c['errors'],status=c['card']['status'] if c['card'] else None,
    action=c['card']['next']['action'] if c['card'] and c['card']['next'] else None) for c in r['cards']]) for r in x['rows']]) for x in summary]))
