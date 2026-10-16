"""Audit and summarize all frozen stages; never replace timeouts by late answers."""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from statistics import median

ROOT=Path(__file__).parent
FOLDER=ROOT/'results/2026-10-16-threshold-search'
SOLVED={'PLAN_FOUND','NO_STRONG_POLICY_WITHIN_H'}


def statistics(rows):
    result=[]
    for key in sorted({(r['mode'],r.get('node_limit')) for r in rows},key=str):
        chosen=[r for r in rows if (r['mode'],r.get('node_limit'))==key]
        result.append(dict(mode=key[0],node_limit=key[1],total=len(chosen),
            completed=sum(r['status'] in SOLVED for r in chosen),
            statuses=dict(Counter(r['status'] for r in chosen)),
            originals=sum(r['status'] in SOLVED and r['config']['cohort']=='original' for r in chosen),
            extensions=sum(r['status'] in SOLVED and r['config']['cohort']!='original' for r in chosen),
            max_peak_rss_kib=max(r.get('peak_rss_kib',0) for r in chosen)))
    return result


def selected(rows,identity):
    return [dict(mode=r['mode'],node_limit=r.get('node_limit'),status=r['status'],
        value=r.get('value'),root=r.get('root_lower'),total_seconds=r.get('total_seconds'),
        root_seconds=r.get('root_seconds'),expanded=(r.get('statistics') or {}).get('search_expanded'),
        relation_nodes=((r.get('statistics') or {}).get('coverage') or {}).get('relation',{}).get('nodes'))
        for r in rows if r['config']['id']==identity]


def analyze(folder=FOLDER):
    locations={'primary':'','demand':'demand','resource_keys':'resource_keys',
        'budget_sweep':'budget_sweep','uniform_budget':'uniform_budget'}
    studies={name:json.loads((folder/path/'analysis.json').read_text()) for name,path in locations.items()}
    expected={'primary':204,'demand':102,'resource_keys':48,'budget_sweep':6,'uniform_budget':68}
    source_checks=0
    for name,study in studies.items():
        assert len(study['rows'])==expected[name]
        for path,digest in study['manifest']['sources'].items():
            assert sha256((ROOT/path).read_text().encode()).hexdigest()==digest,(name,path)
            source_checks+=1
    # Independent exact reference/certificate and all previously completed roots.
    truths={'doors_5_sNone':24,'doors_5_s4':'infinity'}
    older=[]
    for name in ('2026-10-16-symbolic-coverage','2026-10-16-relational-coverage'):
        older+=json.loads((folder.parent/name/'analysis.json').read_text())['rows']
    rows=[r for s in studies.values() for r in s['rows']]
    checks=0
    for r in older+rows:
        if r['status'] in SOLVED:
            key=r['config']['id'];value=r['value']
            if key in truths:assert truths[key]==value,(key,value,truths[key]);checks+=1
            truths[key]=value
            if r in rows and r['status']=='PLAN_FOUND':assert r['verified_policy_depth']==value
    for r in rows:
        value=truths.get(r['config']['id']);lower=r.get('root_lower')
        if value is not None and value!='infinity' and lower is not None:
            assert lower!='infinity' and lower<=value;checks+=1
    # Compare a uniform-budget method against the explicitly reused counts pool.
    controls=[r for r in studies['demand']['rows'] if r['mode']=='threshold_counts'
        and r['config']['cohort']=='original']
    controls += [r for r in studies['resource_keys']['rows'] if r['mode']=='threshold_counts']
    assert len(controls)==34
    byid={r['config']['id']:r for r in controls}
    comparisons=[]
    for mode in ('threshold_lineage','threshold_matching'):
        treatment=[r for r in studies['uniform_budget']['rows'] if r['mode']==mode]
        gains=[];losses=[];ratios=[]
        for r in treatment:
            left=byid[r['config']['id']]
            if left['status'] not in SOLVED and r['status'] in SOLVED:gains.append(r['config']['id'])
            if left['status'] in SOLVED and r['status'] not in SOLVED:losses.append(r['config']['id'])
            if left['status'] in SOLVED and r['status'] in SOLVED:
                ratios.append(r['total_seconds']/left['total_seconds'])
        comparisons.append(dict(mode=mode,newly_completed=gains,lost_completed=losses,
            jointly_completed=len(ratios),median_time_ratio=median(ratios),
            min_time_ratio=min(ratios),max_time_ratio=max(ratios),
            caveat='Reused single measurements; empty-resource wrapper differs for original tasks; no significance claim.'))
    result=dict(stages={name:statistics(s['rows']) for name,s in studies.items()},
        total_timed_runs=sum(expected.values()),source_hash_checks=source_checks,
        cross_result_checks=checks,uniform_budget_comparison=comparisons,
        reused_counts=statistics(controls),api_calls=0,external_or_game_baseline_reruns=0,
        cases={identity:{name:selected(s['rows'],identity) for name,s in studies.items()}
            for identity in ('doors_5_sNone','doors_5_s4','rovers_pfile4_sNone')},
        unresolved={mode:[r['config']['id'] for r in studies['uniform_budget']['rows']
            if r['mode']==mode and r['status'] not in SOLVED]
            for mode in ('threshold_lineage','threshold_matching')})
    (folder/'summary.json').write_text(json.dumps(result,indent=2))
    return result


if __name__=='__main__':print(json.dumps(analyze(),indent=2))
