"""Verify the frozen source/artifact bundle and unchanged historical files."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    manifest = json.loads((ROOT/'results/stage16/historical_manifest.json').read_text())
    for name, expected in manifest['files'].items():
        assert sha(ROOT/name) == expected, 'Historical file changed: '+name
    freeze = json.loads((ROOT/'results/stage16/freeze.json').read_text())
    for name, expected in freeze['files'].items():
        assert sha(ROOT/name) == expected, 'Frozen baseline changed: '+name
    publication = json.loads((ROOT/'results/stage16/publication_manifest.json').read_text())
    for name, expected in publication['files'].items():
        assert sha(ROOT/name) == expected, 'Published artifact changed: '+name
    local = json.loads((ROOT/'results/stage16/replay_local.json').read_text())
    server = json.loads((ROOT/'results/stage16/replay_server.json').read_text())
    assert local == server and local['passed']
    assert local['p3_checkpoints'] == 39 and local['ablation_checkpoints'] == 8
    assert local['new_api_calls'] == local['new_native_actions'] == local['full_episode_replays'] == 0
    assert len(local['archived_chain_net_branch']) == 3
    receipt = json.loads((ROOT/'results/stage16/server_integrity.json').read_text())
    assert not receipt['historical_changed'] and not receipt['historical_missing']
    assert receipt['runtime_before'] == receipt['runtime_after']
    for name, expected in receipt['source_sha256'].items():
        assert sha(ROOT/name) == expected, 'Source differs from server-tested version: '+name
    for site in ('local', 'server'):
        assert '279 passed' in (ROOT/f'results/stage16/unit_tests_{site}.txt').read_text()
    return {'passed': True, 'historical_files_unchanged': len(manifest['files']),
            'frozen_files': len(freeze['files']), 'published_files': len(publication['files']),
            'local_server_replay_identical': True, 'tests_each_site': 279,
            'new_api_calls': 0, 'new_native_actions': 0, 'new_performance_scores': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/scar_stage16_verification.json'))
    args = parser.parse_args()
    result = verify()
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
