"""Cohort-preserving analysis of development ablations and recorded old results."""
import json,statistics
from collections import Counter
from hashlib import sha256
from pathlib import Path


def main():
    root=Path(__file__).parent;folder=root/'results/2026-10-16-decision-coverage'
    a=json.loads((folder/'analysis.json').read_text());b=json.loads((folder/'direct/analysis.json').read_text())
    old=json.loads((root/'results/2026-10-17-information-gaps/analysis.json').read_text())
    for experiment in (a,b):
        for name,h in experiment['manifest']['sources'].items():
            assert sha256((root/name).read_text().encode()).hexdigest()==h,name
    rows=a['rows']+b['rows'];modes=a['manifest']['modes']+['direct_gate']
    assert len(rows)==195 and len({(r['config']['id'],r['mode']) for r in rows})==195
    done={'PLAN_FOUND','NO_STRONG_POLICY_WITHIN_H'};by={(r['config']['id'],r['mode']):r for r in rows}
    oldby={(r['config']['id'],r['mode']):r for r in old['rows']}
    for c in a['manifest']['cases']:
        values={r['value'] for r in rows+old['rows'] if r['config']['id']==c['id'] and r['status'] in done}
        assert len(values)<=1,(c['id'],values)
    totals={m:dict(Counter(r['status'] for r in rows if r['mode']==m)) for m in modes}
    cohorts={cohort:{m:dict(Counter(r['status'] for r in rows if r['mode']==m and r['config']['cohort']==cohort))
        for m in modes} for cohort in sorted({r['config']['cohort'] for r in rows})}
    inference={}
    for m in modes:
        target=[r['statistics']['target_capacity'] for r in rows if r['mode']==m and r.get('statistics')]
        inference[m]=dict(seconds=sum(x['seconds'] for x in target),attempts=sum(x['attempts'] for x in target),
            interrupted=sum(x['interrupted'] for x in target),
            decisions=dict(sum((Counter(x['decisions'] or {}) for x in target),Counter())),
            direct=dict(sum((Counter((x['coverage'] or {}).get('direct',{})) for x in target),Counter())))
    ratios={}
    for m in modes:
        ratios[m]={}
        for reference in ('current_leaf','old_leaf'):
            values=[]
            for r in rows:
                if r['mode']!=m or r['status'] not in done:continue
                base=(by if reference=='current_leaf' else oldby)[r['config']['id'],'leaf']
                if base['status'] in done:values.append(r['total_seconds']/base['total_seconds'])
            ratios[m][reference]=dict(n=len(values),median=statistics.median(values),max=max(values),min=min(values))
    cases=[]
    for c in a['manifest']['cases']:
        results={m:by[c['id'],m] for m in modes};r=results['leaf']
        cases.append(dict(id=c['id'],cohort=c['cohort'],old_leaf_status=oldby[c['id'],'leaf']['status'],
            old_leaf_seconds=oldby[c['id'],'leaf'].get('total_seconds'),metadata=r.get('metadata'),
            methods={m:dict(status=x['status'],seconds=x.get('total_seconds'),active_phase=x.get('active_phase'),
                parse_seconds=x.get('parse_seconds'),expanded=(x.get('statistics') or {}).get('search_expanded'),
                optional_seconds=(x.get('statistics') or {}).get('target_capacity',{}).get('seconds'),
                indexed=(x.get('statistics') or {}).get('indexed_engine')) for m,x in results.items()}))
    result=dict(runs=len(rows),source_hashes_verified=True,completed_values_consistent=True,
        totals=totals,cohorts=cohorts,inference=inference,time_ratios=ratios,cases=cases,
        new_completions_from_shared_engine=[c['id'] for c in cases if c['old_leaf_status'] not in done
            and c['methods']['leaf']['status'] in done],
        extra_completions_from_relation=[c['id'] for c in cases if c['methods']['leaf']['status'] not in done
            and any(c['methods'][m]['status'] in done for m in ('relation_threshold','relation_gate','direct_gate'))],
        scope='Already-observed development data; direct variant was designed after the four-mode ablation. '
            'Single-run timing is descriptive. Conditional time ratios include only jointly completed cases. '
            'Inference totals include timeouts and differing explored states; not a fixed-query microbenchmark.',api_calls=0)
    (folder/'summary.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='cases'},indent=2))


if __name__=='__main__':main()
