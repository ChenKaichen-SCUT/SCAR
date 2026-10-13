"""Exactly one process per game/method. Completed failures are never rerun."""
import argparse
import concurrent.futures
import json
import subprocess
import sys
from pathlib import Path
from scar.io import atomic_json
from .config import ROOT, RESULTS, SCHEDULE
from .run import check_freeze, read


def job(entry, runtime):
    game, method = entry
    path = RESULTS / 'runs' / f'{game}__{method}' / 'summary.json'
    if path.exists(): return read(path)
    logs = runtime / 'logs'
    logs.mkdir(parents=True, exist_ok=True)
    with (logs / f'{game}__{method}.log').open('a') as stream:
        result = subprocess.run([sys.executable, '-m', 'scar_stage22.run', '--game', game,
                                 '--method', method, '--runtime', str(runtime)],
                                 cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
    if not path.exists():
        return dict(game=game, method=method, status='worker_crash', exit_code=result.returncode)
    return read(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runtime', required=True)
    args = parser.parse_args()
    check_freeze()
    completed = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        futures = [pool.submit(job, row, Path(args.runtime)) for row in SCHEDULE]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            completed.append(result)
            atomic_json(RESULTS / 'batch_progress.json', dict(finished=len(completed), total=15, runs=completed))
            print(json.dumps(dict(game=result['game'], method=result['method'], status=result['status'],
                                 steps=result.get('steps'), scores=result.get('scores')), ensure_ascii=False), flush=True)
    atomic_json(RESULTS / 'batch_completion.json', dict(runs=completed, archived_all=len(completed)==15 and all(r['status'] != 'worker_crash' for r in completed)))


if __name__ == '__main__': main()
