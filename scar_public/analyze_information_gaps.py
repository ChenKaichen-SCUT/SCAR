"""Reproduce cohort counts and cost comparisons without dropping failed cases."""
import json,statistics
from collections import Counter
from hashlib import sha256
from pathlib import Path


def main():
    root=Path(__file__).parent;folder=root/'results/2026-10-17-information-gaps'
    a=json.loads((folder/'analysis.json').read_text());rows=a['rows'];spec=a['manifest']
    assert len(rows)==234 and len({(r['config']['id'],r['mode']) for r in rows})==234
    for name,digest in spec['sources'].items():
        assert sha256((root/name).read_text().encode()).hexdigest()==digest,name
    completed={'PLAN_FOUND','NO_STRONG_POLICY_WITHIN_H'}
    groups={};ratios={};disagreements=[]
    for cohort in sorted({r['config']['cohort'] for r in rows}):
        groups[cohort]={m:dict(Counter(r['status'] for r in rows
            if r['config']['cohort']==cohort and r['mode']==m)) for m in spec['modes']}
    for c in spec['cases']:
        values={r['value'] for r in rows if r['config']['id']==c['id'] and r['status'] in completed}
        if len(values)>1:disagreements.append(dict(id=c['id'],values=list(values)))
    assert not disagreements
    bykey={(r['config']['id'],r['mode']):r for r in rows}
    for m in spec['modes']:
        rr=[]
        for c in spec['cases']:
            if c['cohort']=='old_failure_diagnostic':continue
            base=bykey[c['id'],'leaf'];r=bykey[c['id'],m]
            if r['status'] in completed and base['status'] in completed:
                rr.append(r['total_seconds']/base['total_seconds'])
        ratios[m]=dict(n=len(rr),median=statistics.median(rr),maximum=max(rr))
    costs=[dict(id=r['config']['id'],cohort=r['config']['cohort'],mode=r['mode'],
        status=r['status'],seconds=r.get('total_seconds',r.get('elapsed_seconds')),
        expanded=(r.get('statistics') or {}).get('search_expanded'),
        control=(r.get('statistics') or {}).get('cost_control'),
        information=(r.get('statistics') or {}).get('information_control')) for r in rows]
    external=json.loads((folder/'external_process/analysis.json').read_text())
    post=json.loads((folder/'transition_diagnostic/analysis.json').read_text())
    summary=dict(main_runs=len(rows),frozen_source_hashes_verified=True,
        cohort_counts=groups,completed_value_disagreements=disagreements,
        new_completed_time_ratios_to_leaf=ratios,
        exclusions=[dict(id=r['config']['id'],reason=r.get('message')) for r in rows
            if r['mode']=='leaf' and r['status']=='UNSUPPORTED_INPUT'],
        main_costs=costs,external_counts=dict(Counter(r['status'] for r in external['rows'])),
        external_scope=external['manifest']['scope'],
        postholdout=[dict(id=r['config']['id'],mode=r['mode'],status=r['status'],
            seconds=r.get('total_seconds',r.get('elapsed_seconds')),statistics=r['statistics']) for r in post['rows']],
        new_original_unique_lineage_completions=[r['config']['id'] for r in rows
            if r['config']['cohort']=='new_public_original' and r['mode']=='leaf_lineage_scheduled'
            and r['status'] in completed and bykey[r['config']['id'],'leaf']['status'] not in completed],
        notes='Single deterministic runs. CFF is satisficing and raw-dialect-only, not an optimality control. '
            'Post-holdout diagnostics are exploratory and excluded from main cohort coverage.',api_calls=0)
    (folder/'summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps({k:v for k,v in summary.items() if k not in ('main_costs','postholdout')},indent=2))


if __name__=='__main__':main()
