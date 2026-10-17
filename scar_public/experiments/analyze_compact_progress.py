"""Rebuild compact-progress summaries from immutable full-run evidence."""
import argparse, json, math
from collections import Counter
from pathlib import Path
from scar_public.experiments.analyze_reachable_labels import analyze, COMPLETE


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('evidence', type=Path)
    parser.add_argument('output', type=Path); args = parser.parse_args()
    batches = {}; all_rows = []; certificates = []
    for version in ('v1', 'v2', 'v3'):
        suites = ('results_dev', 'results_reused', 'results_scale') if version == 'v2' else ('results_dev', 'results_reused')
        for suite in suites:
            name = version+'_'+suite
            source = args.evidence/version/suite
            summary = analyze(source, args.output/name)
            rows = [json.loads(x) for x in (source/'runs.jsonl').read_text().splitlines()]
            compact = json.loads((args.output/name/'runs_summary.json').read_text())
            by_key = {(r['id'], r['mode']): r for r in compact}
            for row in rows:
                target = (row.get('statistics') or {}).get('target_capacity') or {}
                coverage = target.get('coverage') or {}
                by_key[row['config']['id'], row['mode']].update(
                    compact_progress=coverage.get('compact_progress'),
                    factored_progress=coverage.get('factored_progress'),
                    incremental_pool=coverage.get('incremental_pool'))
                for e in target.get('evidence', []):
                    if e['reason'] == 'relation_prune':
                        certificates.append(dict(batch=name, id=row['config']['id'], mode=row['mode'], evidence=e))
                row['batch'] = name
            (args.output/name/'runs_summary.json').write_text(json.dumps(compact, indent=2))
            batches[name] = summary; all_rows += rows
    by_id = {}
    for r in all_rows:
        if r['status'] in COMPLETE:
            by_id.setdefault(r['config']['id'], set()).add(r['value'])
    assert all(len(v) == 1 for v in by_id.values()), 'Cross-version optimum mismatch'
    def compare(first_version, first_mode, second_version, second_mode):
        a = {r['config']['id']: r for r in all_rows if r['batch'].startswith(first_version+'_') and r['mode'] == first_mode and 'scale' not in r['batch']}
        b = {r['config']['id']: r for r in all_rows if r['batch'].startswith(second_version+'_') and r['mode'] == second_mode and 'scale' not in r['batch']}
        ids = sorted(a.keys() & b.keys())
        joint = [i for i in ids if a[i]['status'] in COMPLETE and b[i]['status'] in COMPLETE]
        return dict(configurations=len(ids), joint_completed=len(joint),
            geomean_speedup_second=math.exp(sum(math.log(a[i]['total_seconds']/b[i]['total_seconds']) for i in joint)/len(joint)),
            new_completed=[i for i in ids if a[i]['status'] not in COMPLETE and b[i]['status'] in COMPLETE],
            lost_completed=[i for i in ids if a[i]['status'] in COMPLETE and b[i]['status'] not in COMPLETE])
    comparisons = {}
    for va, ma, vb, mb in (('v1','compact_relation','v2','compact_relation'),
            ('v2','compact_count','v2','compact_relation'),
            ('v2','compact_count','v3','factored_relation'),
            ('v2','compact_count','v3','factored_continue'),
            ('v3','compact_continue','v3','factored_continue')):
        comparisons[f'{va}/{ma}__{vb}/{mb}'] = compare(va, ma, vb, mb)
    summary = dict(runs=len(all_rows), configurations=len({r['config']['id'] for r in all_rows}),
        statuses=dict(Counter(r['status'] for r in all_rows)),
        verified_policies=sum(r['status']=='PLAN_FOUND' for r in all_rows),
        relation_certificates=len(certificates), comparisons=comparisons,
        api_calls=0, manuscript_changed=False,
        scope='One run per version/method/configuration. V1/V2/V3 development inputs reused. '
            'Only V2 scale input filenames newly selected before their outcomes; same generator families. '
            'V3 continuation was developed after the Ring diagnostic. No independent V3 validation claim. '
            'Statistics include all preprocessing and optional inference; timeouts are not proof of impossibility.')
    (args.output/'validation.json').write_text(json.dumps(summary, indent=2))
    (args.output/'relation_certificates.json').write_text(json.dumps(certificates, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
