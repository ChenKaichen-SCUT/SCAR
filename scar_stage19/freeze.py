"""Freeze a single SCAR19 variant and a 24-run local schedule before any API call."""
import datetime
import statistics
import subprocess
from .common import ROOT, RESULTS, ENGINE_COMMIT, load, write, read_gzip, sha
from .config import (PROVIDER, BASE_COMMIT, WORKERS, MAX_ACTIONS, MAX_PLANNING_CALLS,
                     INTENT_ACTION_LIMIT, EXPLORATORY_ACTION_LIMIT, PRECONDITION_DEPTH_LIMIT)


def main():
    if (RESULTS/'freeze.json').exists():raise FileExistsError('Cannot replace an existing formal freeze')
    receipt=load(RESULTS/'preflight_local.json')
    assert receipt['passed'] and receipt['api_calls']==0 and receipt['unit_tests']>=13
    assert all(sha(ROOT/p)==h for p,h in receipt['source_hashes'].items())
    prior=load(RESULTS/'prior_manifest.json')['files']
    assert all(sha(ROOT/p)==h for p,h in prior.items())
    tasks=load(RESULTS/'tasks.json')
    assert tasks==load(ROOT/'results/stage17/tasks.json') and len(tasks)==24
    assert sha(RESULTS/'initial_public_histories.jsonl.gz')==sha(ROOT/'results/stage17/initial_public_histories.jsonl.gz')
    assert not (RESULTS/'runs').exists()
    old=[]
    for t in tasks:old += read_gzip(ROOT/'results/stage18/runs'/f"{t['task_id']}__SCAR18/requests.jsonl.gz")
    price=PROVIDER['pricing_usd_per_million']
    budget=dict(global_cap_usd=3,episode_cap_usd=.25,historical_stage18_requests=len(old),
        historical_stage18_cost=sum(r['charged_or_reserved_usd'] for r in old),
        max_logical_subgoal_requests=24*MAX_PLANNING_CALLS,max_attempts_per_logical_request=3,
        historical_mean_cost_scenario_576_calls=24*MAX_PLANNING_CALLS*statistics.mean(r['charged_or_reserved_usd'] for r in old),
        no_cache_6000_input_768_output_576_calls=(6000*price['cache_miss']+768*price['output'])*24*MAX_PLANNING_CALLS/1e6,
        caveat='Scenarios, not guarantees; new prompt lengths and paid parsing retries vary. Shared reservations enforce the cap; budget stops remain in all 24 denominators.')
    write(RESULTS/'budget_estimate.json',budget)
    files={p:h for p,h in prior.items() if p.endswith('.py')}
    files.update({str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'scar_stage19').rglob('*.py')})
    for name in ('tasks.json','initial_public_histories.jsonl.gz','preflight_local.json','preflight_branches.jsonl.gz','budget_estimate.json','prior_manifest.json'):
        files['results/stage19/'+name]=sha(RESULTS/name)
    data=dict(schema_version=1,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        algorithm_base_commit=BASE_COMMIT,parent_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        engine_commit=ENGINE_COMMIT,files=files,methods=['SCAR19'],worker_processes=WORKERS,
        schedule=[[t['task_id'],'SCAR19'] for t in tasks],model_config=PROVIDER,
        max_steps=MAX_ACTIONS,internal_P3_horizon=100,report_budgets=[60,80,100],
        intent_action_limit=INTENT_ACTION_LIMIT,exploratory_intent_limit=EXPLORATORY_ACTION_LIMIT,
        prerequisite_depth_limit=PRECONDITION_DEPTH_LIMIT,max_logical_calls_per_episode=MAX_PLANNING_CALLS,
        site='local',site_override='Latest user explicitly requested local code and experiments, up to 12 parallel; supersedes server wording in guide19.',
        success_rule='native crafted target during task >= required amount AND currently possesses required amount',
        prefix='same target-independent Stage17 public histories; robot 0 / quarantine 28 excluded from action budget',
        new_schema='real subgoal JSON: type,target,entry,public_evidence,direction,completion,uncertainty; no action wrapper',
        policy='P3 supported final progress; persistent accepted intent; public missing area prerequisite path/construction; reliable inherited FIFO; request one subgoal for actual gap; bounded old S1 fallback',
        knowledge='native public P1 ingestion only; missing necessary X is an unknown-type required area object; hypotheses never registered as facts',
        acquisition='Stage18 public nominal deficit and held-first transfer; no consequence memory; no new batch, rounding or consistency rules',
        retry='shared Stage17 provider; at most 3 paid attempts, exact cached responses on resume, uncertain billing abort; completed failures never rerun',
        preservation='all old source/results unchanged, no baseline runs, no ablations',
        formal_api_before_freeze=0,holdout=False,
        interpretation='24 previously analysed development tasks; one temperature .7 sample; descriptive historical comparison, no independent generalization or strict causal/significance claim')
    write(RESULTS/'freeze.json',data)
    write(RESULTS/'research_state.json',dict(phase='frozen_ready_to_run',formal_started=False))
    print(budget)


if __name__=='__main__':main()
