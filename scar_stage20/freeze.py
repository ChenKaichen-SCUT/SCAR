"""Freeze a single SCAR20 variant and a 24-run local schedule before any API call."""
import datetime
import statistics
import subprocess
from .common import ROOT, RESULTS, ENGINE_COMMIT, load, write, read_gzip, sha
from .config import (PROVIDER, BASE_COMMIT, WORKERS, MAX_ACTIONS, MAX_PLANNING_CALLS,
                     INTENT_ACTION_LIMIT, EXPLORATORY_ACTION_LIMIT, PRECONDITION_DEPTH_LIMIT)


def main():
    if (RESULTS/'freeze.json').exists():raise FileExistsError('Cannot replace an existing formal freeze')
    receipt=load(RESULTS/'preflight_local.json')
    assert receipt['passed'] and receipt['api_calls']==0 and receipt['unit_tests']>=20
    assert receipt['old_success_tasks_checked']==12 and receipt['stagnation_states_checked']==2
    assert all(sha(ROOT/p)==h for p,h in receipt['source_hashes'].items())
    prior=load(RESULTS/'prior_manifest.json')['files']
    assert all(sha(ROOT/p)==h for p,h in prior.items())
    tasks=load(RESULTS/'tasks.json')
    assert tasks==load(ROOT/'results/stage17/tasks.json') and len(tasks)==24
    assert sha(RESULTS/'initial_public_histories.jsonl.gz')==sha(ROOT/'results/stage17/initial_public_histories.jsonl.gz')
    assert not (RESULTS/'runs').exists()
    old=[]
    for t in tasks:old += read_gzip(ROOT/'results/stage19/runs'/f"{t['task_id']}__SCAR19/requests.jsonl.gz")
    price=PROVIDER['pricing_usd_per_million']
    budget=dict(global_cap_usd=3,episode_cap_usd=.25,historical_stage19_requests=len(old),
        historical_stage19_cost=sum(r['charged_or_reserved_usd'] for r in old),
        max_logical_subgoal_requests=24*MAX_PLANNING_CALLS,max_attempts_per_logical_request=3,
        historical_mean_cost_scenario_576_calls=24*MAX_PLANNING_CALLS*statistics.mean(r['charged_or_reserved_usd'] for r in old),
        no_cache_6000_input_768_output_576_calls=(6000*price['cache_miss']+768*price['output'])*24*MAX_PLANNING_CALLS/1e6,
        no_cache_10000_input_768_output_576_calls=(10000*price['cache_miss']+768*price['output'])*24*MAX_PLANNING_CALLS/1e6,
        caveat='Scenarios, not guarantees; new prompt lengths and paid parsing retries vary. Shared reservations enforce the cap; budget stops remain in all 24 denominators.')
    write(RESULTS/'budget_estimate.json',budget)
    files={p:h for p,h in prior.items() if p.endswith('.py')}
    files.update({str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'scar_stage20').rglob('*.py')})
    for name in ('tasks.json','initial_public_histories.jsonl.gz','preflight_local.json','preflight_branches.jsonl.gz','budget_estimate.json','prior_manifest.json','interface_regression.json','interface_regression.jsonl.gz','stagnation_regression.json'):
        files['results/stage20/'+name]=sha(RESULTS/name)
    data=dict(schema_version=1,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        algorithm_base_commit=BASE_COMMIT,parent_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        engine_commit=ENGINE_COMMIT,files=files,methods=['SCAR20'],worker_processes=WORKERS,
        schedule=[[t['task_id'],'SCAR20'] for t in tasks],model_config=PROVIDER,
        max_steps=MAX_ACTIONS,internal_P3_horizon=100,report_budgets=[60,80,100],
        intent_action_limit=INTENT_ACTION_LIMIT,exploratory_intent_limit=EXPLORATORY_ACTION_LIMIT,
        prerequisite_depth_limit=PRECONDITION_DEPTH_LIMIT,max_logical_calls_per_episode=MAX_PLANNING_CALLS,
        site='local',site_override='Persistent user authorization for local execution, up to 12 independent workers.',
        success_rule='native crafted target during task >= required amount AND currently possesses required amount',
        prefix='same target-independent Stage17 public histories; robot 0 / quarantine 28 excluded from action budget',
        new_schema='type,target,entry,evidence_ids,direction,uncertainty; completion computed deterministically; no action wrapper',
        normalization='single JSON code fence, unique field aliases, discard redundant completion, scalar uncertainty to list; never fix quotes, target names, evidence IDs or reasons',
        evidence='content-addressed public snapshot records with source and observation time; actual entry/target checked separately; deep-copied prompt audit',
        policy='P3 final progress and compatible active material intent; persistent/suspended bounded intents; inherited reliable FIFO; resolve unfinished public dependency chain; specific blocker requests; bounded public recovery entries; explicit method_stalled without purposeless wait',
        context_replanning_limit=2,logical_requests_per_decision=2,suspended_intent_resume_limit=2,
        public_evidence_prompt_limit=dict(records=64,characters=14000),
        knowledge='native public P1 ingestion only; missing necessary X is an unknown-type required area object; hypotheses never registered as facts',
        acquisition='Stage18 public nominal deficit and held-first transfer; no consequence memory; no new batch, rounding or consistency rules',
        retry='Stage17 accounting/cache/concurrency retained in independent provider; at most 3 paid attempts, deterministic normalization; failed parsing falls back without fabricated response; uncertain billing abort; completed failures never rerun',
        preservation='all old source/results unchanged, no baseline runs, no ablations',
        formal_api_before_freeze=0,holdout=False,
        interpretation='24 previously analysed development tasks; one temperature .7 sample; descriptive historical comparison, no independent generalization or strict causal/significance claim')
    write(RESULTS/'freeze.json',data)
    write(RESULTS/'research_state.json',dict(phase='frozen_ready_to_run',formal_started=False))
    print(budget)


if __name__=='__main__':main()
