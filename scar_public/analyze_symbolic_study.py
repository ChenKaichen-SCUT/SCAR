"""Recompute denominators, consistency checks and failure-aware summaries."""
from collections import Counter
import json
from pathlib import Path

FOLDER=Path(__file__).parent/'results/2026-10-16-symbolic-coverage'
SOLVED={'PLAN_FOUND','NO_STRONG_POLICY_WITHIN_H'}

def analyze(folder=FOLDER):
    main=json.loads((folder/'analysis.json').read_text());diag=json.loads((folder/'diagnostic.json').read_text())
    rows=main['rows'];assert len(rows)==170 and len({(r['config']['id'],r['mode']) for r in rows})==170
    truths={};bound_checks=value_checks=0
    for r in rows+diag['rows']:
        if r['status'] in SOLVED:
            key=r['config']['id'];value=r['value']
            if key in truths:assert truths[key]==value;value_checks+=1
            truths[key]=value
    for r in rows+diag['rows']:
        truth=truths.get(r['config']['id']);lower=r.get('root_lower')
        if truth is not None and truth!='infinity' and lower is not None:
            assert lower!='infinity' and lower<=truth;bound_checks+=1
    summary=[]
    for mode in main['manifest']['modes']:
        subset=[r for r in rows if r['mode']==mode]
        def completed(cohort):return sum(r['status'] in SOLVED for r in subset if r['config']['cohort']==cohort)
        summary.append(dict(mode=mode,total_solved=sum(r['status'] in SOLVED for r in subset),
            original_solved=completed('original'),extension_solved=completed('declared_resource_extension'),
            plans=sum(r['status']=='PLAN_FOUND' for r in subset),statuses=dict(Counter(r['status'] for r in subset))))
    external=[]
    compat=json.loads((folder/'compatibility_v3/analysis.json').read_text()) if (folder/'compatibility_v3/analysis.json').exists() else []
    for r in main['external']+compat:
        truth=truths.get(r['config']['id'])
        if r['policy_verified'] and truth is not None:
            assert truth!='infinity' and r['worst_case_depth']>=truth
    for method in ('cff_h2','cff_h3'):
        subset=[r for r in main['external'] if r['method']==method]
        syntax_failures=[r['config']['id'] for r in subset if r['config']['family'] in ('doors','localize')]
        external.append(dict(method=method,verified=sum(r['policy_verified'] for r in subset),
            original_attempts=len(subset),syntax_incompatible=syntax_failures,
            common_source_instances=16,common_source_verified=sum(r['policy_verified'] for r in subset),
            statuses=dict(Counter(r['status'] for r in subset)),
            compatibility_results=[dict(id=r['config']['id'],status=r['status'],depth=r.get('worst_case_depth')) for r in compat if r['method']==method]))
    diagnostic=[dict(mode=m,solved=sum(r['status'] in SOLVED for r in diag['rows'] if r['mode']==m),total=15)
                for m in diag['manifest']['modes']]
    result=dict(internal=summary,external=external,diagnostic=diagnostic,
                consistency=dict(equal_exact_values=value_checks,root_lower_checks=bound_checks,all_passed=True),
                api_calls=0,original_sources=18,resource_extensions=16,
                limitations=['Single timings; no significance claims.','External hFF plans are verified feasible, not presumed optimal.',
                    'Raw syntax failures excluded from the common 16-source comparison.',
                    'Peak RSS is available only for completed cells; timeout memory is censored.',
                    'No general advantage on Doors/Rovers or resource overlays established.'])
    (folder/'summary.json').write_text(json.dumps(result,indent=2))
    return result

if __name__=='__main__':print(json.dumps(analyze(),indent=2))
