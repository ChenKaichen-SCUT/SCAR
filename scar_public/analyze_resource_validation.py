"""Primary frozen results; duplicate-aware summaries; audit repeats kept separate."""
import json,statistics
from collections import Counter
from pathlib import Path


def main():
    folder=Path(__file__).parent/'results/2026-10-16-resource-validation'
    first=json.loads((folder/'analysis.json').read_text())
    later=json.loads((folder/'witness/analysis.json').read_text())
    queries=json.loads((folder/'queries.json').read_text())
    audit=json.loads((folder/'source_audit.json').read_text())
    types=json.loads((folder/'type_audit.json').read_text())
    assert all(r['old_sha256']==r['new_sha256'] for r in types['rows'])
    rows=first['rows']+later['rows'];modes=first['manifest']['modes']+later['manifest']['modes']
    lookup={(r['config']['id'],r['mode']):r for r in rows}
    representatives={g[0] for g in audit['groups'].values()}
    def unique(r):return r['config']['source']!='fresh' or r['config']['folder'] in representatives
    def done(r):return r['status'] in ('PLAN_FOUND','NO_STRONG_POLICY_WITHIN_H')
    def seconds(r):return r['total_seconds']
    outcomes={}
    for mode in modes:
        subset=[r for r in rows if r['mode']==mode]
        outcomes[mode]=dict(all=dict(Counter(r['status'] for r in subset)),
            fresh_raw=dict(Counter(r['status'] for r in subset if r['config']['source']=='fresh')),
            fresh_deduplicated=dict(Counter(r['status'] for r in subset if r['config']['source']=='fresh' and unique(r))),
            development=dict(Counter(r['status'] for r in subset if r['config']['source']!='fresh')))
    for c in first['manifest']['cases']:
        complete=[lookup[c['id'],m] for m in modes if done(lookup[c['id'],m])]
        assert len({r['value'] for r in complete})<=1, c['id']
        for r in complete:
            if r['status']=='PLAN_FOUND':assert r['verified_policy_depth']==r['value']
    timing={}
    for mode in modes:
        pairs=[(r,lookup[r['config']['id'],'leaf']) for r in rows if r['mode']==mode and unique(r)]
        pairs=[(r,b) for r,b in pairs if done(r) and done(b)]
        fresh=[(r,b) for r,b in pairs if r['config']['source']=='fresh']
        timing[mode]=dict(common_completed=len(pairs),median_ratio_to_leaf=statistics.median(seconds(r)/seconds(b) for r,b in pairs),
            fresh_common_completed=len(fresh),fresh_median_ratio_to_leaf=statistics.median(seconds(r)/seconds(b) for r,b in fresh))
    focus=[]
    for mode in modes:
        r=lookup['rover4_a16s1',mode];t=r['statistics']['target_capacity'];c=t.get('coverage') or {}
        ref=c.get('refinement',{});amort=c.get('amortized',{})
        focus.append(dict(mode=mode,seconds=seconds(r),expanded=r['statistics']['search_expanded'],
            optional_seconds=t['seconds'],selection_seconds=amort.get('selection_seconds',ref.get('selection_seconds',0)),
            other_seconds=seconds(r)-t['seconds'],witness_gate=c.get('witness_gate'),
            relation_nodes=sum(b.get('relation',{}).get('nodes',0) for b in ref.get('children',[]))))
    separations=[]
    for r in queries['rows']:
        if r['status']=='SEPARATION':
            separations.append(dict(id=r['config']['id'],source=r['config']['source'],query=r['queries'][-1],
                controls={k:{x:v[x] for x in ('status','seconds','values','evidence') if x in v} for k,v in r['controls'].items()},
                complete_bound_scan_seconds=sum(q['seconds'] for q in r['queries'])+r['selection_seconds'],
                note='Last query timing has warm caches; compare cold total scan only with its declared broader work.'))
    result=dict(outcomes=outcomes,timing=timing,rover4_resource_focus=focus,separations=separations,
        root_statuses=dict(Counter(r['status'] for r in queries['rows'])),
        root_scan_endings=dict(Counter(r['queries'][-1]['status'] for r in queries['rows'] if r['queries'])),
        fresh_source_files=21,fresh_distinct_normalized=19,primary_configs=50,primary_unique_configs=46,
        first_stage_runs=len(first['rows']),witness_stage_runs=len(later['rows']),
        typing_audit_runs=36,typing_audit_primary=False,all_completed_values_agree=True,
        primary_policy_replays=sum(r['status']=='PLAN_FOUND' for r in rows),api_calls=0,
        limitations=['All new-source completed cases are bounded infeasibility results, not successful policies.',
            'One run per method/configuration; no statistical speed significance claim.',
            'Rover scale configurations are previously observed development cases.',
            'Second-stage witness variant is development on already inspected inputs.',
            'No reproduction of an external published resource-aware planner is claimed.',
            'Type audit repeats cannot inflate validation count or replace primary timings.'])
    (folder/'summary.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(dict(outcomes=outcomes,focus=focus,root_scan_endings=result['root_scan_endings']),indent=2))


if __name__=='__main__':main()
