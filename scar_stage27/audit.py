"""Final integrity, completeness, credential exclusion and artifact accounting."""
import csv
import gzip
import hashlib
import json
import math
import subprocess
from .common import *

def main():
    offline();integrity=check_freeze()
    frozen=subprocess.check_output(['git','show','7b26e15:results/stage27/freeze.json'],cwd=ROOT)
    assert hashlib.sha256(frozen).hexdigest()==sha(RESULTS/'freeze.json')
    ss=samples();summary=read(RESULTS/'summary.json');cost=read(RESULTS/'cost_reconciliation.json');ver=read(RESULTS/'verification.json')
    assert read(RESULTS/'completion.json')['complete'] and ver['passed'] and cost['passed']
    assert len(ss)==336 and sum(s['action_test_eligible'] for s in ss)==334
    assert ver['diagnostic_jobs']==1004 and len(read(RESULTS/'paired_comparison.json'))==334
    judgments=read(RESULTS/'understanding_judgments.json');assert set(judgments)=={s['id'] for s in ss}
    assert summary['new_requests']==cost['new_requests'] and summary['input_tokens']==cost['input_tokens'] and summary['output_tokens']==cost['output_tokens']
    assert math.isclose(summary['cost_usd'],cost['cost_usd'],abs_tol=1e-12)
    assert ver['exact_model_contexts']<=1140
    evidence=[]
    for index,s in enumerate(ss,1):
        base=RESULTS/'probes'/s['id']
        for condition in ['understanding','A','B'] if s['action_test_eligible'] else ['understanding']:
            r=read(base/condition/'result.json');qq=rows(base/condition/'requests.jsonl.gz')
            evidence.append(dict(id=s['id'],trajectory=s['trajectory'],trigger_step=s['step'],condition=condition,
                failure_database_line=index,source_trajectory=s['source_trajectory'],source_line=s['source_line'],
                result=str((base/condition/'result.json').relative_to(ROOT)),request_ids=[q['request_id'] for q in qq],
                checkpoint=str((RESULTS/'checkpoints'/s['id']).relative_to(ROOT)) if s['action_test_eligible'] else None,
                state_hash=s['post_state_hash']))
            for c in r.get('chain',[]):assert c['step']<=300
    gzwrite(RESULTS/'evidence_index.jsonl.gz',evidence)
    logs=RESULTS/'logs';logs.mkdir(exist_ok=True)
    sources=[RUNTIME/'batch.log',RUNTIME/'verify.log',RUNTIME.parent/'stage27_prepare.log',RUNTIME.parent/'stage27_smoke.log']
    for p in sources:
        if p.exists():(logs/(p.name+'.gz')).write_bytes(gzip.compress(p.read_bytes(),mtime=0))
    from scar.providers.deepseek import read_key
    secret=read_key(ROOT.parent/'miyao.txt').encode();assert secret
    exclusions={'artifact_manifest.json','artifact_audit.json','publication.json','change_accounting.json','Git变更记录.md'}
    paths=[p for folder in [ROOT/'scar_stage27',RESULTS,REPORTS] for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc']
    for p in paths:
        content=p.read_bytes();assert secret not in content,'Credential in artifact'
        if p.suffix=='.gz':assert secret not in gzip.decompress(content),'Credential in compressed artifact'
        assert p.stat().st_size<50*1024*1024,str(p)
    files={str(p.relative_to(ROOT)):dict(sha256=sha(p),bytes=p.stat().st_size) for p in sorted(paths) if p.name not in exclusions}
    write(RESULTS/'artifact_manifest.json',dict(files=files,metadata_excluded=sorted(exclusions)))
    write(RESULTS/'artifact_audit.json',dict(passed=True,freeze_integrity=integrity,freeze_matches_committed_copy=True,
        complete_jobs=1004,failures=336,action_pairs=334,independent_parent_episodes=1,new_requests=cost['new_requests'],cost_usd=cost['cost_usd'],
        exact_native_replays=ver['exact_native_actions'],private_key_absent=True,old_algorithm_and_sources_unchanged=True,
        analysis_model_calls=0,artifact_files=len(files),artifact_bytes=sum(f['bytes'] for f in files.values())))
    print(json.dumps(read(RESULTS/'artifact_audit.json')),flush=True)

if __name__=='__main__':main()
