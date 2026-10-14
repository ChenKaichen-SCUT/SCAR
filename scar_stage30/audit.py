"""Source integrity, accounting, provenance and credential exclusion."""
import hashlib
import subprocess
from .common import *

FREEZE_COMMIT='72ed428'

def main():
    offline();integrity=check_freeze()
    assert sha(RESULTS/'freeze.json')==hashlib.sha256(subprocess.check_output(['git','show',f'{FREEZE_COMMIT}:results/stage30/freeze.json'],cwd=ROOT)).hexdigest()
    assert read(RESULTS/'completion.json')['complete'] and read(RESULTS/'verification.json')['passed']
    assert read(RESULTS/'analysis_verification.json')['passed']
    s=read(RESULTS/'summary.json');cost=read(RESULTS/'cost_reconciliation.json')
    assert s['variants']['OracleGoalStack']['requests']==cost['new_requests']
    assert abs(s['variants']['OracleGoalStack']['cost_usd']-cost['cost_usd'])<1e-10
    assert len(list((REPORTS/'timelines').glob('*.md')))==20
    for ident in CASES:
        meta=read(RESULTS/'checkpoints'/ident/'meta.json')
        saved=read(CHECKPOINTS/ident/'meta.json')
        assert meta['goal_stack']['goal_stack'][0]['goal']==saved['original_goal']
        assert meta['goal_stack']['goal_stack'][1]['goal']==CASES[ident]
        assert meta['original_first_messages']==saved['original_first_messages']
        assert meta['knowledge_source']['step']==meta['failure_step']
    logs=RESULTS/'logs';logs.mkdir(exist_ok=True)
    for p in list((RUNTIME/'logs').glob('*.log'))+[RUNTIME/'batch.log',RUNTIME/'verify.log']:
        if p.exists():(logs/(p.name+'.gz')).write_bytes(gzip.compress(p.read_bytes(),mtime=0))
    write(RESULTS/'development_notes.json',dict(production_changes=0,paid_reruns=0,unknown_billing=0,
        prelaunch_issues=['System python command absent; switched to the existing virtualenv interpreter.',
            'First shell redirection failed before launch because runtime directory was absent; created directory and launched once.'],
        prepublication_formatting_fix='Stripped source-feedback trailing spaces in rendered Markdown timelines after git diff --check rejected them; original JSON evidence and experiment data unchanged.',
        affected_model_calls=0))
    files=[p for folder in [ROOT/'scar_stage30',RESULTS,REPORTS] for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc']
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
    write(RESULTS/'artifact_audit.json',dict(passed=True,freeze_integrity=integrity,freeze_commit=FREEZE_COMMIT,
        old_agent_model_environment_prompts_data_unchanged=True,source_checkpoint_states_reused=True,
        original_recovery_reused=True,new_goal_stack_controller_implemented=False,new_branches=10,
        independent_parent_episodes=1,new_requests=cost['new_requests'],cost_usd=cost['cost_usd'],analysis_model_calls=0,
        private_key_scan_performed=bool(key),private_key_absent=True if key else None,
        artifact_files=len(manifest),artifact_bytes=sum(v['bytes'] for v in manifest.values())))
    print(json.dumps(read(RESULTS/'artifact_audit.json')),flush=True)

if __name__=='__main__':main()
