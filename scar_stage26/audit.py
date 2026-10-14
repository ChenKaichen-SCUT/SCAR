"""Cross-artifact accounting, immutable-source and credential exclusion checks."""
import hashlib
import math
import subprocess
import csv
from .common import *

def main():
    offline();integrity=check_freeze();completion=read(RESULTS/'completion_audit.json');cost=read(RESULTS/'cost_reconciliation.json')
    assert completion['complete'] and read(RESULTS/'completion.json')['complete']
    frozen=subprocess.check_output(['git','show','800096d:results/stage26/freeze.json'],cwd=ROOT)
    assert hashlib.sha256(frozen).hexdigest()==sha(RESULTS/'freeze.json')
    pairs=read(RESULTS/'paired_comparison.json');assert len(pairs)==10 and {p['start'] for p in pairs}==set(CASES)
    index=rows(RESULTS/'evidence_index.jsonl.gz');assert len(index)==completion['verified_oracle_native_actions']
    assert len({(x['case'],x['step']) for x in index})==len(index)
    assert sum(x['oracle_replacement'] for x in index)==10
    assert all(x['oracle_replacement'] or x['action']==x['proposed_action'] for x in index)
    allq=[];request_index=[];old={(q['step'],q['ordinal']):q for q in rows(SOURCE/'requests.jsonl.gz')}
    for n in CASES:
        folder=RESULTS/'runs'/case_id(n)/'Oracle';rr=rows(folder/'trajectory.jsonl.gz');qq=rows(folder/'requests.jsonl.gz');s=read(folder/'summary.json');allq+=qq
        assert len(rr)==s['steps'] and rr[0]['step']==n and s['last_step']<=300
        if s['status']=='step_limit':assert len(rr)==301-n
        assert read(RESULTS/'verification'/f'{case_id(n)}.json')['passed']
        assert rr[0]['state_hash']==read(RESULTS/'checkpoints'/case_id(n)/'oracle_probe.json')['state_hash']
        for q in qq:assert q['step']>n,'Intervention must reuse source response, not a new model sample.'
        for line,q in enumerate(qq,1):
            request_index.append(dict(case=case_id(n),step=q['step'],ordinal=q['ordinal'],origin='new',request_id=q['request_id'],
                input_tokens=q.get('usage',{}).get('prompt_tokens',0),output_tokens=q.get('usage',{}).get('completion_tokens',0),
                new_cost_usd=q.get('cost_usd',0),status=q['status'],reference=str((folder/'requests.jsonl.gz').relative_to(ROOT))+f':{line}',
                environment_action_executed=any(r['step']==q['step'] for r in rr)))
        for reused in rows(folder/'source_reuse.jsonl.gz'):
            q=old[reused['step'],reused['ordinal']]
            request_index.append(dict(case=case_id(n),step=q['step'],ordinal=q['ordinal'],origin='source_reuse',request_id=q['request_id'],
                input_tokens=q['usage']['prompt_tokens'],output_tokens=q['usage']['completion_tokens'],new_cost_usd=0,status=q['status'],
                reference='results/stage25/runs/remnant__s42__AGC-v2/requests.jsonl.gz',environment_action_executed=True))
    assert len(allq)==cost['new_requests'] and len({q['request_id'] for q in allq})==len(allq)
    assert math.isclose(sum(q.get('cost_usd',0) for q in allq),cost['cost_usd'],abs_tol=1e-12)
    with (RESULTS/'request_index.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(request_index[0]),lineterminator='\n');w.writeheader();w.writerows(request_index)
    from scar.providers.deepseek import read_key
    secret=read_key(ROOT.parent/'miyao.txt').encode();assert secret
    paths=[p for folder in [ROOT/'scar_stage26',RESULTS,REPORTS] for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc']
    for p in paths:
        content=p.read_bytes();assert secret not in content,'Private credential in artifact'
        if p.suffix=='.gz':assert secret not in gzip.decompress(content),'Private credential in compressed artifact'
        assert p.stat().st_size<50*1024*1024,(str(p),'oversize')
    exclusions={'artifact_manifest.json','artifact_audit.json','publication.json','change_accounting.json','Git变更记录.md'}
    files={str(p.relative_to(ROOT)):dict(sha256=sha(p),bytes=p.stat().st_size) for p in sorted(paths) if p.name not in exclusions}
    write(RESULTS/'artifact_manifest.json',dict(files=files,metadata_excluded=sorted(exclusions)))
    receipt=dict(passed=True,oracle_branches=10,independent_parent_episodes=1,source_actions_replayed=300,
        oracle_actions_replayed=len(index),exact_model_contexts_replayed=completion['verified_model_contexts'],new_requests=cost['new_requests'],cost_usd=cost['cost_usd'],
        freeze_integrity=integrity,freeze_manifest_matches_committed_copy=True,old_algorithm_and_sources_unchanged=True,
        private_key_absent=True,artifact_files=len(files),artifact_bytes=sum(x['bytes'] for x in files.values()),new_analysis_model_calls=0)
    write(RESULTS/'artifact_audit.json',receipt);print(json.dumps(receipt))

if __name__=='__main__':main()
