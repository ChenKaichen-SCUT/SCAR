"""Export a completed study's public evidence, never hidden-world snapshots.

The optional secret file is used only for a local scan, not copied or printed.
This post-study exporter does not affect frozen actor behavior.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import tarfile

from scar_public.provider import read_key


def export(root, destination, secret_file=None):
    assert (root/'analysis.json').exists(), 'Analyze every completed block first'
    files = {root/name for name in (
        'analysis.json', 'evaluation_plan.json', 'environment_receipt.json',
        'upstream_source_manifest.json', 'source_normalized_manifest.json',
        'cost_audit.json', 'mechanism_audit.json')
        if (root/name).exists()}
    frozen = root/'frozen'
    source_manifest = json.loads((frozen/'source_manifest.json').read_text())
    files.add(frozen/'source_manifest.json')
    for relative, expected in source_manifest.items():
        if relative == 'parent_revision': continue
        source = frozen/relative
        assert hashlib.sha256(source.read_bytes()).hexdigest() == expected
        files.add(source)
    for block in (root/'evaluation').iterdir():
        if not block.is_dir():
            continue
        assert (block/'result.json').exists()
        for name in ('manifest.json', 'initial_receipt.json', 'result.json',
                     'coupling.json', 'calls.jsonl', 'sentry_events.jsonl',
                     'environment_replay_audit.json'):
            path = block/name
            if path.exists():
                files.add(path)
        for arm in ('prompt', 'checked', 'sentry', 'v16'):
            files.add(block/arm/'current.json')
            files.update((block/arm/'trace').glob('*.json'))
            # Agent notebooks contain public memory, not engine world state.
            for name in ('agent.json', 'core_events.json'):
                files.update((block/arm/'checkpoints').glob('*/'+name))
        files.update((block/'api').glob('*.request.json.gz'))
        files.update((block/'api').glob('*.response.json'))
        files.update(p for p in (block/'api').glob('*.jsonl'))
    secret = read_key(secret_file).encode() if secret_file else None
    entries = []
    for path in sorted(files):
        relative = path.relative_to(root).as_posix()
        assert path.suffix != '.pkl' and 'initial_environment' not in path.parts
        data = path.read_bytes()
        if secret:
            content = gzip.decompress(data) if path.suffix == '.gz' else data
            assert secret not in content, 'Secret scan failed; export withheld'
        entries.append(dict(path=relative, bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))
    manifest = dict(files=entries, hidden_world_snapshots_included=False,
                    secret_scan_performed=bool(secret),
                    trace_files=sum('/trace/' in e['path'] for e in entries))
    index = root/'public_evidence_manifest.json'
    index.write_text(json.dumps(manifest, indent=2))
    with tarfile.open(destination, 'w:gz') as archive:
        archive.add(index, arcname='public_evidence_manifest.json')
        for path in sorted(files):
            archive.add(path, arcname=path.relative_to(root).as_posix())
    receipt = dict(archive_name=destination.name, bytes=destination.stat().st_size,
                   sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),
                   files=len(entries), trace_files=manifest['trace_files'],
                   hidden_world_snapshots_included=False, secret_scan_performed=bool(secret))
    (root/'public_evidence_receipt.json').write_text(json.dumps(receipt, indent=2))
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--destination', type=Path, required=True)
    p.add_argument('--secret-file', type=Path)
    args = p.parse_args()
    export(args.root, args.destination, args.secret_file)
