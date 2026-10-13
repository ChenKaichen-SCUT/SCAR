"""Archive named old local checks and organize guides without deleting evidence."""
import argparse
import hashlib
import json
import shutil
import tarfile
from pathlib import Path

CHECKS = ('stage15_formal_replay_local', 'stage15_preflight_local',
          'stage15_preflight_local_v1', 'stage15_preflight_local_v2',
          'unknown17_portable_check')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--archive-name', default='2026-10-13')
    args = parser.parse_args()
    root = args.workspace.resolve()
    dest = root / 'archive' / args.archive_name
    if dest.exists():
        raise FileExistsError('Archive already exists; refusing to overwrite')
    dest.mkdir(parents=True)
    files = {str(p.relative_to(root)): {'sha256': sha(p.read_bytes()), 'bytes': p.stat().st_size}
             for name in CHECKS for p in (root / name).rglob('*') if p.is_file()}
    archive = dest / 'old-local-checks.tar.gz'
    with tarfile.open(archive, 'w:gz') as out:
        for name in CHECKS:
            if (root / name).is_dir():
                out.add(root / name, arcname=name)
    # Verify every byte in the compressed archive before removing source dirs.
    with tarfile.open(archive) as saved:
        for name, record in files.items():
            assert sha(saved.extractfile(name).read()) == record['sha256'], name
    (dest / 'checks-manifest.json').write_text(json.dumps(files, ensure_ascii=False, indent=2))
    for name in CHECKS:
        if (root / name).is_dir():
            shutil.rmtree(root / name)
    guides = root / ('指引文件' if (root / '指引文件').is_dir() else '指引')
    moved = []
    for p in sorted(root.glob('指引*')):
        if p.is_file() and p.suffix in {'.md', '.txt'}:
            guides.mkdir(exist_ok=True)
            target = guides / p.name
            if target.exists():
                raise FileExistsError(target)
            digest = sha(p.read_bytes())
            p.rename(target)
            assert sha(target.read_bytes()) == digest
            moved.append({'from': p.name, 'to': str(target.relative_to(root)), 'sha256': digest})
    progress = root / 'research-progress.json'
    if progress.is_file():
        shutil.copy2(progress, dest / progress.name)
    cache_dirs = [p for p in (root / 'scar_agentodyssey').rglob('__pycache__')
                  if '.git' not in p.parts and 'runtime' not in p.parts]
    cache_dirs += [root / 'scar_agentodyssey/.pytest_cache']
    cache_bytes = 0
    removed_caches = []
    for path in cache_dirs:
        if path.is_dir() and not path.is_symlink():
            cache_bytes += sum(p.stat().st_size for p in path.rglob('*') if p.is_file())
            removed_caches.append(str(path.relative_to(root)))
            shutil.rmtree(path)
    report = dict(archive=str(archive), original_check_bytes=sum(r['bytes'] for r in files.values()),
                  archive_bytes=archive.stat().st_size, verified_check_files=len(files),
                  moved_guides=moved, removed_cache_dirs=removed_caches, removed_cache_bytes=cache_bytes,
                  preserved=['all historical source and result files', 'baseline code and runtimes',
                             'downloaded dependencies and Python environment', 'private API key'])
    (dest / 'cleanup.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k not in ('moved_guides', 'removed_cache_dirs')}))


if __name__ == '__main__':
    main()
