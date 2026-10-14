import gzip
import hashlib
import json
import subprocess
from .common import *

def main():
    offline();integrity=check_freeze();ver=read(RESULTS/'verification.json');assert ver['passed']
    assert sha(RESULTS/'freeze.json')==hashlib.sha256(subprocess.check_output(['git','show','1353d35:results/stage29/freeze.json'],cwd=ROOT)).hexdigest()
    s=read(RESULTS/'summary.json');assert s['new_model_calls']==s['new_cost_usd']==0 and not s['oracle_goal_stack_model_replay_executed']
    assert read(ROOT/'results/stage28/verification.json')['passed']
    assert len(list((REPORTS/'timelines').glob('*.md')))==20
    logs=RESULTS/'logs';logs.mkdir(exist_ok=True)
    for p in [RUNTIME/'native_probe.log',RUNTIME/'verify.log']:
        if p.exists():(logs/(p.name+'.gz')).write_bytes(gzip.compress(p.read_bytes(),mtime=0))
    write(RESULTS/'analysis_development_notes.json',dict(experiment_data_or_policy_changed=False,new_model_calls=0,
        offline_script_development_fixes=[
            'extract.py first run wrote its outputs then failed at final status printing because json was not imported; import added and offline extraction recomputed.',
            'annotations.py initial serialization passed evidence twice to dict; separate evidence_steps and raw evidence fields fixed before generating annotations.'
        ],note='These were new analysis-code development errors, not changes or reruns of the frozen experiment.'))
    files=[p for d in [ROOT/'scar_stage29',RESULTS,REPORTS] for p in d.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc']
    key=None
    if (ROOT.parent/'miyao.txt').exists():
        from scar.providers.deepseek import read_key
        key=read_key(ROOT.parent/'miyao.txt').encode()
    for p in files:
        b=p.read_bytes();assert p.stat().st_size<50*1024*1024,str(p)
        if key:
            assert key not in b,str(p)
            if p.suffix=='.gz':assert key not in gzip.decompress(b),str(p)
    exclude={'artifact_manifest.json','artifact_audit.json','publication.json','change_accounting.json','Git变更记录.md'}
    manifest={str(p.relative_to(ROOT)):dict(sha256=sha(p),bytes=p.stat().st_size) for p in sorted(files) if p.name not in exclude}
    write(RESULTS/'artifact_manifest.json',dict(files=manifest,metadata_excluded=sorted(exclude)))
    write(RESULTS/'artifact_audit.json',dict(passed=True,freeze_integrity=integrity,freeze_matches_committed_copy=True,source_actions=3116,
        paired_checkpoints=10,independent_parent_episodes=1,paper_trees=10,full_suffix_timelines=20,new_model_calls=0,cost_usd=0,
        private_key_scan_performed=bool(key),private_key_absent=True if key else None,old_agent_model_environment_prompts_data_unchanged=True,
        new_goal_stack_implemented=False,oracle_goal_stack_model_replay_executed=False,
        artifact_files=len(manifest),artifact_bytes=sum(f['bytes'] for f in manifest.values())))
    print(json.dumps(read(RESULTS/'artifact_audit.json')),flush=True)

if __name__=='__main__':main()
