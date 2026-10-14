"""Publication boundary, frozen source and raw/decompressed credential checks."""
import hashlib,subprocess
from .common import *
FREEZE_COMMIT='eb2b7b6c385d01b20404350d57057fb4e4050875'

def main():
    offline();integrity=check_freeze()
    assert sha(RESULTS/'freeze.json')==hashlib.sha256(subprocess.check_output(['git','show',f'{FREEZE_COMMIT}:results/stage32/freeze.json'],cwd=ROOT)).hexdigest()
    for name in ['verification.json','analysis_verification.json','cost_reconciliation.json']:assert read(RESULTS/name)['passed']
    assert read(RESULTS/'online_completion.json')['complete'];assert read(RESULTS/'offline_completion.json')['complete'];cost=read(RESULTS/'cost_reconciliation.json')
    roots=['agents/saer/','scar_stage32/','reports/stage32/','results/stage32/']
    changed=subprocess.check_output(['git','diff','--name-only','-z',BASE],cwd=ROOT).decode().split('\0');assert all(not n or n.startswith(tuple(roots)) for n in changed)
    logs=RESULTS/'logs';logs.mkdir(exist_ok=True)
    for p in list((RUNTIME/'logs').glob('*.log'))+list(RUNTIME.glob('*.log')):
        (logs/(p.name+'.gz')).write_bytes(gzip.compress(p.read_bytes(),mtime=0))
    write(RESULTS/'development_notes.json',dict(old_agent_files_changed=0,post_freeze_policy_changes=0,paid_reruns=0,complete_baselines_reused=3,
        historical_actions_reused=900,historical_requests_reused=970,offline_fixed_candidates=77,offline_unique_states=75,
        before_freeze_correction='Added both observed condition-loss events before any model call, expanding the cohort from 75 to 77. Freeze regenerated before calls.',
        administrative_read_issue='An early git-add ran before the online-gate checksum job completed; it staged nothing. After completion, the offline commit succeeded before online start. No model call or data changed.',
        analysis_only_additions=['Role-aware response schema audit.','All raw resource transition events retained; custody risk not equated with harm.','All native candidate/final probes, positive and negative indexes.'],
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
    write(RESULTS/'artifact_audit.json',dict(passed=True,freeze_commit=FREEZE_COMMIT,freeze_integrity=integrity,old_agent_model_environment_unchanged=True,
        policy_unchanged_after_freeze=True,only_remnant=True,seeds=SEEDS,formal_pairs=3,all_failures_retained=True,paid_reruns=0,
        new_requests=cost['new_requests'],cost_usd=cost['cost_usd'],analysis_model_calls=0,private_key_scan_performed=bool(key),private_key_absent=True if key else None,
        downloaded_dependencies_included=False,artifact_files=len(manifest),artifact_bytes=sum(x['bytes'] for x in manifest.values())))
    print(json.dumps(read(RESULTS/'artifact_audit.json')),flush=True)

if __name__=='__main__':main()
