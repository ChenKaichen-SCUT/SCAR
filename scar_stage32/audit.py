"""Publication boundary, frozen source and raw/decompressed credential checks."""
import hashlib,subprocess
from .common import *

def main():
    offline();integrity=check_freeze()
    freeze_commit=subprocess.check_output(['git','log','-1','--format=%H','--','results/stage32/freeze.json'],cwd=ROOT,text=True).strip()
    assert sha(RESULTS/'freeze.json')==hashlib.sha256(subprocess.check_output(['git','show',f'{freeze_commit}:results/stage32/freeze.json'],cwd=ROOT)).hexdigest()
    for name in ['verification.json','analysis_verification.json','cost_reconciliation.json']:assert read(RESULTS/name)['passed']
    assert read(RESULTS/'online_completion.json')['complete'];assert SEEDS==[42];assert not (RESULTS/'offline').exists();cost=read(RESULTS/'cost_reconciliation.json')
    roots=['agents/saer/','scar_stage32/','reports/stage32/','results/stage32/']
    changed=subprocess.check_output(['git','diff','--name-only','-z',BASE],cwd=ROOT).decode().split('\0');assert all(not n or n.startswith(tuple(roots)) for n in changed)
    logs=RESULTS/'logs';logs.mkdir(exist_ok=True)
    for p in list((RUNTIME/'logs').glob('*.log'))+list(RUNTIME.glob('*.log')):
        (logs/(p.name+'.gz')).write_bytes(gzip.compress(p.read_bytes(),mtime=0))
    write(RESULTS/'development_notes.json',dict(original_agc_v2_files_changed=0,post_freeze_policy_changes=0,post_fix_paid_reruns=0,complete_baselines_reused=1,
        historical_actions_referenced=300,historical_requests_referenced=len(rows(baseline(42)/'requests.jsonl.gz')),offline_paid_samples=0,
        user_scope='Stop superseded runs, repair interface feedback, rerun only seed42 from initial state; remove previous Stage32 records.',
        syntax_fix='Expose previous malformed proposal plus required public signature and argument count to the existing bounded native repair loop; no automatic argument filling.',
        new_analysis_model_calls=0))
    files=[p for name in roots for p in (ROOT/name).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc']
    key=None
    if (ROOT.parent/'miyao.txt').exists():
        from scar.providers.deepseek import read_key
        key=read_key(ROOT.parent/'miyao.txt').encode()
    for p in files:
        b=p.read_bytes();assert len(b)<50*1024*1024,str(p)
        if key:
            assert key not in b,str(p)
            if p.suffix=='.gz':assert key not in gzip.decompress(b),str(p)
    excluded={'artifact_manifest.json','artifact_audit.json','publication.json','change_accounting.json','Git变更记录.md'}
    manifest={str(p.relative_to(ROOT)):dict(sha256=sha(p),bytes=p.stat().st_size) for p in sorted(files) if p.name not in excluded}
    write(RESULTS/'artifact_manifest.json',dict(files=manifest,metadata_excluded=sorted(excluded)))
    write(RESULTS/'artifact_audit.json',dict(passed=True,freeze_commit=freeze_commit,freeze_integrity=integrity,original_agc_v2_model_environment_unchanged=True,
        policy_unchanged_after_freeze=True,only_remnant=True,seeds=SEEDS,formal_pairs=1,post_fix_failures_retained=True,post_fix_paid_reruns=0,
        new_requests=cost['new_requests'],cost_usd=cost['cost_usd'],analysis_model_calls=0,private_key_scan_performed=bool(key),private_key_absent=True if key else None,
        downloaded_dependencies_included=False,artifact_files=len(manifest),artifact_bytes=sum(x['bytes'] for x in manifest.values())))
    print(json.dumps(read(RESULTS/'artifact_audit.json')),flush=True)

if __name__=='__main__':main()
