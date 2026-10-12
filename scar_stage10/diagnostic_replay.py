"""Replay both published knowledge-diagnostic branches without server runtime."""
import argparse
import contextlib
import gzip
import hashlib
import json
from pathlib import Path

from scar.io import atomic_json
from scar_unknown17.audit import branch

OUT = Path('results/stage10')


def main(output):
    cases = {c['id']: c for c in json.loads((OUT/'cases.json').read_text())}
    records = json.loads((OUT/'knowledge_counterfactuals.json').read_text())['records']
    checks = []
    with open('/dev/null', 'w') as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        for record in records:
            raw = gzip.decompress(Path(record['state']['path']).read_bytes())
            assert hashlib.sha256(raw).hexdigest() == record['state']['serialized_sha256']
            for label, expected in record['branches'].items():
                assert record['index']+len(expected['actions']) <= 40
                got = branch(raw, expected['actions'], cases[record['case_id']])
                matches = (got['final_hash'] == expected['final_hash'] and got['goal'] == expected['goal']
                           and len(got['trace']) == len(expected['trace']))
                fields = ['state_hash', 'goal', 'semantic_rejection', 'after']
                for new, old in zip(got['trace'], expected['trace'], strict=True):
                    matches = matches and all(new[k] == old[k] for k in fields)
                checks.append({'task_id': record['task_id'], 'index': record['index'], 'branch': label,
                               'steps': len(got['trace']), 'replayed_twice': True, 'passed': matches})
    result = {'states': len(records), 'branches': len(checks), 'checks': checks,
              'api_calls': 0, 'passed': all(c['passed'] for c in checks)}
    atomic_json(Path(output), result)
    print(json.dumps({k: v for k, v in result.items() if k != 'checks'}))
    assert result['passed']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--output', required=True)
    main(parser.parse_args().output)
