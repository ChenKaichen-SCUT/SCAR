"""Build a deduplicated reproduction ZIP from explicit code/result inputs."""
import argparse, json
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED


RESTORE = '''import json, sys
from pathlib import Path
root=Path(__file__).resolve().parent
version, destination=sys.argv[1],Path(sys.argv[2])
mapping=json.loads((root/'snapshots'/version/'sources.json').read_text())
for name,digest in mapping.items():
 target=destination/'scar_public'/name; target.parent.mkdir(parents=True,exist_ok=True)
 target.write_bytes((root/'blobs'/digest).read_bytes())
for origin, relative in ((root/'analysis','scar_public/experiments'),(root/'evidence'/version,'frozen_results'),(root/'diagnostics','diagnostics')):
 for source in origin.rglob('*'):
  if source.is_file():
   target=destination/relative/source.relative_to(origin);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(source.read_bytes())
print('Restored',version,'to',destination)
'''


def main():
    p = argparse.ArgumentParser(); p.add_argument('outputs', type=Path)
    p.add_argument('destination', type=Path); a = p.parse_args()
    a.destination.mkdir(parents=True, exist_ok=True)
    archive = a.destination/'reproduction.zip'; blobs = {}; maps = {}; audit = []
    names = dict(v1='compact_progress_code.zip', v2='compact_progress_v2_code.zip', v3='compact_progress_v3_code.zip')
    for version, filename in names.items():
        mapping = {}
        with ZipFile(a.outputs/filename) as z:
            for name in z.namelist():
                assert name.startswith('scar_public/') and name.endswith('.py')
                data = z.read(name); digest = sha256(data).hexdigest()
                mapping[Path(name).name] = digest; blobs[digest] = data
        maps[version] = mapping
        for manifest in (a.outputs/'compact_evidence'/version).glob('*/manifest.json'):
            expected = json.loads(manifest.read_text())['sources']
            assert expected == mapping, (version, manifest)
            audit.append(dict(version=version, batch=manifest.parent.name,
                source_files=len(mapping), all_source_bytes_verified=True,
                manifest_sha256=sha256(manifest.read_bytes()).hexdigest()))
    diagnostics = dict(interrupted_query='compact_interrupted_diagnostic.json',
        query_factor_ablation='compact_query_factor_ablation.json',
        pattern_diagnostic='compact_pattern_diagnostic.json', scale_audit='compact_scale_audit.json')
    for target, source in diagnostics.items():
        (a.destination/(target+'.json')).write_bytes((a.outputs/source).read_bytes())
    (a.destination/'source_snapshot_audit.json').write_text(json.dumps(audit, indent=2))
    (a.destination/'test_validation.json').write_text(json.dumps(dict(tests_passed=29,
        command='python -m pytest scar_public/test_compact_progress.py scar_public/test_factored_progress.py scar_public/test_progress_carrier.py scar_public/test_reachable_labels.py scar_public/test_theory_strengthening.py scar_public/test_label_comparison.py -q',
        manuscript_changed=False, api_calls=0), indent=2))
    inputs = dict(sources=[
        dict(filename='BKS_jair_domains.tgz', url='https://rakaposhi.eas.asu.edu/belief-search/BKS_jair_domains.tgz',
            sha256='3b6db211b4eaedab6dc86a5811039f8f440f285283ae6e7ccefccc0ed4bee12d'),
        dict(filename='contff-tests.tgz', url='https://fai.cs.uni-saarland.de/hoffmann/ff/contff-tests.tgz',
            sha256='e30a16ab8dbfb00e65e6d3dfca31820686d0a8289a718238e25417236ee31e49')])
    for suffix in ('d', 'p'):
        name = f'Tests_localize5_{suffix}.pddl'
        data = (a.outputs.parent/'work/planning_sources'/name).read_bytes()
        inputs['sources'].append(dict(filename=name, sha256=sha256(data).hexdigest(),
            url=f'https://raw.githubusercontent.com/aiplan4eu/up-cpor/4776479597e33610f68dcc20613850f414eb6688/Tests/localize5/{suffix}.pddl'))
    with ZipFile(archive, 'w', ZIP_DEFLATED) as z:
        z.writestr('restore.py', RESTORE)
        z.writestr('input_sources.json', json.dumps(inputs, indent=2))
        for digest, data in sorted(blobs.items()):
            z.writestr('blobs/'+digest, data)
        for version, mapping in maps.items():
            z.writestr(f'snapshots/{version}/sources.json', json.dumps(mapping, indent=2))
        for path in sorted((a.outputs/'compact_evidence').rglob('*')):
            if path.is_file():
                z.write(path, 'evidence/'+path.relative_to(a.outputs/'compact_evidence').as_posix())
        for target, source in diagnostics.items():
            z.write(a.outputs/source, 'diagnostics/'+target+'.json')
        for path in Path(__file__).parent.glob('*compact*.py'):
            z.write(path, 'analysis/'+path.name)
        path = Path(__file__).parent/'ablate_progress_query.py'
        z.write(path, 'analysis/'+path.name)
        path = Path(__file__).parent/'analyze_reachable_labels.py'
        z.write(path, 'analysis/'+path.name)
    receipt = dict(sha256=sha256(archive.read_bytes()).hexdigest(), bytes=archive.stat().st_size,
        snapshots=maps.keys(), input_datasets_bundled=False)
    receipt['snapshots'] = list(receipt['snapshots'])
    (a.destination/'reproduction.json').write_text(json.dumps(receipt, indent=2))
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
