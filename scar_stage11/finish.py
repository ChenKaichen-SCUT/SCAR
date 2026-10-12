"""Finite zero-API statistical audit of an already completed closed-loop batch.

Run in a separate checkout when reproducing: the analysis modules write to
results/stage11. Original narrative judgments and post-hoc diagnostic suffixes
are deliberately not reapplied to an independent stochastic experiment.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from scar.io import atomic_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', required=True)
    parser.add_argument('--workers', type=int, default=8)
    args = parser.parse_args()
    root = Path(args.runtime)
    if args.workers < 1:
        parser.error('--workers must be positive')
    tasks = json.loads((root/'tasks.json').read_text())
    if len(tasks) != 50 or any(t['game'] != 'robot_kingdom' for t in tasks):
        raise ValueError('Expected the frozen 50-episode Robot Kingdom batch')
    terminal = {'completed', 'method_abort', 'failed', 'worker_failed'}
    for task in tasks:
        path = root/'runs'/task['task_id']/'status.json'
        if not path.exists() or json.loads(path.read_text())['status'] not in terminal:
            raise ValueError(f'Batch is not terminal: {task["task_id"]}')
    for module in ['failure_audit', 'evaluate', 'analyze', 'verify']:
        atomic_json(root/'finish_status.json', {'phase': module, 'api_calls_in_postprocess': 0})
        command = [sys.executable, '-m', 'scar_stage11.'+module, '--runtime', str(root)]
        if module in {'evaluate', 'verify'}:
            command += ['--workers', str(args.workers)]
        subprocess.run(command, check=True)
    atomic_json(root/'finish_status.json', {
        'phase': 'verified_statistics_ready', 'api_calls_in_postprocess': 0,
        'narrative': 'Independently interpret new outcomes; original research judgment was not regenerated.'})


if __name__ == '__main__':
    main()
