"""Frozen-source, publication scope, complete artifacts and credential audit."""
import hashlib
import subprocess
from .common import *

FREEZE_COMMIT='aa364b89352040b59fe0193be9324e63d41cb640'

def main():
    offline();integrity=check_freeze()
    assert sha(RESULTS/'freeze.json')==hashlib.sha256(subprocess.check_output(['git','show',f'{FREEZE_COMMIT}:results/stage31/freeze.json'],cwd=ROOT)).hexdigest()
    for n in ['verification.json','analysis_verification.json','cost_reconciliation.json','terminal_review.json']:assert read(RESULTS/n)['passed']
    assert read(RESULTS/'completion.json')['complete'];cost=read(RESULTS/'cost_reconciliation.json')
    roots=['agents/rec_v1/','scar_stage31/','reports/stage31/','results/stage31/']
    changed=subprocess.check_output(['git','diff','--name-only',BASE],cwd=ROOT,text=True).splitlines()
    # core.quotepath may quote Chinese paths; use NUL-delimited raw filenames.
    changed=subprocess.check_output(['git','diff','--name-only','-z',BASE],cwd=ROOT).decode().split('\0')
    assert all(not n or n.startswith(tuple(roots)) for n in changed)
    logs=RESULTS/'logs';logs.mkdir(exist_ok=True)
    for p in list((RUNTIME/'logs').glob('*.log'))+[RUNTIME/n for n in ['batch.log','verify.log','terminal_review.log','offline_native.log']]:
        if p.exists():(logs/(p.name+'.gz')).write_bytes(gzip.compress(p.read_bytes(),mtime=0))
    write(RESULTS/'development_notes.json',dict(new_controller=True,old_agent_files_changed=0,post_freeze_policy_changes=0,paid_reruns=0,
        historical_actions_reused=394,historical_requests_reused=423,partial_baselines_resumed=2,complete_baseline_reused=1,
        pre_freeze_corrections=['Unknown/obscured public state is not treated as unchanged state.',
            'Unobserved unavailable storage destinations do not imply predicted visibility loss. Initial review artifacts retained.'],
        analysis_only_refinements=['Terminal AGC retry counters reconstructed after REC exception interrupted native decision finalization; raw requests unchanged.',
            'Repeated missing-precondition metric excludes unknown/format-only rejection categories.',
            'Extra zero-API terminal alternatives test the passed-to-AGC proposal and two-step local recovery.'],
        prelaunch_read_issue='A checksum scan attempted to read freeze.json while freeze hashing was still running; repeated after freeze completed. Zero API calls affected.',
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
    exclude={'artifact_manifest.json','artifact_audit.json','publication.json','change_accounting.json','Git变更记录.md'}
    manifest={str(p.relative_to(ROOT)):dict(sha256=sha(p),bytes=p.stat().st_size) for p in sorted(files) if p.name not in exclude}
    write(RESULTS/'artifact_manifest.json',dict(files=manifest,metadata_excluded=sorted(exclude)))
    write(RESULTS/'artifact_audit.json',dict(passed=True,freeze_commit=FREEZE_COMMIT,freeze_integrity=integrity,old_agent_model_environment_unchanged=True,
        policy_unchanged_after_freeze=True,only_remnant=True,seeds=SEEDS,formal_pairs=3,failed_runs_retained=True,paid_reruns=0,
        new_requests=cost['new_requests'],cost_usd=cost['cost_usd'],analysis_model_calls=0,private_key_scan_performed=bool(key),
        private_key_absent=True if key else None,downloaded_dependencies_included=False,artifact_files=len(manifest),artifact_bytes=sum(x['bytes'] for x in manifest.values())))
    print(json.dumps(read(RESULTS/'artifact_audit.json')),flush=True)

if __name__=='__main__':main()
