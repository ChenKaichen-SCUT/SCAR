"""Freeze exactly one version after zero-API acceptance and before any paid run."""
from .common import *
from . import config
import subprocess
import os
from pathlib import Path
from datetime import datetime,timezone


def main():
    if (RESULTS/'freeze.json').exists():raise FileExistsError('Formal protocol already frozen')
    test=load(RESULTS/'preflight_local.json')
    assert test['passed'] and test['api_calls']==0 and test['network_attempts']==0
    assert test['unit_tests']>=23 and test['negative_controls']==264
    assert test['repaired_nonquota_tasks']==7 and test['stalled_shadow_states']==11
    assert test['historical_deterministic_checks']['success_tasks']=={'18':14,'19':12,'20':12}
    assert test['stalled_native_checks']['checks_passed']
    for p,h in test['source_hashes'].items():assert sha(ROOT/p)==h,p
    prior=load(RESULTS/'prior_manifest.json')
    assert prior['base_commit']==config.BASE_COMMIT
    for p,h in prior['files'].items():assert sha(ROOT/p)==h,p
    engine=Path(os.environ['AGENTODYSSEY_ROOT'])
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=engine,text=True).strip()==ENGINE_COMMIT
    assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=engine,text=True).strip()
    assert load(RESULTS/'tasks.json')==load(ROOT/'results/stage17/tasks.json')
    assert sha(RESULTS/'initial_public_histories.jsonl.gz')==sha(ROOT/'results/stage17/initial_public_histories.jsonl.gz')
    assert not (RESULTS/'runs').exists()
    assert not (ROOT/'runtime/stage21/budget.sqlite').exists()
    files={p:h for p,h in prior['files'].items() if p.endswith('.py')}
    files.update({str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'scar_stage21').rglob('*.py')})
    files['scar_stage21/run.sh']=sha(ROOT/'scar_stage21/run.sh')
    for p in RESULTS.iterdir():
        if p.is_file():files[str(p.relative_to(ROOT))]=sha(p)
    data=dict(schema_version=1,created_utc=datetime.now(timezone.utc).isoformat(),base_commit=config.BASE_COMMIT,
        engine_commit=ENGINE_COMMIT,files=files,methods=['SCAR21'],worker_processes=config.WORKERS,
        schedule=[[t['task_id'],'SCAR21'] for t in load(RESULTS/'tasks.json')],model_config=config.PROVIDER,
        max_steps=100,internal_P3_horizon=100,report_budgets=[60,80,100],site='local',holdout=False,
        engineering='typed public evidence, public BFS transit, blocker-scoped attempts, one bounded probe; frozen known FIFO/P1/P3 and acquisition',
        policy='P3 then reliable S1 then known dependency; bounded probe; deterministic ETBR when normal budget/entries unavailable; one optional model probe when multiple normal entries; deterministic fallback; explicit stall',
        normal_exploration_actions=18,extra_credits=6,credits_per_blocker=2,one_probe_per_credit=True,transit_steps_per_credit=3,
        extra_environment_actions_upper_bound=24,evidence_consumption='once globally, stronger than once per blocker',
        probe_total_actions=4,logical_model_calls_per_episode=24,logical_calls_per_decision=1,paid_attempts_per_call=3,
        prompt_characters=8000,prompt_records=24,output_tokens=512,history_in_prompt=False,
        exact_model='deepseek-flash; thinking disabled; temperature .7',
        unsupported_online_evidence=['unparsed NPC dialogue','unparsed task-stage narrative'],
        generic_interface_tests=['production_relation','map_connection','task_condition from public NPC dialogue','task_stage'],
        safety='new credit refused on current public risk; disclosed locked edges need held key; unchanged failed conditions rejected',
        cost_authorization='Current guide21 suggests global $3 and episode $.25; adopted as stricter caps within persistent user experiment authorization.',
        max_protocol_cost_usd=3,episode_cost_usd=.25,
        success_rule='native target produced during task >= target_amount AND currently possessed >= target_amount',
        initialization='unchanged Stage17 target-independent histories: robot 0, quarantine 28 excluded from 100-step task budget',
        model_calls_before_freeze=0,retry='paid responses cached; uncertain billing stops; finalized failures never rerun',
        scope='24 repeatedly analysed development tasks, one sample; no paid ablation or baseline reruns; no independent generalization or causal improvement claim')
    write(RESULTS/'freeze.json',data)
    write(RESULTS/'research_state.json',dict(phase='frozen_ready_to_run',formal_started=False,total_runs=24))
    print('Frozen SCAR21: 24 tasks, 12 workers, $3 global / $.25 per episode, zero prior calls')


if __name__=='__main__':main()
