"""Final server-only acceptance of archived runs, billing and publication files."""
import datetime
import os
import subprocess
from .common import ROOT, RESULTS, REPORTS, load, write, read_gzip, sha, deny_network
from .run import check_freeze

REPORT_NAMES=('代码改进说明.md','需求收取与负面后果分析.md','控制器仲裁分析.md','知识到执行转化分析.md',
              '24任务性能对比.md','逐任务成败变化.md','实验总报告.md','复现指南.md')


def main():
    deny_network();freeze=check_freeze()
    engine_root=os.environ['AGENTODYSSEY_ROOT']
    engine_commit=subprocess.check_output(['git','-C',engine_root,'rev-parse','HEAD'],text=True).strip()
    engine_dirty=subprocess.check_output(['git','-C',engine_root,'status','--porcelain'],text=True).strip()
    assert engine_commit==freeze['engine_commit'] and not engine_dirty
    prior=load(RESULTS/'prior_manifest.json')['files']
    assert all(sha(ROOT/p)==h for p,h in prior.items())
    tasks=load(RESULTS/'tasks.json');assert len(tasks)==24
    assert tasks==load(ROOT/'results/stage17/tasks.json')
    assert len(list((RESULTS/'runs').glob('*/summary.json')))==24
    rows=[];requests=[];run_summaries=[];episode_costs={}
    freeze_time=datetime.datetime.fromisoformat(freeze['created_utc']).timestamp()
    for t in tasks:
        p=RESULTS/'runs'/f"{t['task_id']}__SCAR18"
        s=load(p/'summary.json');rr=read_gzip(p/'trajectory.jsonl.gz');qq=read_gzip(p/'requests.jsonl.gz')
        assert s['method']=='SCAR18' and len(rr)==s['steps']<=100
        assert s['status'] in ('success','game_failure','step_limit','api_budget_abort','model_parse_exception','api_uncertain_abort','environment_exception','method_exception')
        assert len({q['request_id'] for q in qq})==len(qq)
        assert all(q['start']>=freeze_time for q in qq)
        for q in qq:
            assert q['model']=='deepseek-flash' and q['temperature']==.7 and q['thinking']=='disabled' and q['max_tokens']==768
            assert 0<=q['attempt']<3 and q['phase']=='action'
        for step,r in enumerate(rr,1):
            assert r['step']==step and r['method']=='SCAR18'
            ok=[q for q in qq if q['step']==step and q['status']=='ok']
            assert len(ok)==1
            assert ok[0]['parsed']['action']==r['decision']['decision']['proposed_action']
            assert len(r['decision']['memory'])<=5
            summary=r['decision']['decision']['fact_summary']
            assert summary['characters']<=6000 and len(summary['records'])<=48
            if r['success']:assert r['target_produced_during_task']>=t['target_amount'] and r['physical_after']['target_owned']>=t['target_amount']
        assert rr[-1]['success']==s['success'] if rr else not s['success']
        requests.extend(qq);rows.extend(rr);run_summaries.append(s)
        episode_costs[t['task_id']]=sum(q['charged_or_reserved_usd'] for q in qq)
    assert len({q['request_id'] for q in requests})==len(requests)
    ledger=load(RESULTS/'cost_ledger.json');account={r['request_id']:r for r in ledger['requests']}
    assert set(account)=={q['request_id'] for q in requests}
    for q in requests:
        charge=account[q['request_id']]['charged_usd']
        assert charge is not None and abs(charge-q['charged_or_reserved_usd'])<1e-12
    cost=sum(q['charged_or_reserved_usd'] for q in requests)
    assert abs(cost-ledger['committed_usd'])<1e-9 and cost<=3
    assert all(value<=.25 for value in episode_costs.values())
    for name in ('replay_server.json','analysis_receipt.json','same_state_effects_receipt.json'):
        assert load(RESULTS/name)['passed']
    assert load(RESULTS/'replay_server.json')['real_replay_actions']==len(rows)
    assert load(RESULTS/'same_state_effects_receipt.json')['replayed_actual_actions']==len(rows)
    for r in read_gzip(RESULTS/'same_state_effects_server.jsonl.gz'):
        if r['actual_terminal_failure'] or r['alternate_terminal_failure']:
            assert 'higher_post_action_health' not in r['actual_advantage_dimensions']+r['alternate_advantage_dimensions']
    assert not (RESULTS/'replay_local.json').exists(), 'Latest instruction prohibits local post-experiment replay'
    for name in REPORT_NAMES:assert (REPORTS/name).is_file() and (REPORTS/name).stat().st_size>1000
    stats=load(RESULTS/'per_task.json');new=[r for r in stats if r['method']=='SCAR18']
    assert len(stats)==144 and len(new)==24 and sum(r['steps'] for r in new)==len(rows)
    assert sum(r['success'] for r in new)==sum(r['success'] for r in run_summaries)
    data=dict(passed=True,site='server',freeze_hash=sha(RESULTS/'freeze.json'),
        engine_commit=engine_commit,engine_worktree_clean=True,
        historical_files_unchanged=len(prior),frozen_source_and_protocol_files_unchanged=len(freeze['files']),
        unique_formal_runs=24,finalized_runs=24,actions=len(rows),requests=len(requests),
        success=sum(r['success'] for r in new),paid_format_or_api_errors=sum(q['status']!='ok' for q in requests),
        extra_analysis_api_calls=0,ledger_rows=len(account),ledger_matches_requests=True,
        cost_usd=cost,all_requests_after_freeze=True,all_successes_native_craft_and_possession=True,
        all_reports_present=list(REPORT_NAMES),server_replay_passed=True,separate_server_counterfactual_passed=True,
        local_post_experiment_replay_performed=False,latest_user_scope=load(RESULTS/'verification_scope.json'))
    write(RESULTS/'verification.json',data)
    write(RESULTS/'research_state.json',dict(phase='complete_server_verified',formal_started=True,formal_complete=True,
        total_runs=24,archived_runs=24,successes=data['success'],actions=len(rows),cost_usd=cost,
        algorithm_frozen=True,failed_runs_rerun=0,baseline_runs_added=0,next_stage_started=False,
        local_post_experiment_replay_performed=False))
    files={}
    for directory in (ROOT/'scar_stage18',RESULTS,REPORTS):
        for p in directory.rglob('*'):
            if p.is_file() and p.name!='artifact_manifest.json' and '__pycache__' not in p.parts and p.suffix!='.pyc':
                files[str(p.relative_to(ROOT))]=sha(p)
    write(RESULTS/'artifact_manifest.json',dict(schema_version=1,files=files,
        scope='all self-authored Stage18 sources/reports plus archived formal and offline evidence; manifest excludes itself; third-party engine and private credentials excluded'))
    print(data)


if __name__=='__main__':main()
