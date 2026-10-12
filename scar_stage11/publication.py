"""Reconcile the original Stage11 publication without model calls or engines."""
import collections
import gzip
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from scar.io import atomic_json, digest

OUT = Path('results/stage11')
METHODS = ['E0', 'E1', 'E2', 'E3', 'E4']


def main():
    def load(name):
        return json.loads((OUT/(name+'.json')).read_text())

    freeze, cases, verification = load('freeze'), load('cases'), load('verification')
    by_case = {c['id']: c for c in cases}
    metrics, models = load('episode_metrics'), load('request_model_audit')
    prior_errors = [p for p, h in freeze['prior_file_hashes'].items()
                    if hashlib.sha256(Path(p).read_bytes()).hexdigest() != h]
    frozen_errors = [p for p, h in (freeze['code_hashes'] | freeze['data_hashes']).items()
                     if hashlib.sha256(Path(p).read_bytes()).hexdigest() != h]
    errors, totals, request_ids = [], {}, set()
    for method in METHODS:
        episodes = list(map(json.loads, gzip.open(OUT/f'trajectories_{method}.jsonl.gz', 'rt')))
        requests = [x['request'] for x in map(json.loads, gzip.open(OUT/f'requests_{method}.jsonl.gz', 'rt'))]
        mm = [m for m in metrics if m['algorithm'] == method]
        got = {
            'episodes': len(episodes), 'actions': sum(len(e['rows']) for e in episodes),
            'successes': sum(any(r['diagnostic_goal_reached'] for r in e['rows']) for e in episodes),
            'api_calls': len(requests), 'cost_usd': sum(r.get('cost_usd', 0) for r in requests),
            'tokens': sum((r.get('usage') or {}).get('prompt_tokens', 0)
                          +(r.get('usage') or {}).get('completion_tokens', 0) for r in requests),
            'request_statuses': dict(collections.Counter(r['status'] for r in requests)),
        }
        if (len(episodes) != 10 or {e['case_id'] for e in episodes} != set(by_case)
                or got['actions'] != sum(m['steps'] for m in mm)
                or got['successes'] != sum(m['recovery_at_40'] for m in mm)
                or abs(got['cost_usd']-sum(m['cost_usd'] for m in mm)) > 1e-8
                or got['tokens'] != sum(m['input_tokens']+m['output_tokens'] for m in mm)
                or got['api_calls'] != models[method]['requests']
                or models[method]['served_models'] != {'deepseek-flash': len(requests)}):
            errors.append({'method': method, 'kind': 'raw_statistic_mismatch'})
        for episode in episodes:
            case = by_case[episode['case_id']]
            if (len(episode['rows']) > 40 or episode['summary']['game'] != 'robot_kingdom'
                    or any(r['initial_state_hash'] != case['state_hash'] for r in episode['rows'])
                    or any(r['extra_repair_call'] for r in episode['rows'])):
                errors.append({'task_id': episode['task_id'], 'kind': 'scope_or_protocol'})
        for request in requests:
            if request['request_id'] in request_ids:
                errors.append({'method': method, 'kind': 'duplicate_request_id'})
            request_ids.add(request['request_id'])
        totals[method] = got

    actions = sum(t['actions'] for t in totals.values())
    cost = sum(t['cost_usd'] for t in totals.values())
    local = load('local_portable_replay')
    suites = list(ET.parse(OUT/'unit_tests.xml').getroot().iter('testsuite'))
    unit = {k: sum(int(s.attrib.get(k, 0)) for s in suites)
            for k in ['tests', 'failures', 'errors', 'skipped']}
    checks = {
        'complete': load('completion')['fully_complete'],
        'only_original_robot_10': len(cases) == 10 and all(c['game'] == 'robot_kingdom' and c['max_steps'] == 40 and c['cohort'] == 'development_old10' for c in cases),
        'dataset_digest_matches': digest(cases) == freeze['dataset_digest'],
        'physical_replay_passed': verification['passed'] and verification['episodes_replayed'] == 50
                                  and verification['actions_replayed'] == actions,
        'independent_local_replay_passed': local['passed'] and local['episodes_replayed'] == 50
                                          and local['actions_replayed'] == actions and local['api_calls'] == 0,
        'offline_gate_passed': load('offline_checks')['passed'],
        'integration_passed': load('integration_checks')['passed'],
        'mechanism_audit_passed': load('mechanism_audit_completion')['passed'],
        'bounds_passed': load('bounds_audit')['passed'],
        'prompt_fidelity_passed': load('prompt_fidelity')['passed'],
        'only_S1_backbone': all(r['only_S1_backbone'] for r in load('bounds_audit')['records']),
        'offline_scope_passed': load('offline_checks')['api_calls'] == 0
                                and load('offline_checks')['reference_decisions'] == 622
                                and load('offline_checks')['decision_checks'] == 6220
                                and load('offline_checks')['autonomous_rollouts'] == 72,
        'required_reports_present': all((Path('reports/stage11')/n).is_file()
              for n in ['实验报告.md', '复现指南.md', '逐例机制归因.md', '可重算统计表.md', '行动链.md']),
        'judgment_matches_raw_results': load('research_judgment')['successes'] ==
              {method: totals[method]['successes'] for method in METHODS},
        'no_paid_rerun': load('analysis_decisions')['paid_episode_reruns'] == 0,
        'no_post_freeze_policy_edits': not load('analysis_decisions')['policy_changed_after_freeze'],
        'unit_tests_passed': unit['tests'] == freeze['unit_tests'] == 118 and not any(unit[k] for k in ['failures', 'errors', 'skipped']),
        'accounting_passed': abs(cost-verification['new_ledger_usd']) < 1e-8
                             and abs(verification['request_ledger_difference']) < 1e-8
                             and not verification['pending_reservations'],
        'immutable_history_passed': not prior_errors and not frozen_errors,
        'raw_statistics_passed': not errors,
    }
    files = sorted(p for base in ['scar_stage11', 'results/stage11', 'reports/stage11']
                   for p in Path(base).rglob('*') if p.is_file() and '__pycache__' not in p.parts
                   and p.name not in {'publication_checks.json', 'artifact_manifest.json'})
    files += [Path('tests/test_stage11.py'), Path('configs/protocol_stage11.json')]
    patterns = [rb'sk-[A-Za-z0-9_-]{20,}', rb'gh[pousr]_[A-Za-z0-9]{20,}',
                rb'-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----']
    secret_bytes = []
    for path in [Path('/root/.scar-deepseek-key'), Path('/mnt/Space0/AINative/miyao.txt')]:
        if path.exists():
            secret_bytes.extend(value.strip().encode() for value in path.read_text().splitlines()
                                if len(value.strip()) > 12)
    leaks, unexpected, large = [], [], []
    allowed = {'.py', '.json', '.gz', '.csv', '.xml', '.md'}
    for path in files:
        data = path.read_bytes()
        if path.suffix not in allowed or path.is_symlink(): unexpected.append(str(path))
        if len(data) >= 100_000_000: large.append(str(path))
        if path.suffix == '.gz': data = gzip.decompress(data)
        if any(re.search(pattern, data) for pattern in patterns) or any(s in data for s in secret_bytes):
            leaks.append(str(path))
    checks.update(credential_scan_passed=not leaks, publication_file_scope_passed=not unexpected,
                  github_file_sizes_passed=not large)
    result = {
        'checks': checks, 'passed': all(checks.values()), 'protected_prior_files': len(freeze['prior_file_hashes']),
        'prior_file_mismatches': prior_errors, 'frozen_file_mismatches': frozen_errors,
        'statistic_mismatches': errors, 'credential_pattern_files': leaks,
        'unexpected_files': unexpected, 'oversize_files': large, 'unit_tests': unit,
        'raw_totals': totals, 'new_cost_usd': cost, 'files': len(files)+2,
        'artifact_scope': 'our Stage11 implementation and generated results; no downloaded engine, model, private ledger or credentials',
        'api_calls_in_publication_check': 0,
    }
    atomic_json(OUT/'publication_checks.json', result)
    if not result['passed']:
        raise AssertionError(result)
    files.append(OUT/'publication_checks.json')
    atomic_json(OUT/'artifact_manifest.json', {
        'files': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        'scope': result['artifact_scope']+'; excludes manifest itself',
    })
    print(json.dumps({'passed': True, 'files': len(files)+1, 'episodes': 50,
                      'actions': actions, 'new_cost_usd': cost}))


if __name__ == '__main__':
    main()
