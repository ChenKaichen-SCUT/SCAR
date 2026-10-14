"""Completeness, original artifact immutability and credential exclusion."""
import hashlib
import math
import subprocess
from .common import *

def main():
    offline();integrity=check_freeze()
    frozen=subprocess.check_output(['git','show','07c8284:results/stage28/freeze.json'],cwd=ROOT)
    assert hashlib.sha256(frozen).hexdigest()==sha(RESULTS/'freeze.json')
    assert read(RESULTS/'completion.json')['complete']
    summary=read(RESULTS/'summary.json');ver=read(RESULTS/'verification.json');cost=read(RESULTS/'cost_reconciliation.json')
    assert ver['passed'] and cost['passed'] and summary['pairs']==10
    assert len(rows(RESULTS/'failure_recovery_database.jsonl.gz'))==336
    assert len(read(RESULTS/'selected_pair_semantic_review.json'))==10
    assert summary['new_requests']==cost['new_requests'] and math.isclose(summary['cost_usd'],cost['cost_usd'],abs_tol=1e-12)
    evidence=[];sources={p:rows(ROOT/p) for p in {s['source_trajectory'] for s in samples()}}
    for line,s in enumerate(samples(),1):
        entry=dict(id=s['id'],failure_database_line=line,source_trajectory=s['source_trajectory'],source_failure_line=s['source_line'],
            failure_absolute_step=s['step'],state_hash=s['post_state_hash'],chain_database_line=line,
            next20_source_lines=[dict(absolute_step=r['step'],line=i) for i,r in enumerate(sources[s['source_trajectory']],1) if s['step']<r['step']<=s['step']+20])
        if s['id'] in CASES:
            out=RESULTS/'runs'/s['id']/'OracleRecovery';rr=rows(out/'trajectory.jsonl.gz');qq=rows(out/'requests.jsonl.gz')
            entry.update(checkpoint=f'results/stage28/checkpoints/{s["id"]}',oracle_trajectory=str((out/'trajectory.jsonl.gz').relative_to(ROOT)),
                oracle_actions=[dict(line=i,absolute_step=r['step'],state_hash=r['state_hash']) for i,r in enumerate(rr,1)],
                oracle_requests=[dict(line=i,absolute_step=q['step'],ordinal=q['ordinal'],request_id=q['request_id']) for i,q in enumerate(qq,1)])
            assert all(s['step']<r['step']<=300 for r in rr)
        evidence.append(entry)
    gzwrite(RESULTS/'evidence_index.jsonl.gz',evidence)
    logs=RESULTS/'logs';logs.mkdir(exist_ok=True)
    for p in [RUNTIME/'batch.log',RUNTIME/'verify.log',RUNTIME.parent/'stage28_prepare.log',RUNTIME.parent/'stage28_smoke.log']:
        if p.exists():(logs/(p.name+'.gz')).write_bytes(gzip.compress(p.read_bytes(),mtime=0))
    from scar.providers.deepseek import read_key
    key=read_key(ROOT.parent/'miyao.txt').encode();assert key
    excluded={'artifact_manifest.json','artifact_audit.json','publication.json','change_accounting.json','Git变更记录.md'}
    paths=[p for folder in [ROOT/'scar_stage28',RESULTS,REPORTS] for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc']
    for p in paths:
        b=p.read_bytes();assert key not in b,'Credential in artifact'
        if p.suffix=='.gz':assert key not in gzip.decompress(b),'Credential in compressed artifact'
        assert p.stat().st_size<50*1024*1024,str(p)
    files={str(p.relative_to(ROOT)):dict(sha256=sha(p),bytes=p.stat().st_size) for p in sorted(paths) if p.name not in excluded}
    write(RESULTS/'artifact_manifest.json',dict(files=files,metadata_excluded=sorted(excluded)))
    write(RESULTS/'artifact_audit.json',dict(passed=True,freeze_integrity=integrity,freeze_matches_committed_copy=True,
        independent_parent_episodes=1,failure_events=336,paired_checkpoints=10,new_requests=cost['new_requests'],cost_usd=cost['cost_usd'],
        exact_native_replays=ver['exact_native_actions'],isolated_probe_actions=ver['isolated_probe_actions'],
        old_agent_model_environment_sources_unchanged=True,private_key_absent=True,analysis_model_calls=0,
        artifact_files=len(files),artifact_bytes=sum(f['bytes'] for f in files.values())))
    print(json.dumps(read(RESULTS/'artifact_audit.json')),flush=True)

if __name__=='__main__':main()
