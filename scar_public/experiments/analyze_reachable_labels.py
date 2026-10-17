"""Validate all saved outcomes and attribute gains to the correct comparison."""
import argparse, json, math
from collections import Counter
from hashlib import sha256
from pathlib import Path

COMPLETE = {'PLAN_FOUND', 'NO_STRONG_POLICY_WITHIN_H'}


def analyze(source, output):
    output.mkdir(parents=True, exist_ok=True)
    spec = json.loads((source/'manifest.json').read_text())
    raw = source/'runs.jsonl'; rows = [json.loads(x) for x in raw.read_text().splitlines()]
    assert len(rows) == len(spec['cases'])*len(spec['modes'])
    keyed = {(r['config']['id'], r['mode']): r for r in rows}
    assert len(keyed) == len(rows)
    compact = []
    for r in rows:
        s = r.get('statistics') or {}; target = s.get('target_capacity', {})
        coverage = target.get('coverage') or {}
        evidence = target.get('evidence', [])
        for e in evidence:
            if e['reason'] == 'relation_prune':
                assert e['scalar'] >= e['candidates'] > e['identity_capacity']
            elif e['reason'] == 'scalar_prune':
                assert e['scalar'] < e['candidates']
        selected = sorted({json.dumps(e.get('selected_atoms', []), sort_keys=True) for e in evidence})
        if r['status'] == 'PLAN_FOUND':
            assert r['verified_policy_depth'] == r['value']
        compact.append(dict(id=r['config']['id'], mode=r['mode'], status=r['status'], value=r.get('value'),
            total_seconds=r.get('total_seconds'), elapsed_seconds=r.get('elapsed_seconds'),
            parse_seconds=r.get('parse_seconds'), construct_seconds=r.get('construct_seconds'),
            search_seconds=r.get('search_seconds'), expansions=s.get('search_expanded'),
            capacity_seconds=target.get('seconds', 0), target_prunes=target.get('prunes', 0),
            interrupted=target.get('interrupted', 0), decisions=target.get('decisions'),
            reason_counts=dict(Counter(e['reason'] for e in evidence)), selected_projections=selected,
            carrier=coverage.get('progress_carrier'), closure=coverage.get('reachable_labels'),
            assembly=coverage.get('labelled_channels'), amortized=coverage.get('amortized'),
            metadata=r.get('metadata'), verified_policy_depth=r.get('verified_policy_depth')))
    result = dict(runs=len(rows), cases=len(spec['cases']), raw_sha256=sha256(raw.read_bytes()).hexdigest(),
        verified_policies=sum(r['status'] == 'PLAN_FOUND' for r in rows), methods={}, comparisons={},
        validation='All completed methods agree on bounded optimum; all returned policies replayed.',
        timing='One run, soft inference budgets, 30s hard subprocess limit; no significance claim.', api_calls=0)
    for c in spec['cases']:
        values = {keyed[c['id'], m]['value'] for m in spec['modes'] if keyed[c['id'], m]['status'] in COMPLETE}
        assert len(values) <= 1, (c['id'], values)
    for mode in spec['modes']:
        rr = [r for r in compact if r['mode'] == mode]
        result['methods'][mode] = dict(statuses=dict(Counter(r['status'] for r in rr)),
            completed=sum(r['status'] in COMPLETE for r in rr),
            capacity_seconds=sum(r['capacity_seconds'] for r in rr),
            scalar_prunes=sum((r.get('amortized') or r.get('decisions') or {}).get('scalar_prunes', 0) for r in rr),
            relation_prunes=sum((r.get('amortized') or r.get('decisions') or {}).get('relation_prunes', 0) for r in rr))
    for first, second in (('reachable_count', 'reachable_relation'), ('carrier_count', 'carrier_relation'),
            ('amortized_count', 'amortized_relation'), ('amortized_relation', 'carrier_relation')):
        if first not in spec['modes'] or second not in spec['modes']:
            continue
        pairs = [(keyed[c['id'], first], keyed[c['id'], second]) for c in spec['cases']]
        joint = [(a, b) for a, b in pairs if a['status'] in COMPLETE and b['status'] in COMPLETE]
        result['comparisons'][first+'__'+second] = dict(joint_completed=len(joint),
            geomean_speedup_second=math.exp(sum(math.log(a['total_seconds']/b['total_seconds']) for a, b in joint)/len(joint)) if joint else None,
            new_completed=[b['config']['id'] for a, b in pairs if b['status'] in COMPLETE and a['status'] not in COMPLETE],
            lost_completed=[a['config']['id'] for a, b in pairs if a['status'] in COMPLETE and b['status'] not in COMPLETE])
    (output/'summary.json').write_text(json.dumps(result, indent=2))
    (output/'runs_summary.json').write_text(json.dumps(compact, indent=2))
    for name in ('manifest.json', 'environment.json'):
        (output/name).write_bytes((source/name).read_bytes())
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('source', type=Path); p.add_argument('output', type=Path)
    a = p.parse_args(); print(json.dumps(analyze(a.source, a.output), indent=2))
