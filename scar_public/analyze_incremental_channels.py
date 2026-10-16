"""Separate exact cache savings, discovery evidence and controlled search results."""
import json,statistics
from collections import Counter
from hashlib import sha256
from pathlib import Path


def main():
    root=Path(__file__).parent;folder=root/'results/2026-10-16-incremental-channels'
    study=json.loads((folder/'analysis.json').read_text())
    previous=json.loads((root/'results/2026-10-16-certificate-refinement/analysis.json').read_text())
    base=json.loads((root/'results/2026-10-16-decision-coverage/analysis.json').read_text())
    for name,digest in study['manifest']['sources'].items():
        assert sha256((root/name).read_text().encode()).hexdigest()==digest,name
    assert len(study['rows'])==39
    old={r['config']['id']:r for r in previous['rows'] if r['mode']=='refine_certificate'}
    leaf={r['config']['id']:r for r in base['rows'] if r['mode']=='leaf'}
    complete={'PLAN_FOUND','NO_STRONG_POLICY_WITHIN_H'};ratios={};cases=[]
    for label,source in [('previous_refinement',old),('leaf',leaf)]:
        ratios[label]=[r['total_seconds']/source[r['config']['id']]['total_seconds'] for r in study['rows']
            if r['status'] in complete and source[r['config']['id']]['status'] in complete]
    totals=Counter();refine=Counter();pools=Counter();seconds=0
    for r in study['rows']:
        prior=old[r['config']['id']];ref=leaf[r['config']['id']]
        if r['status'] in complete:
            assert r['value']==prior['value']==ref['value']
        t=(r.get('statistics') or {}).get('target_capacity',{});coverage=t.get('coverage') or {}
        refstats=coverage.get('refinement',{});pool=coverage.get('incremental_pool',{})
        refine.update({k:v for k,v in refstats.items() if type(v) in (int,float)})
        pools.update({k:v for k,v in pool.items() if type(v) in (int,float)})
        seconds+=t.get('seconds',0)
        cases.append(dict(id=r['config']['id'],status=r['status'],seconds=r.get('total_seconds'),
            prior_seconds=prior.get('total_seconds'),leaf_seconds=ref.get('total_seconds'),
            expanded=(r.get('statistics') or {}).get('search_expanded'),
            prior_expanded=(prior.get('statistics') or {}).get('search_expanded'),
            static_groups=r.get('metadata',{}).get('static_model_groups'),optional_seconds=t.get('seconds'),
            refined_scalar_prunes=refstats.get('refined_scalar_prunes'),
            refined_relation_prunes=refstats.get('refined_relation_prunes')))
    fixed=json.loads((folder/'fixed_queries.json').read_text())['rows']
    micro={m:dict(seconds=sum(r['results'][m]['seconds'] for r in fixed),
        statuses=dict(Counter(r['results'][m]['status'] for r in fixed))) for m in ('old','cold_core','shared_core')}
    discovery=json.loads((folder/'discovery/analysis.json').read_text())
    assert sha256((root/'search_public_separations.py').read_text().encode()).hexdigest()==discovery['manifest']['source_sha256']
    separations=[dict(config=r['config'],query=q) for r in discovery['rows'] for q in r['queries'] if q['status']=='SEPARATION']
    validation=json.loads((folder/'public_validation.json').read_text())
    strong=next(r for r in validation['rows'] if r['config']['id']=='rovers_pfile4_a16s1')
    assert strong['oracle']['status']=='complete' and strong['oracle']['full']=='infinity'
    assert not strong['oracle']['single_detects'] and not strong['oracle']['pair_detects']
    assert strong['leaf_lower']==0
    for e in strong['engines'].values():assert (e['scalar'],e['identity'],e['fallbacks'])==(4,3,0)
    result=dict(runs=39,source_hashes_verified=True,completed_values_consistent=True,
        statuses=dict(Counter(r['status'] for r in study['rows'])),cases=cases,refinement=dict(refine),
        channel_pool=dict(pools),optional_seconds=seconds,
        time_ratios={k:dict(n=len(v),median=statistics.median(v),min=min(v),max=max(v)) for k,v in ratios.items()},
        fixed_queries=11,microbenchmark=micro,
        single_static_group_cases=sum(c['static_groups']==1 for c in cases),
        discovery=dict(configurations=len(discovery['rows']),
            statuses=dict(Counter(r['status'] for r in discovery['rows'])),
            query_statuses=dict(Counter(q['status'] for r in discovery['rows'] for q in r['queries'])),
            separation_queries=len(separations),separation_configurations=len({r['config']['id'] for r in separations}),
            separations=separations),stronger_control_separation=strong,api_calls=0,
        scope='39-case known-development performance, 11 saved-query microbenchmark, and 51-config exploratory '
        'root sweep kept separate. Stronger-control witness is a declared public-task resource extension. '
        'No general dominance, independent-holdout or statistical speedup claim.')
    (folder/'summary.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k not in ('cases','discovery','stronger_control_separation')},indent=2))
    print(json.dumps({k:v for k,v in result['discovery'].items() if k!='separations'},indent=2))


if __name__=='__main__':main()
