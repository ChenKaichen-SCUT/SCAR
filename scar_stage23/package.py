"""Offline final completeness, integrity and publication artifact audit."""
import datetime
import re
from .common import *


def main():
    from scar_stage22b.common import forbid_network
    forbid_network();integrity=check_freeze()
    assert read(RESULTS/'batch_completion.json')['complete']
    verification=[read(RESULTS/'verification'/f'{case_id(n)}.json') for n in CASES]
    assert all(r['passed'] and r['new_model_calls']==0 for r in verification)
    native=sum(v.get('exact_native_steps',0) for r in verification for v in r['variants'])
    contexts=sum(v.get('exact_model_contexts',0) for r in verification for v in r['variants'])
    assert native==contexts==3538
    metrics=read(RESULTS/'metrics.json');assert len(metrics)==30 and len({(r['case'],r['variant']) for r in metrics})==30
    assert sum(r['actual_actions'] for r in metrics)==5307
    assert all(r['actual_actions']==r['remaining_budget'] for r in metrics)
    assert all(r['new_model_requests']==0 for r in metrics if r['variant']=='Stage18-Origin')
    cost=read(RESULTS/'cost_reconciliation.json');assert cost['passed']
    assert cost['new_requests']==sum(r['new_model_requests'] for r in metrics)
    assert cost['unique_new_anomalies']==0
    contrasts=read(RESULTS/'paired_contrasts.json')
    identical=[r['case'] for r in contrasts if r.get('identical_action_and_state_path')]
    assert len(identical)==8
    local=[r for r in contrasts if r['comparison'].startswith('Stage18-Origin')]
    assert len(local)==20 and all(r['same_state_at_divergence'] and r['same_context_at_divergence'] and r['same_raw_response_at_divergence'] for r in local)
    names=['Stage23实验报告.md','三版本轨迹对比.md','reset前后行为变化分析.md','stale_goal统计.md','wait行为统计.md','关键反事实案例.md','Stage18.1开发建议.md']
    assert all((REPORTS/name).exists() for name in names)
    roots=[ROOT/'scar_stage23',REPORTS,RESULTS]
    files=sorted(p for root in roots for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    excluded={'artifact_manifest.json','package_receipt.json','publication.json','publication_changes.json'}
    files=[p for p in files if p.name not in excluded]
    # Match credential-shaped values without ever including a value in output.
    patterns=[re.compile(rb'\bsk-[a-zA-Z0-9_-]{16,}\b'),re.compile(rb'Authorization\s*[:=]\s*Bearer\s+[A-Za-z0-9_-]{16,}',re.I)]
    key_path=ROOT.parent/'miyao.txt'
    if key_path.exists():
        for key in re.findall(rb'\bsk-[a-zA-Z0-9_-]{16,}\b',key_path.read_bytes()):patterns.append(re.compile(re.escape(key)))
    for p in files:
        assert p.stat().st_size<50*1024*1024,('Artifact too large',str(p.relative_to(ROOT)))
        data=p.read_bytes()
        if p.suffix=='.gz':data=gzip.decompress(data)
        assert not any(pattern.search(data) for pattern in patterns),('Credential-shaped content',str(p.relative_to(ROOT)))
    receipt=dict(completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),passed=True,
        independent_parent_episodes=1,checkpoint_count=10,completed_trace_slots=30,unfinished_slots=0,
        logical_action_rows=5307,original_native_verified_steps=300,intervention_native_verified_steps=native,
        intervention_model_contexts_verified=contexts,first_divergence_same_state_context_response_pairs=20,
        identical_reset_oracle_paths=identical,freeze_integrity=integrity,new_model_calls_during_analysis=0,
        new_experiment_requests=cost['new_requests'],usage_priced_usd=cost['usage_priced_usd'],
        credential_scan_passed=True,artifact_files_scanned=len(files),largest_artifact_bytes=max(p.stat().st_size for p in files),
        verdict=read(RESULTS/'conclusion.json')['verdict'])
    write(RESULTS/'package_receipt.json',receipt)
    files.append(RESULTS/'package_receipt.json')
    write(RESULTS/'artifact_manifest.json',dict(files={str(p.relative_to(ROOT)):dict(sha256=sha(p),bytes=p.stat().st_size) for p in files},
        excluded_self='results/stage23/artifact_manifest.json',post_commit_provenance_excluded=['publication.json','publication_changes.json']))
    print(json.dumps(receipt,ensure_ascii=False))


if __name__=='__main__':main()
