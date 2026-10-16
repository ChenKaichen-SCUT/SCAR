"""Recompute the two observed development stages without rerunning baselines."""
import json
from collections import Counter,defaultdict
from pathlib import Path
from statistics import median

ROOT=Path(__file__).parent/'results/2026-10-16-frontier-scheduler'
OLD=ROOT.parent/'2026-10-16-resource-validation'
DONE={'PLAN_FOUND','NO_STRONG_POLICY_WITHIN_H'}


def compact(row,stage):
    stats=row.get('statistics') or {};f=stats.get('frontier') or {}
    r={k:row.get(k) for k in ('config','mode','status','value','verified_policy_depth',
       'total_seconds','parse_seconds','construct_seconds','root_seconds','search_seconds','timed_out')}
    r.update(stage=stage,expanded=stats.get('search_expanded'),frontier=f)
    return r


def main():
    rows=[]
    has_raw=all((p/'analysis.json').exists() for p in (ROOT,ROOT/'focused'))
    if has_raw:
        for stage,p in [('first',ROOT),('focused',ROOT/'focused')]:
            rows += [compact(r,stage) for r in json.loads((p/'analysis.json').read_text())['rows']]
    else:rows=json.loads((ROOT/'runs_summary.json').read_text())['rows']
    baseline=json.loads((OLD/'analysis.json').read_text())['rows']
    leaf={r['config']['id']:r for r in baseline if r['mode']=='leaf'}
    audit=json.loads((OLD/'source_audit.json').read_text())
    excluded={name for group in audit['groups'].values() for name in group[1:]}
    methods={}
    for mode in sorted({r['mode'] for r in rows}):
        group=[r for r in rows if r['mode']==mode]
        dedup=[r for r in group if r['config'].get('folder') not in excluded]
        for r in group:
            b=leaf[r['config']['id']]
            if r['status'] in DONE and b['status'] in DONE:assert r['value']==b['value']
            if r['status']=='PLAN_FOUND':assert r['verified_policy_depth']==r['value']
        methods[mode]=dict(raw_status=dict(Counter(r['status'] for r in group)),
            deduplicated_status=dict(Counter(r['status'] for r in dedup)),
            completed=sum(r['status'] in DONE for r in group),
            prunes=sum(r['frontier'].get('prunes',0) for r in group),
            ancestor_prunes=sum(r['frontier'].get('ancestor_prunes',0) for r in group),
            refinements=sum(r['frontier'].get('trace',{}).get('refinements',0) for r in group))
    prediction=[]
    for r in rows:
        if r['stage']!='focused':continue
        segments=defaultdict(list)
        for e in r['frontier'].get('evidence',[]):
            segments[e['query']].append(e)
            if e['status'] in ('REJECT','BOUND_PASS','REFINED'):
                segment=segments.pop(e['query']);first=segment[0]
                units=sum(s['work'] for s in segment)
                prediction.append(dict(id=r['config']['id'],mode=r['mode'],query=e['query'],
                    status=e['status'],predicted_units=first['prediction'],realized_units=units,
                    actual_over_predicted=units/max(1,first['prediction']),slices=len(segment)))
    if not has_raw:prediction=json.loads((ROOT/'prediction_segments.json').read_text())
    def public_row(row):
        result=dict(row)
        result['frontier']={k:v for k,v in row.get('frontier',{}).items() if k!='evidence'}
        return result
    comparisons=[compact(r,'reused_baseline') for r in baseline
        if r['config']['family']=='rovers' and r['mode'] in ('leaf','amortized_relation')]
    previous=json.loads((ROOT.parent/'2026-10-16-multistep-refinement/runs_summary.json').read_text())['rows']
    comparisons += [r for r in previous if r['config']['family']=='rovers'
                     and r['mode'] in ('final_work','persistent_multistep')]
    comparisons += [r for r in rows if r['config']['family']=='rovers']
    ratios=[e['actual_over_predicted'] for e in prediction]
    result=dict(scope='300 changed-variant runs, 50 previously observed configs, 46 distinct. Development only; unchanged baselines reused. Single runs. Completed-query prediction diagnostics exclude censored/retired queries and cannot establish unbiased prediction accuracy.',
        methods=methods,rover_comparison=[public_row(r) for r in comparisons],prediction=dict(completed_segments=len(prediction),
            median_actual_over_predicted=median(ratios) if ratios else None,
            max_actual_over_predicted=max(ratios,default=None),segments=prediction),
        kernel_first=json.loads((ROOT/'work_diagnostics.json').read_text()),
        kernel_catalog=json.loads((ROOT/'focused/work_diagnostics.json').read_text()),api_calls=0)
    (ROOT/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'runs_summary.json').write_text(json.dumps(dict(rows=[public_row(r) for r in rows]),separators=(',',':')),encoding='utf-8')
    (ROOT/'prediction_segments.json').write_text(json.dumps(prediction,separators=(',',':')),encoding='utf-8')
    print(json.dumps(dict(methods=methods,prediction={k:v for k,v in result['prediction'].items() if k!='segments'}),indent=2))


if __name__=='__main__':main()
