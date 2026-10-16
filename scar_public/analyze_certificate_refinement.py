"""Verify frozen source hashes and separate scalar, identity and timing effects."""
import json, statistics
from collections import Counter
from hashlib import sha256
from pathlib import Path


def main():
    root = Path(__file__).parent; folder = root/'results/2026-10-16-certificate-refinement'
    a = json.loads((folder/'analysis.json').read_text())
    baseline = json.loads((root/'results/2026-10-16-decision-coverage/analysis.json').read_text())
    direct = json.loads((root/'results/2026-10-16-decision-coverage/direct/analysis.json').read_text())
    for name, digest in a['manifest']['sources'].items():
        assert sha256((root/name).read_text().encode()).hexdigest() == digest, name
    rows = a['rows']; modes = a['manifest']['modes']
    assert len(rows) == 78 and len({(r['config']['id'], r['mode']) for r in rows}) == 78
    by = {(r['config']['id'],r['mode']):r for r in baseline['rows']+direct['rows']+rows}
    done = {'PLAN_FOUND', 'NO_STRONG_POLICY_WITHIN_H'}
    for c in a['manifest']['cases']:
        values = {r['value'] for r in by.values() if r['config']['id']==c['id'] and r['status'] in done}
        assert len(values) <= 1, (c['id'],values)
    results = {}
    for mode in modes:
        subset = [r for r in rows if r['mode']==mode]
        target = [r['statistics']['target_capacity'] for r in subset if r.get('statistics')]
        counters = Counter()
        for t in target:
            counters.update({k:v for k,v in t['coverage']['refinement'].items() if type(v) in (int,float)})
        ratios = {}
        for ref in ('leaf','direct_gate'):
            times = [r['total_seconds']/by[r['config']['id'],ref]['total_seconds'] for r in subset
                if r['status'] in done and by[r['config']['id'],ref]['status'] in done]
            ratios[ref] = dict(n=len(times),median=statistics.median(times),min=min(times),max=max(times))
        results[mode] = dict(statuses=dict(Counter(r['status'] for r in subset)),
            cohorts={c:dict(Counter(r['status'] for r in subset if r['config']['cohort']==c))
                for c in sorted({r['config']['cohort'] for r in subset})},
            inference_seconds=sum(t['seconds'] for t in target),
            interruptions=sum(t['interrupted'] for t in target), refinement=dict(counters),time_ratios=ratios)
    cases = []
    for config in a['manifest']['cases']:
        case = dict(id=config['id'],cohort=config['cohort'],methods={})
        for mode in ('leaf','direct_gate')+tuple(modes):
            r = by[config['id'],mode]; t = (r.get('statistics') or {}).get('target_capacity',{})
            case['methods'][mode] = dict(status=r['status'],seconds=r.get('total_seconds'),
                expanded=(r.get('statistics') or {}).get('search_expanded'),
                optional_seconds=t.get('seconds'),refinement=(t.get('coverage') or {}).get('refinement'),
                prune_evidence=[e for e in t.get('evidence',[]) if e.get('reason','').startswith('refined_')
                    and 'prune' in e.get('reason','')])
        cases.append(case)
    mechanism = json.loads((folder/'mechanism_checks.json').read_text())
    queries = [q for c in mechanism['public'] for q in c['queries']]
    fixed = {m:dict(statuses=dict(Counter(q['methods'][m]['status'] for q in queries)),
        prunes=sum(q['methods'][m].get('prune',False) for q in queries)) for m in ('certificate','goal_first')}
    result = dict(runs=78,source_hashes_verified=True,completed_values_consistent=True,
        results=results,cases=cases,fixed_queries=len(queries),fixed_query_results=fixed,
        extra_completed_cases=[c['id'] for c in cases if c['methods']['leaf']['status'] not in done
            and c['methods']['refine_certificate']['status'] in done],
        api_calls=0,scope='Previously observed development cases, single-run descriptive timing. '
        'Baselines reused unchanged. Fixed queries selected post hoc to inspect mechanism, not to estimate average benefit.')
    (folder/'summary.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='cases'},indent=2))


if __name__ == '__main__':
    main()
