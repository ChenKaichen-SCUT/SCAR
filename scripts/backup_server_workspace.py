"""Archive unpublished project artifacts and SCAR18 terminal memory, offline.

Run on the source server with a manifest of files already published in Git.
Downloaded engines, environments, credentials and regenerable world copies are
not publication artifacts. Server files are only read, never removed.
"""
import argparse
import gzip
import hashlib
import io
import json
import sqlite3
import tarfile
from pathlib import Path


def dump(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def allowed(path):
    return not (set(path.parts) & {'.git', '__pycache__', '.pytest_cache', '.venv', 'dependencies'}
                or path.suffix in {'.pyc', '.key'} or path.name == 'miyao.txt'
                or path.name.startswith('.env'))


def archive(path, entries):
    with tarfile.open(path, 'w:gz') as out:
        for name, data in sorted(entries.items()):
            item = tarfile.TarInfo(name)
            item.size, item.mode = len(data), 0o600
            out.addfile(item, io.BytesIO(data))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--published-manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    published = json.loads(args.published_manifest.read_text())
    project = args.workspace / 'project'
    manifest, supplemental = {}, {}
    # Read known secrets only to reject accidental publication. Never log them.
    secrets = [p.read_bytes().strip() for p in (Path('/root/.scar-deepseek-key'),)
               if p.is_file() and p.stat().st_size]

    def safe(data, name):
        for secret in secrets:
            if secret in data:
                raise ValueError('Secret detected; publication stopped: ' + name)
        return data

    for path in sorted(project.rglob('*')):
        name = path.relative_to(project)
        if not path.is_file() or path.is_symlink() or not allowed(name):
            continue
        data = safe(path.read_bytes(), str(name))
        record = {'sha256': sha(data), 'bytes': len(data)}
        manifest[str(name)] = record
        if published.get(str(name), {}).get('sha256') != record['sha256']:
            supplemental['project/' + str(name)] = data
    archive(args.output / 'project-supplement.tar.gz', supplemental)
    (args.output / 'project-manifest.json').write_bytes(dump(manifest))

    runtime = args.workspace / 'runtime_stage18'
    runtime_manifest, terminal, duplicate_evidence = {}, {}, []
    for path in sorted(runtime.rglob('*')):
        if not path.is_file() or path.is_symlink():
            continue
        name = str(path.relative_to(runtime))
        data = path.read_bytes()
        runtime_manifest[name] = {'sha256': sha(data), 'bytes': len(data)}
        # Requests and per-step records already exist in canonical published runs.
        if path.suffix == '.log' or path.name in {'latest.json', 'progress.json'} or (
                path.parent.name.startswith('checkpoint-') and path.suffix == '.json'):
            terminal['runtime_stage18/' + name] = safe(data, name)
        if path.suffix == '.sqlite':
            with sqlite3.connect(f'file:{path}?mode=ro', uri=True) as db:
                export = '\n'.join(db.iterdump()).encode()
            terminal['runtime_stage18/' + name + '.sql'] = safe(export, name)
    for folder in sorted((runtime / 'runs').iterdir()):
        if not folder.is_dir():
            continue
        canonical = project / 'results/stage18/runs' / folder.name
        steps = [json.loads(gzip.decompress(p.read_bytes()))
                 for p in sorted((folder / 'steps').glob('*.jsonl.gz'))]
        published_steps = [json.loads(line) for line in
                           gzip.decompress((canonical / 'trajectory.jsonl.gz').read_bytes()).splitlines()]
        requests = [json.loads(s) for s in (folder / 'requests.jsonl').read_text().splitlines()]
        published_requests = [json.loads(s) for s in
                              gzip.decompress((canonical / 'requests.jsonl.gz').read_bytes()).splitlines()]
        if steps != published_steps or requests != published_requests:
            raise ValueError('Canonical evidence differs from runtime: ' + folder.name)
        duplicate_evidence.append({'run': folder.name, 'steps': len(steps),
                                   'requests': len(requests), 'canonical_equal': True})
    archive(args.output / 'scar18-terminal-memory.tar.gz', terminal)
    (args.output / 'scar18-runtime-manifest.json').write_bytes(dump(runtime_manifest))
    inventory = {'project_files': len(manifest), 'already_published': len(manifest) - len(supplemental),
                 'supplemental_files': len(supplemental), 'terminal_files': len(terminal),
                 'duplicate_evidence': duplicate_evidence,
                 'exclusions': ['credentials', 'downloaded dependencies / virtualenv',
                                'regenerable world copies', 'physical pickle snapshots (server and local private copy)',
                                'old runtime caches (server retained; published results unchanged)'],
                 'files': {p.name: {'sha256': sha(p.read_bytes()), 'bytes': p.stat().st_size}
                           for p in sorted(args.output.iterdir())}}
    (args.output / 'backup-index.json').write_bytes(dump(inventory))
    print(json.dumps({k: inventory[k] for k in
                      ('project_files', 'already_published', 'supplemental_files', 'terminal_files')}))


if __name__ == '__main__':
    main()
