"""Verify trusted server artifacts and terminal checkpoints without model calls."""
import argparse
import hashlib
import json
import tarfile
from pathlib import Path

from .cli import ROOT, FROZEN, doctor, load, write


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class NoModel:
    def generate(self, *args, **kwargs):
        raise RuntimeError('Model calls forbidden during migration verification')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backup', type=Path, required=True)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    from scar_stage18.common import deny_network, read_gzip
    deny_network()
    environment = doctor()
    index = load(args.backup / 'backup-index.json')
    for name, record in index['files'].items():
        assert sha(args.backup / name) == record['sha256'], name
    project = load(args.backup / 'project-manifest.json')
    with tarfile.open(args.backup / 'project-supplement.tar.gz') as archive:
        extras = {m.name.removeprefix('project/'): hashlib.sha256(archive.extractfile(m).read()).hexdigest()
                  for m in archive.getmembers() if m.isfile()}
    canonical = supplement = 0
    for name, record in project.items():
        if name in extras:
            assert extras[name] == record['sha256'], name
            supplement += 1
        else:
            assert sha(ROOT / name) == record['sha256'], name
            canonical += 1
    runtime_manifest = load(args.backup / 'scar18-runtime-manifest.json')
    for name, record in runtime_manifest.items():
        assert sha(args.runtime / name) == record['sha256'], name
    from scar.environment import restore, state_digest
    from scar_stage18.agent import make_method
    histories = {r['task_id']: r['history'] for r in read_gzip(FROZEN / 'initial_public_histories.jsonl.gz')}
    restored = []
    for task in load(FROZEN / 'tasks.json'):
        folder = args.runtime / 'runs' / (task['task_id'] + '__SCAR18')
        cp = folder / load(folder / 'latest.json')['checkpoint']
        meta = load(cp / 'meta.json')
        agent = make_method('SCAR18', task['game_name'], NoModel(), task['objective_text'],
                            task['target_item'], histories[task['task_id']], folder / 'unused-memory')
        agent.load_memory(str(cp))
        saved_agent = load(cp / 'stage18.json')
        assert agent.controller.to_dict() == saved_agent['controller']
        assert agent.facts.to_dict() == saved_agent['facts']
        env = restore(cp / 'physical.pkl', agent=agent)
        assert state_digest(env) == meta['state_hash'], task['task_id']
        summary = load(FROZEN / 'runs' / folder.name / 'summary.json')
        assert meta['step'] == summary['steps']
        assert state_digest(env) == summary['final_state_hash']
        restored.append(dict(task=task['task_id'], step=meta['step'],
                             physical_hash_equal=True, controller_and_facts_equal=True))
    receipt = dict(passed=True, environment=environment, canonical_server_files_verified=canonical,
                   supplemental_server_files_verified=supplement,
                   local_runtime_files_verified=len(runtime_manifest),
                   terminal_checkpoints=restored, api_calls=0, network_disabled=True)
    write(args.output, receipt)
    print(json.dumps({k: v for k, v in receipt.items() if k not in ('environment', 'terminal_checkpoints')}))


if __name__ == '__main__':
    main()
