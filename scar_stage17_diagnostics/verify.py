"""Reconcile diagnostic outputs against all raw runs and immutable input hashes."""
import math
import re
import socket
import statistics as S
from .common import *

def run():
    deny_network();unchanged=baseline()
    try:socket.create_connection(('127.0.0.1',1))
    except RuntimeError as e:assert 'prohibits' in str(e)
    else:raise AssertionError('Offline guard failed')
    tasks=load(RESULTS/'tasks.json');runs=load(OUT/'per_run.json');stats=load(OUT/'statistics.json')
    assert len(tasks)==24 and len(runs)==120 and len({(r['task_id'],r['method']) for r in runs})==120
    assertions=0
    for t in tasks:
        for m in METHODS:
            r=next(r for r in runs if r['task_id']==t['task_id'] and r['method']==m)
            raw=read_gzip(run_dir(t,m)/'trajectory.jsonl.gz');req=read_gzip(run_dir(t,m)/'requests.jsonl.gz')
            assert len(raw)==r['steps']<=100 and len(req)==r['api_calls']
            assert math.isclose(sum(q['charged_or_reserved_usd'] for q in req),r['cost_usd'],abs_tol=1e-12)
            assert all(q.get('usage') for q in req)
            assert r['success']==bool(raw and raw[-1]['success'])
            assert all(a['step']==i+1 for i,a in enumerate(raw));assertions+=6
    for m in METHODS:
        rr=[r for r in runs if r['method']==m];s=stats['methods'][m]
        for b in (60,80,100):assert sum(r['success'] and r['steps']<=b for r in rr)/24==s['R'+str(b)]
        for key in ('steps','api_calls','input_tokens','output_tokens','cost_usd'):
            sk='total_actions' if key=='steps' else key
            assert math.isclose(sum(r[key] for r in rr),s[sk],abs_tol=1e-10)
        success=[r['steps'] for r in rr if r['success']]
        assert S.mean(success)==s['success_steps_mean'] and S.median(success)==s['success_steps_median'];assertions+=9
    for m,p in stats['paired'].items():assert sum(p['counts'].values())==24 and len(p['tasks'])==24
    cf=read_gzip(OUT/'counterfactual_local.jsonl.gz');audit=read_gzip(OUT/'controller_audit.jsonl.gz')
    assert len(cf)==len(audit)==635 and sum(r['overridden'] for r in cf)==471
    local=load(OUT/'counterfactual_local_receipt.json');server=load(OUT/'counterfactual_server_receipt.json')
    assert local['output_sha256']==server['output_sha256']==sha(OUT/'counterfactual_local.jsonl.gz')
    assert local['all_factual_hashes_match'] and server['all_factual_hashes_match']
    server_stats=load(OUT/'server_analysis_receipt.json')
    assert server_stats['passed'] and all(sha(OUT/n)==h for n,h in server_stats['files'].items())
    for c in cf:
        if c['alternate']:
            assert c['proposal']!=c['actual_action']
            if 'proposal_avoids_immediate_terminal_failure' in c['local_dimensions']:
                assert not c['alternate']['death'] and not c['alternate']['done'] and c['alternate']['gains']['health']>0
    assert sum('proposal_avoids_immediate_terminal_failure' in c['local_dimensions'] for c in cf)==6
    errors=load(OUT/'response_errors.json')
    assert len(errors)==108 and sum(e['terminal'] for e in errors)==21
    assert len({(e['task_id'],e['method']) for e in errors if e['terminal']})==7
    assert all(e['terminal'] or e['subsequently_recovered'] for e in errors)
    kn=load(OUT/'knowledge.json');assert len(kn)==120
    for k in kn:
        for b,d in k['snapshots'].items():
            assert d['observed_through']<=int(b)
        for n,first in k['first']['relation'].items():
            assert any(e['product']==n and e['evaluation_step']==first and e['ingredients'] for e in k['events'])
    classes=load(OUT/'failure_classifications.json');assert len(classes)==14
    allids={r['evidence_id'] for r in read_gzip(OUT/'action_evidence.jsonl.gz')}
    assert len(allids)==5042
    for cl in classes:
        for s in cl['annotated_steps']:assert eid(cl,'A0',s) in allids
    zero=next(r for r in runs if r['method']=='A3' and r['target']=='ruin_club')
    assert zero['steps']==0 and zero['api_calls']>0 and zero['status']=='model_parse_exception'
    assert not any(r['status']=='step_limit' for r in runs if r['method']=='A0')
    assert not any(r['target_made_not_obtained'] for r in runs)
    reports=['逐任务性能对比.md','规则知识发现与执行分析.md','SCAR失败原因归因.md','控制器动作覆盖审计.md','下一阶段研究判断.md']
    checked_links=0;cache={}
    for name in reports:
        file=ROOT/'reports/stage17'/name
        for target in re.findall(r'\]\(([^)]+)\)',file.read_text()):
            if '://' in target:continue
            parts=target.split('#',1);destination=(file.parent/parts[0]).resolve()
            assert destination.exists(), (name,target)
            if len(parts)==2:
                if destination not in cache:cache[destination]=destination.read_text()
                assert f'id="{parts[1]}"' in cache[destination],(name,target)
            checked_links+=1
    validation=dict(passed=True,immutable_files_verified=unchanged,runs=120,actual_actions=5042,
        SCAR_actions=635,counterfactual_steps=471,local_server_counterfactual_sha256=local['output_sha256'],
        all_120_original_native_replays=all(load(RESULTS/f'replay_{site}.json')['passed'] for site in ('local','server')),
        reconciled_metric_assertions_at_least=assertions,anomalous_requests=108,terminal_anomaly_runs=7,
        classified_SCAR_failures=14,network_guard_verified=True,new_model_api_calls=0,
        server_statistics_identical=True,report_links_verified=checked_links,
        algorithm_changes=False,model_task_reruns=False)
    write(OUT/'validation.json',validation)
    files=[p for p in (ROOT/'scar_stage17_diagnostics').rglob('*') if p.is_file() and '__pycache__' not in str(p)]
    files += [p for p in OUT.rglob('*') if p.is_file() and p.name!='artifact_manifest.json']
    files += [ROOT/'reports/stage17'/n for n in reports]
    write(OUT/'artifact_manifest.json',dict(files={str(p.relative_to(ROOT)):sha(p) for p in sorted(files)},new_api_calls=0))
    print(json.dumps(validation,ensure_ascii=False))

if __name__=='__main__':run()
