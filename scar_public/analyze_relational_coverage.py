"""Summarize the frozen primary study and disclosed follow-up diagnostics."""
from collections import Counter
import json
from pathlib import Path
from statistics import median
SOLVED={'PLAN_FOUND','NO_STRONG_POLICY_WITHIN_H'}
FOLDER=Path(__file__).parent/'results/2026-10-16-relational-coverage'

def summarize(folder=FOLDER):
    primary=json.loads((folder/'analysis.json').read_text());stages=json.loads((folder/'stages/analysis.json').read_text())
    reference=json.loads((folder/'doors_reference.json').read_text())
    rows=primary['rows'];assert len(rows)==102 and len(stages['rows'])==16
    truths={'doors_5_sNone':reference['optimal_worst_case_depth']}
    old=json.loads((folder.parent/'2026-10-16-symbolic-coverage/analysis.json').read_text())['rows']
    checks=0
    for r in old+rows+stages['rows']:
        if r['status'] in SOLVED:
            key=r['config']['id'];value=r['value']
            if key in truths:assert truths[key]==value;checks+=1
            truths[key]=value
    for r in rows+stages['rows']:
        truth=truths.get(r['config']['id']);lb=r.get('root_lower')
        if truth is not None and truth!='infinity' and lb is not None:
            assert lb!='infinity' and lb<=truth;checks+=1
    result=dict(primary=[],stages=[],cross_result_checks=checks,api_calls=0,external_baseline_reruns=0)
    for mode in ('counts','lineage','matching'):
        selected=[r for r in rows if r['mode']==mode]
        result['primary'].append(dict(mode=mode,statuses=dict(Counter(r['status'] for r in selected)),
            completed=sum(r['status'] in SOLVED for r in selected),
            original_completed=sum(r['status'] in SOLVED and r['config']['cohort']=='original' for r in selected),
            resource_completed=sum(r['status'] in SOLVED and r['config']['cohort']!='original' for r in selected),
            relation_budget_exhausted=sum((r.get('statistics') or {}).get('coverage',{}).get('relation',{}).get('fallbacks',0)>0 for r in selected),
            peak_rss_kib_max=max((r.get('peak_rss_kib',0) for r in selected),default=0)))
    lookup={(r['config']['id'],r['mode']):r for r in rows}
    stronger=[];ratios=[]
    for c in primary['manifest']['cases']:
        left,right=lookup[c['id'],'counts'],lookup[c['id'],'matching']
        a,b=left.get('root_lower'),right.get('root_lower')
        if a is not None and b is not None and a!='infinity' and (b=='infinity' or b>a):stronger.append(dict(id=c['id'],counts=a,matching=b))
        if left['status'] in SOLVED and right['status'] in SOLVED:ratios.append(right['total_seconds']/left['total_seconds'])
    result['strict_root_improvements']=stronger
    result['paired_completed_timing']=dict(cases=len(ratios),median_matching_over_counts=median(ratios),
        min=min(ratios),max=max(ratios),scope='One timing each, descriptive only; timeouts excluded explicitly.')
    deductions=[]
    for r in rows:
        rel=(r.get('statistics') or {}).get('coverage',{}).get('relation',{})
        if rel.get('sibling_deduplications'):deductions.append(dict(id=r['config']['id'],mode=r['mode'],deduplications=rel['sibling_deduplications']))
    result['sibling_deduplication_activity']=deductions
    result['doors_reference']={k:v for k,v in reference.items() if k not in ('source','config','policy_certificate')}
    for mode in ('counts','matching'):
        selected=[r for r in stages['rows'] if r['mode']==mode]
        result['stages'].append(dict(mode=mode,completed=sum(r['status'] in SOLVED for r in selected),total=8,
            statuses=dict(Counter(r['status'] for r in selected))))
    result['interpretation']=('Candidate identity improves one navigation root bound from 12 to 23 (independent optimum 24), '
        'but no primary completion increase. Sibling matching has local effects, no additional completed tasks. '
        'Stage projection diagnostic is negative; broad low-cost navigation/operation search benefit is not established.')
    (folder/'summary.json').write_text(json.dumps(result,indent=2));return result

if __name__=='__main__':print(json.dumps(summarize(),indent=2))
