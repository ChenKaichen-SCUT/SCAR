"""Launch frozen SCAR18 into separate local outputs, with zero-API acceptance."""
import argparse
import contextlib
import copy
import datetime
import fcntl
import importlib.metadata
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / 'results/stage18'
LOCAL = ROOT / 'runtime/local'


def load(path):
    return json.loads(path.read_text())


def write(path, value):
    from scar.io import atomic_json
    atomic_json(path, value)


def stamp():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')


def doctor():
    from scar_stage17.common import ENGINE_COMMIT
    from scar_stage18.run import check_freeze
    engine = Path(os.environ['AGENTODYSSEY_ROOT']).resolve()
    actual = subprocess.check_output(['git', '-C', str(engine), 'rev-parse', 'HEAD'], text=True).strip()
    dirty = subprocess.check_output(['git', '-C', str(engine), 'status', '--porcelain'], text=True).strip()
    mismatches = []
    for line in (ROOT / 'requirements-cpu.lock').read_text().splitlines():
        name, expected = line.split('==')
        try:
            installed = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            installed = None
        if installed != expected:
            mismatches.append({'package': name, 'expected': expected, 'installed': installed})
    freeze = check_freeze()
    result = dict(passed=sys.version_info[:2] == (3, 12) and actual == ENGINE_COMMIT
                  and not dirty and not mismatches, python=sys.version.split()[0],
                  executable=sys.executable, engine=str(engine), engine_commit=actual,
                  engine_clean=not dirty, dependency_mismatches=mismatches,
                  frozen_files_verified=len(freeze['files']), method='SCAR18',
                  max_actions=100, api_calls=0)
    if not result['passed']:
        raise RuntimeError(json.dumps(result, ensure_ascii=False))
    return result


def output_path(path):
    path = path.resolve()
    # Neither local runs nor imported terminal state may write historical artifacts.
    for forbidden in (ROOT / 'results', ROOT / 'reports', ROOT / 'backups',
                      ROOT / 'runtime/server_stage18'):
        if path == forbidden or forbidden in path.parents:
            raise ValueError('Output overlaps preserved artifacts: ' + str(path))
    return path


def prepare(directory, task):
    directory = output_path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    output = directory / 'results'
    output.mkdir()
    shutil.copyfile(FROZEN / 'initial_public_histories.jsonl.gz', output / 'initial_public_histories.jsonl.gz')
    from scar_stage18.config import PROVIDER
    write(directory / 'run_config.json', dict(method='SCAR18', task=task,
          provider=PROVIDER, max_actions=100, freeze=load(FROZEN / 'freeze.json'),
          scope='new local run; separate from published formal results'))
    write(output / 'tasks.json', [task])
    return directory


class RecordedProvider:
    """Replay saved successful responses, checking every complete prompt signature."""
    source = None
    calls = 0

    def __init__(self, folder, ledger, key_path, config=None):
        from scar_stage18.common import read_gzip
        self.config = config
        self.cache = {r['logical_id']: r for r in read_gzip(self.source) if r['status'] == 'ok'}
        self.step = self.ordinal = 0

    def begin_step(self, step):
        self.step, self.ordinal = step, 0

    def generate(self, user_prompt, system_prompt=None, required=('action', 'reasoning'),
                 phase='action', max_tokens=None, validator=None):
        from scar.io import digest
        from scar_stage17.provider import SharedDeepSeekProvider
        self.ordinal += 1
        row = self.cache[f'{self.step:03d}:{self.ordinal:03d}']
        messages = ([dict(role='system', content=system_prompt)] if system_prompt else [])
        messages += [dict(role='user', content=user_prompt)]
        signature = digest(dict(messages=messages, phase=phase,
                                max_tokens=max_tokens or self.config['max_tokens'], required=required))
        if row['signature'] != signature:
            raise ValueError('Local request differs from the recorded server prompt')
        if validator:
            validator(row['parsed'])
        type(self).calls += 1
        return copy.deepcopy(SharedDeepSeekProvider.result(row))


def smoke():
    from scar_stage18.common import deny_network, read_gzip
    # Block network before environment and agent construction; no key is read.
    deny_network()
    receipt = doctor()
    import scar_stage18.run as runner
    original_results, original_provider = runner.RESULTS, runner.SharedDeepSeekProvider
    tasks = load(FROZEN / 'tasks.json')
    checks = []
    RecordedProvider.calls = 0
    LOCAL.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix='smoke-', dir=LOCAL) as temp:
            for game in ('robot_kingdom', 'quarantine'):
                # Shortest successful historical run per game keeps acceptance cheap.
                candidates = [(t, load(FROZEN / 'runs' / (t['task_id'] + '__SCAR18') / 'summary.json'))
                              for t in tasks if t['game_name'] == game]
                task, old = min((pair for pair in candidates if pair[1]['success']),
                                key=lambda pair: pair[1]['steps'])
                path = prepare(Path(temp) / game, task)
                historical = FROZEN / 'runs' / (task['task_id'] + '__SCAR18')
                RecordedProvider.source = historical / 'requests.jsonl.gz'
                runner.RESULTS, runner.SharedDeepSeekProvider = path / 'results', RecordedProvider
                with contextlib.redirect_stdout(io.StringIO()):
                    result = runner.execute(task, 'SCAR18', path / 'runtime', None)
                    # Completed output is idempotent: no resampling on repeated launch.
                    calls = RecordedProvider.calls
                    assert runner.execute(task, 'SCAR18', path / 'runtime', None) == result
                    assert calls == RecordedProvider.calls
                current = read_gzip(path / 'results/runs' / (task['task_id'] + '__SCAR18') / 'trajectory.jsonl.gz')
                prior = read_gzip(historical / 'trajectory.jsonl.gz')
                assert result['success'] and result['steps'] == old['steps'], result
                assert len(current) == len(prior)
                for new, old_row in zip(current, prior):
                    for field in ('action', 'feedback', 'state_hash', 'decision', 'success'):
                        assert new[field] == old_row[field], (game, new['step'], field)
                checks.append(dict(game=game, task=task['task_id'], steps=len(current),
                                   all_prompt_signatures_equal=True, native_states_equal=True,
                                   actions_decisions_feedback_equal=True, completed_resume_idempotent=True))
    finally:
        runner.RESULTS, runner.SharedDeepSeekProvider = original_results, original_provider
    receipt.update(checks=checks, replayed_model_responses=RecordedProvider.calls,
                   network_disabled=True, api_calls=0, new_experiments=0)
    write(LOCAL / 'smoke.json', receipt)
    return receipt


def run(args):
    doctor()
    from scar.providers.deepseek import read_key
    # Validate credentials before creating output. Never print or persist the key.
    read_key(args.key_path)
    task = next(t for t in load(FROZEN / 'tasks.json') if t['task_id'] == args.task)
    path = output_path(args.run_dir or LOCAL / (stamp() + '-' + args.task))
    if args.resume:
        from scar_stage18.config import PROVIDER
        cfg = load(path / 'run_config.json')
        if (cfg['task'] != task or cfg['freeze'] != load(FROZEN / 'freeze.json')
                or cfg['provider'] != PROVIDER or cfg['method'] != 'SCAR18'):
            raise ValueError('Resume configuration differs; preserve the existing run')
    else:
        prepare(path, task)
    # One writer per run, including across CLI processes.
    with (path / '.run.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        import scar_stage18.run as runner
        original = runner.RESULTS
        try:
            runner.RESULTS = path / 'results'
            result = runner.execute(task, 'SCAR18', path / 'runtime', args.key_path)
        finally:
            runner.RESULTS = original
    return dict(directory=str(path), summary=result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('doctor', 'list-tasks', 'smoke'):
        sub.add_parser(name)
    live = sub.add_parser('run', help='New local SCAR18 task using the model API')
    live.add_argument('--task', required=True, choices=[t['task_id'] for t in load(FROZEN / 'tasks.json')])
    live.add_argument('--run-dir', type=Path)
    live.add_argument('--resume', action='store_true')
    live.add_argument('--key-path', default=str(ROOT.parent / 'miyao.txt'))
    args = parser.parse_args()
    if args.command == 'run' and args.resume and not args.run_dir:
        parser.error('--resume requires --run-dir')
    if args.command == 'list-tasks':
        result = [dict(task=t['task_id'], game=t['game_name'], goal=t['target_item'], seed=t['initial_seed'])
                  for t in load(FROZEN / 'tasks.json')]
    else:
        result = {'doctor': doctor, 'smoke': smoke, 'run': lambda: run(args)}[args.command]()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
