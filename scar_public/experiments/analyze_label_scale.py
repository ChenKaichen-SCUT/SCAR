"""Reproduce aggregate results without treating censoring as an exact runtime."""
import json,math,statistics
from collections import Counter
from pathlib import Path
from hashlib import sha256

def analyze(folder):
    rows=[json.loads(x) for x in (folder/'runs.jsonl').read_text().splitlines()]
    spec=json.loads((folder/'manifest.json').read_text())
    assert len(rows)==len(spec['cases'])*len(spec['modes'])
    keyed={(r['config']['id'],r['mode']):r for r in rows};assert len(keyed)==len(rows)
    solved=lambda r:r['status'] in ('PLAN_FOUND','NO_STRONG_POLICY_WITHIN_H')
    result=dict(raw_sha256=sha256((folder/'runs.jsonl').read_bytes()).hexdigest(),runs=len(rows),
        cases=len(spec['cases']),modes={},groups={},comparisons={},api_calls=0,
        inference='One run/configuration; no significance or confidence intervals. '
        'PAR2 charges twice the 30-second limit to supported unsolved cases. '
        'Unsupported cases are separately counted, never solved or assigned a zero time.')
    for mode in spec['modes']:
        rr=[r for r in rows if r['mode']==mode];valid=[r for r in rr if r['status']!='UNSUPPORTED_INPUT']
        reasons=Counter()
        for r in rr:
            reasons.update(e['reason'] for e in (r.get('statistics') or {}).get('target_capacity',{}).get('evidence',[]))
        result['modes'][mode]=dict(statuses=dict(Counter(r['status'] for r in rr)),completed=sum(map(solved,rr)),
            par2_supported=sum(r['total_seconds'] if solved(r) else 60 for r in valid)/len(valid),
            target_reasons=dict(reasons),capacity_seconds=sum((r.get('statistics') or {}).get('target_capacity',{}).get('seconds',0) for r in rr))
        for overlay in ('original','a16s1'):
            selected=[r for r in rr if r['config']['overlay']==overlay]
            result['groups'][mode+'_'+overlay]=dict(statuses=dict(Counter(r['status'] for r in selected)),completed=sum(map(solved,selected)))
    for mode in ('leaf','resource_pair','resource_tree','amortized_count'):
        pairs=[(keyed[c['id'],mode],keyed[c['id'],'amortized_relation']) for c in spec['cases']]
        joint=[(a,b) for a,b in pairs if solved(a) and solved(b)]
        result['comparisons'][mode]=dict(joint_completed=len(joint),
            joint_geomean_speedup=math.exp(statistics.mean(math.log(a['total_seconds']/b['total_seconds']) for a,b in joint)),
            new_completed=[b['config']['id'] for a,b in pairs if solved(b) and not solved(a)],
            lost_completed=[a['config']['id'] for a,b in pairs if solved(a) and not solved(b)],
            disagreements=[a['config']['id'] for a,b in joint if a['value']!=b['value']])
        assert not result['comparisons'][mode]['disagreements']
    assert all(r.get('verified_policy_depth')==r['value'] for r in rows if r['status']=='PLAN_FOUND')
    result['verified_policies']=sum(r['status']=='PLAN_FOUND' for r in rows)
    result['representatives']={c:{m:dict(status=keyed[c,m]['status'],seconds=keyed[c,m].get('total_seconds'),
        depth=keyed[c,m].get('value'),expansions=(keyed[c,m].get('statistics') or {}).get('search_expanded'))
        for m in spec['modes']} for c in ('lug_bt_20_original','lug_btc_20_original','lug_btc_8_a16s1','lug_ring_4_a16s1','lug_medicalPKS_12_original')}
    (folder/'summary.json').write_text(json.dumps(result,indent=2))
    compact=[]
    for r in rows:
        s=r.get('statistics') or {};target=s.get('target_capacity',{})
        compact.append(dict(id=r['config']['id'],mode=r['mode'],status=r['status'],value=r.get('value'),
            total_seconds=r.get('total_seconds'),parse_seconds=r.get('parse_seconds'),
            root_seconds=r.get('root_seconds'),search_seconds=r.get('search_seconds'),
            expansions=s.get('search_expanded'),coverage_seconds=target.get('seconds'),
            prunes=target.get('prunes'),reason_counts=dict(Counter(e['reason'] for e in target.get('evidence',[]))),
            active_phase=r.get('active_phase'),metadata=r.get('metadata'),error=r.get('message'),
            verified_policy_depth=r.get('verified_policy_depth')))
    (folder/'runs_summary.json').write_text(json.dumps(compact,indent=2))
    return result

if __name__=='__main__':
    import sys
    r=analyze(Path(sys.argv[1]));print(json.dumps(dict(modes=r['modes'],comparisons=r['comparisons']),indent=2))
