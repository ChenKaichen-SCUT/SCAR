"""Account for every sparse-policy run, including costs and failed experiments."""
import argparse, json, math
from collections import Counter
from pathlib import Path
from scar_public.experiments.analyze_reachable_labels import analyze, COMPLETE


def main():
    p=argparse.ArgumentParser();p.add_argument('evidence',type=Path);p.add_argument('previous',type=Path)
    p.add_argument('output',type=Path);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    rows=[];summaries={};cores=[];compact=[]
    for suite in ('results_dev','results_reused','results_scale'):
        source=a.evidence/'v1'/suite
        summaries[suite]=analyze(source,a.output/suite)
        rr=[json.loads(line) for line in (source/'runs.jsonl').read_text().splitlines()]
        cc=json.loads((a.output/suite/'runs_summary.json').read_text())
        bykey={(r['id'],r['mode']):r for r in cc}
        for r in rr:
            target=(r.get('statistics') or {}).get('target_capacity') or {}
            sparse=(target.get('coverage') or {}).get('sparse_policy') or {}
            bykey[r['config']['id'],r['mode']]['sparse_policy']=sparse
            if sparse:
                assert len(sparse['cores'])==sparse['prunes'], 'core log cap reached'
                for c in sparse['cores']:
                    assert c['certificate']['members'] and c['upper']<c['candidates']
                    cores.append(dict(id=r['config']['id'],mode=r['mode'],certificate=c))
            r['suite']=suite
        (a.output/suite/'runs_summary.json').write_text(json.dumps(cc,indent=2))
        compact+=cc;rows+=rr
    old=[]
    for f in (a.previous/'v2').glob('*/runs.jsonl'):
        old += [json.loads(line) for line in f.read_text().splitlines()]
    values={}
    for r in rows+old:
        if r['status'] in COMPLETE:values.setdefault(r['config']['id'],set()).add(r['value'])
    assert all(len(v)==1 for v in values.values()),'Cross-version optimum mismatch'
    comparisons={}
    def compare(label,first,second):
        aa={r['config']['id']:r for r in first};bb={r['config']['id']:r for r in second}
        ids=sorted(aa.keys()&bb.keys());joint=[i for i in ids if aa[i]['status'] in COMPLETE and bb[i]['status'] in COMPLETE]
        comparisons[label]=dict(configurations=len(ids),joint_completed=len(joint),
            geomean_speedup_second=math.exp(sum(math.log(aa[i]['total_seconds']/bb[i]['total_seconds']) for i in joint)/len(joint)) if joint else None,
            new_completed=[i for i in ids if aa[i]['status'] not in COMPLETE and bb[i]['status'] in COMPLETE],
            lost_completed=[i for i in ids if aa[i]['status'] in COMPLETE and bb[i]['status'] not in COMPLETE],
            rows=[dict(id=i,first=aa[i]['total_seconds'],second=bb[i]['total_seconds'],
                speedup=aa[i]['total_seconds']/bb[i]['total_seconds']) for i in joint])
    ours=[r for r in rows if r['mode']=='sparse_policy']
    for mode in ('sparse_fresh','sparse_full'):
        compare(mode+'__sparse_policy',[r for r in rows if r['mode']==mode],ours)
    for mode in ('compact_count','resource_tree','amortized_relation'):
        compare('previous_'+mode+'__sparse_policy',[r for r in old if r['mode']==mode],ours)
    methods={}
    for mode in ('sparse_policy','sparse_fresh','sparse_full'):
        rr=[r for r in compact if r['mode']==mode];ss=[r['sparse_policy'] for r in rr]
        methods[mode]=dict(statuses=dict(Counter(r['status'] for r in rr)),
            **{k:sum(s.get(k,0) for s in ss) for k in ('queries','prunes','rule_hits','interrupted','seconds','build_seconds','sat_seconds','added_links')},
            sufficient_core_sizes=dict(Counter(len(c['certificate']['members']) for s in ss for c in s.get('cores',[]))))
    summary=dict(runs=len(rows),configurations=len({r['config']['id'] for r in rows}),
        verified_policies=sum(r['status']=='PLAN_FOUND' for r in rows),
        statuses=dict(Counter(r['status'] for r in rows)),methods=methods,comparisons=comparisons,
        cross_version_completed_optima_agree=True,api_calls=0,manuscript_changed=False,
        limitation='All inputs reused development cases; one run per method/configuration, same soft budgets. '
        'Core size is sufficient, not necessarily minimum. Timeout is not infeasibility. '
        'New sparse proof strength must not be inferred from old coarse prunes. '
        'Timing comparisons with previous versions reuse frozen results and are descriptive, not significance tests.')
    (a.output/'validation.json').write_text(json.dumps(summary,indent=2))
    (a.output/'sparse_certificates.json').write_text(json.dumps(cores,indent=2))
    print(json.dumps({k:v for k,v in summary.items() if k!='comparisons'},indent=2))


if __name__=='__main__':main()
