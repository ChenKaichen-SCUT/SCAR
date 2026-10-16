"""Rebuild development summary from saved outcomes; never reruns a planner."""
import json
from collections import Counter
from pathlib import Path
from statistics import median

ROOT=Path(__file__).parent/'results/2026-10-16-multistep-refinement'
OLD=Path(__file__).parent/'results/2026-10-16-resource-validation'
DONE={'PLAN_FOUND','NO_STRONG_POLICY_WITHIN_H'}


def compact(r,stage):
    stats=r.get('statistics') or {};optional=stats.get('target_capacity') or {}
    coverage=optional.get('coverage') or {};children=coverage.get('refinement',{}).get('children',[])
    result={k:r.get(k) for k in ('config','mode','status','value','verified_policy_depth','total_seconds',
        'parse_seconds','construct_seconds','root_seconds','search_seconds','root_lower','wall_seconds','timed_out')}
    result.update(stage=stage,expanded=stats.get('search_expanded'),optional_seconds=optional.get('seconds'),
        attempts=optional.get('attempts'),prunes=optional.get('prunes'),
        multistep=coverage.get('multistep'),work=coverage.get('work_schedule'),
        amortized=coverage.get('amortized'),batch=stats.get('batch_schedule'),
        persistence=coverage.get('persistence'),
        scalar_nodes=sum(c.get('dp_nodes',0) for c in children),
        relation_nodes=sum(c.get('relation',{}).get('nodes',0) for c in children),
        channel_queries=sum(c.get('channel_queries',0) for c in children))
    return result


def main():
    old=json.loads((OLD/'analysis.json').read_text())['rows']
    baseline={(r['config']['id'],r['mode']):r for r in old}
    rows=[]
    phases=[('first',ROOT),('cached',ROOT/'cached'),('final',ROOT/'final')]
    if all((folder/'analysis.json').exists() for _,folder in phases):
        for stage,folder in phases:
            rows += [compact(r,stage) for r in json.loads((folder/'analysis.json').read_text())['rows']]
    else:
        rows=json.loads((ROOT/'runs_summary.json').read_text())['rows']
    audit=json.loads((OLD/'source_audit.json').read_text())
    excluded={name for group in audit['groups'].values() for name in group[1:]}
    methods={}
    for mode in sorted({r['mode'] for r in rows}):
        group=[r for r in rows if r['mode']==mode]
        dedup=[r for r in group if r['config'].get('folder') not in excluded]
        fresh=[r for r in dedup if r['config']['source']=='fresh']
        ratios=[]
        for r in fresh:
            b=baseline[r['config']['id'],'leaf']
            if r['status'] in DONE and b['status'] in DONE:
                assert r['value']==b['value']
                ratios.append(r['total_seconds']/b['total_seconds'])
        for r in group:
            b=baseline[r['config']['id'],'leaf']
            if r['status'] in DONE and b['status'] in DONE:
                assert r['value']==b['value']
            if r['status']=='PLAN_FOUND':assert r['verified_policy_depth']==r['value']
        methods[mode]=dict(raw_status=dict(Counter(r['status'] for r in group)),
            deduplicated_status=dict(Counter(r['status'] for r in dedup)),
            other_public_deduplicated_status=dict(Counter(r['status'] for r in fresh)),
            fresh_completed_ratio_median=median(ratios) if ratios else None,
            fresh_ratio_pairs=len(ratios),
            completed=sum(r['status'] in DONE for r in group),
            multistep_refinements=sum((r['multistep'] or {}).get('refinements',0) for r in group),
            new_scalar_prunes=sum((r['amortized'] or {}).get('scalar_prunes',0) for r in group),
            new_relation_prunes=sum((r['amortized'] or {}).get('relation_prunes',0) for r in group))
    diagnostics=[]
    for r in json.loads((ROOT/'cached/root_diagnostics.json').read_text())['rows']:
        rejected=[q['depth'] for q in r['queries'] if q.get('prune')]
        diagnostics.append(dict(id=r['config']['id'],added_atoms=r['added_atoms'],queries=r['queries'],
            certified_lower=1+max(rejected,default=-1),seconds=r['seconds'],
            selection=r['statistics']['multistep']))
    comparisons=[compact(r,'reused_baseline') for r in old
        if r['config']['family']=='rovers' and r['mode'] in ('leaf','amortized_relation')]
    result=dict(scope='Development only. 400 changed-variant runs on 50 previously observed configs; 46 after duplicate-source removal. Reuse unchanged baselines. Single measurements, no significance or holdout claim.',
        methods=methods,rover_comparison=comparisons+[r for r in rows if r['config']['family']=='rovers'],
        root_diagnostics=diagnostics,api_calls=0)
    (ROOT/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'runs_summary.json').write_text(json.dumps(dict(rows=rows,storage_note='Compact audit rows. Full phase logs and statistics remain in the three raw result archives in the reproduction bundle.'),separators=(',',':')),encoding='utf-8')
    print(json.dumps(dict(methods=methods,rows=len(rows)),indent=2))


if __name__=='__main__':main()
