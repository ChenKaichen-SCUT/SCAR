"""Freeze the unique formal policy and runner after both offline acceptances."""
import datetime
import statistics
from .common import ROOT, RESULTS, load, write, sha, read_gzip, ENGINE_COMMIT
from .config import PROVIDER, STAGE16_COMMIT, STAGE17_COMMIT


def main():
    path=RESULTS/'freeze.json'
    if path.exists():raise FileExistsError('An existing formal freeze cannot be replaced')
    for site in ('local','server'):
        receipt=load(RESULTS/f'preflight_{site}.json')
        assert receipt['passed'] and receipt['api_calls']==0 and receipt['terminal_harms_avoided']==6
        assert all(sha(ROOT/p)==h for p,h in receipt['source_hashes'].items())
    prior=load(RESULTS/'prior_manifest.json')['files']
    assert all(sha(ROOT/p)==h for p,h in prior.items())
    tasks=load(RESULTS/'tasks.json')
    assert tasks==load(ROOT/'results/stage17/tasks.json') and len(tasks)==24
    assert sha(RESULTS/'initial_public_histories.jsonl.gz')==sha(ROOT/'results/stage17/initial_public_histories.jsonl.gz')
    calls=[]
    for t in tasks:calls.extend(read_gzip(ROOT/'results/stage17/runs'/f"{t['task_id']}__A0/requests.jsonl.gz"))
    charged=sum(r['charged_or_reserved_usd'] for r in calls)
    tokens=[r['usage']['prompt_tokens'] for r in calls if 'usage' in r]
    output=[r['usage']['completion_tokens'] for r in calls if 'usage' in r]
    price=PROVIDER['pricing_usd_per_million']
    estimate=dict(historical_calls=len(calls),historical_actions=635,historical_cost=charged,
        historical_mean_input=statistics.mean(tokens),historical_mean_output=statistics.mean(output),
        same_action_count_scenario=charged,
        full_2400_calls_historical_mean_cost_scenario=charged/len(calls)*2400,
        full_2400_calls_no_cache_mean_tokens_scenario=(statistics.mean(tokens)*price['cache_miss']+statistics.mean(output)*price['output'])*2400/1e6,
        global_reservation_guard_usd=3,episode_guard_usd=.25,
        caveat='Planning estimates, not guaranteed cost/invoice. New trajectories, cache hits, responses and retries vary. Guards include uncertain request reserves; budget aborts stay in denominator.')
    write(RESULTS/'budget_estimate.json',estimate)
    # All old Python dependencies and every new pre-formal source are hashed.
    # Posthoc report/analysis code, if added later, is separately manifested and
    # cannot be imported by this frozen policy or runner.
    files={p:h for p,h in prior.items() if p.endswith('.py')}
    for p in (ROOT/'scar_stage18').rglob('*.py'):files[str(p.relative_to(ROOT))]=sha(p)
    for name in ('tasks.json','initial_public_histories.jsonl.gz','budget_estimate.json',
                 'preflight_local.json','preflight_server.json','prior_manifest.json'):
        files['results/stage18/'+name]=sha(RESULTS/name)
    freeze=dict(schema_version=1,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        baseline_stage16_commit=STAGE16_COMMIT,stage17_diagnosis_commit=STAGE17_COMMIT,
        engine_commit=ENGINE_COMMIT,files=files,methods=['SCAR18'],
        schedule=[[t['task_id'],'SCAR18'] for t in tasks],worker_processes=6,
        model_config=PROVIDER,stm_size=5,summary_records=48,summary_characters=6000,
        max_steps=100,internal_P3_horizon=100,report_budgets=[60,80,100],
        tasks=[{k:t[k] for k in ('task_id','game_name','target_item','initial_seed','initial_state_hash','initial_public_history_hash','task_definition_hash')} for t in tasks],
        success_rule='native crafted target during this episode >= required amount AND currently possesses required amount',
        termination='success; 100 actual actions; native terminal/death/HP0; audited API/method/environment abort',
        prefix='unchanged Stage17 official target-independent prefix, robot 0 / quarantine 28; excluded from 100 action budget',
        acquisition='immediate known nominal demand minus publicly owned quantity; unknown demand one new ground unit; held-first store transfer preserved; no craft batch redesign',
        consequences='current episode public feedback only; explicit carrying damage distinct from temporal HP association; acquisition/count attribution is conditional; discard/cessation strengthens; quantity/location/equipment scope; changed context bounded trial',
        arbitration='public tri-value conditions and consequence checks; reject proven blocked candidates; support observed-risk removal; known direct goal execution over passive uncertain candidate; otherwise retain S1; only inherited alternatives',
        state_commit='candidate generation on copies; restore counter/trial/probe state unless selected actual probe matches; observations once; FIFO planning retained only for selected structured candidate',
        summary='same base prompt and STM5; goal, blockers, recent conditional risk, disclosed dependency recipes, current state/failures/uncertainty, remaining original facts; hard 48/6000 ceiling; old/new snapshots logged',
        retry_protocol='same Stage17 provider: at most 3 attempts/logical call, saved paid-response cache, exact checkpoint resume, interrupted uncertain request abort without resampling; finalized runs immutable',
        formal_api_before_freeze=0,holdout=False,interpretation='24 development tasks; single temperature .7 sample; no ablations or independent generalization claim')
    write(path,freeze)
    write(RESULTS/'research_state.json',dict(phase='frozen_ready_to_run',formal_started=False,freeze_sha256=sha(path)))
    print('Frozen one SCAR18 variant, 24 unique runs.',estimate)


if __name__=='__main__':main()
