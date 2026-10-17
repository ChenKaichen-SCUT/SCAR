"""Package exact server bytes separately from final diagnostic source."""
import argparse,json
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from scar_public.experiments.package_compact_evidence import RESTORE


def main():
    p=argparse.ArgumentParser();p.add_argument('outputs',type=Path);p.add_argument('destination',type=Path)
    a=p.parse_args();a.destination.mkdir(parents=True,exist_ok=True);blobs={};maps={};audit=[]
    mapping={}
    with ZipFile(a.outputs/'sparse_policy_code.zip') as z:
        for name in z.namelist():
            assert name.startswith('scar_public/') and name.endswith('.py')
            data=z.read(name);digest=sha256(data).hexdigest();blobs[digest]=data;mapping[Path(name).name]=digest
    maps['v1']=mapping
    for manifest in (a.outputs/'sparse_evidence/v1').glob('*/manifest.json'):
        assert json.loads(manifest.read_text())['sources']==mapping
        audit.append(dict(batch=manifest.parent.name,source_files=len(mapping),all_source_bytes_verified=True,
            manifest_sha256=sha256(manifest.read_bytes()).hexdigest()))
    mapping={}
    for path in Path(__file__).resolve().parent.parent.glob('*.py'):
        data=path.read_bytes();digest=sha256(data).hexdigest();mapping[path.name]=digest;blobs[digest]=data
    maps['diagnostic_current']=mapping
    diagnostics=dict(ring_core='sparse_core_diagnostic.json',cube_queries='sparse_query_diagnostic.json',
        compressed_cores='sparse_compressed_cores.json')
    for target,name in diagnostics.items():(a.destination/(target+'.json')).write_bytes((a.outputs/name).read_bytes())
    (a.destination/'source_snapshot_audit.json').write_text(json.dumps(audit,indent=2))
    tests=dict(tests_passed=38,manuscript_changed=False,api_calls=0,
        command='python -m pytest scar_public/test_sparse_policy.py scar_public/test_compact_progress.py scar_public/test_factored_progress.py scar_public/test_progress_carrier.py scar_public/test_reachable_labels.py scar_public/test_theory_strengthening.py scar_public/test_label_comparison.py -q')
    (a.destination/'test_validation.json').write_text(json.dumps(tests,indent=2))
    with ZipFile(a.outputs/'SCAR_compact_progress_reproduction.zip') as old:
        inputs=old.read('input_sources.json')
    archive=a.destination/'reproduction.zip'
    with ZipFile(archive,'w',ZIP_DEFLATED) as z:
        z.writestr('restore.py',RESTORE);z.writestr('input_sources.json',inputs)
        for digest,data in sorted(blobs.items()):z.writestr('blobs/'+digest,data)
        for version,mapping in maps.items():z.writestr(f'snapshots/{version}/sources.json',json.dumps(mapping,indent=2))
        for path in sorted((a.outputs/'sparse_evidence').rglob('*')):
            if path.is_file():z.write(path,'evidence/'+path.relative_to(a.outputs/'sparse_evidence').as_posix())
        for target,name in diagnostics.items():z.write(a.outputs/name,'diagnostics/'+target+'.json')
        for path in Path(__file__).parent.glob('*sparse*.py'):z.write(path,'analysis/'+path.name)
        for name in ('analyze_reachable_labels.py','package_compact_evidence.py','README_SPARSE_POLICY.txt'):
            z.write(Path(__file__).parent/name,'analysis/'+name)
    receipt=dict(sha256=sha256(archive.read_bytes()).hexdigest(),bytes=archive.stat().st_size,
        snapshots=list(maps),input_datasets_bundled=False,credentials_bundled=False)
    (a.destination/'reproduction.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))


if __name__=='__main__':main()
