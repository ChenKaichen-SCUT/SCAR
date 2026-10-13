"""Create the protocol freeze only after complete adapter acceptance."""
import datetime
import random
import subprocess
from .common import ROOT,RESULTS,BASE_COMMIT,ENGINE_COMMIT,METHODS,load,write,sha
from .provider import CONFIG


def main():
    path=RESULTS/'freeze.json'
    if path.exists():raise FileExistsError('Do not rewrite a protocol freeze')
    assert load(RESULTS/'preflight_local.json')['passed']
    assert load(RESULTS/'preflight_server.json')['passed']
    assert load(RESULTS/'pipeline_acceptance.json')['passed']
    assert load(RESULTS/'connectivity.json')['passed']
    assert load(RESULTS/'task_check_server.json')['passed']
    for site in ('local','server'):assert '297 passed' in (RESULTS/f'unit_tests_{site}.txt').read_text()
    previous=load(RESULTS/'prior_manifest.json')['files']
    assert all(sha(ROOT/p)==h for p,h in previous.items())
    tasks=load(RESULTS/'tasks.json');assert len(tasks)==24
    old=load(RESULTS/'prior_task_inventory.json');oldids={r['object_id'] for r in old};oldseeds={r['seed'] for r in old}
    truth=load(RESULTS/'evaluator_truth.json')
    assert all(truth[t['task_id']]['target_id'] not in oldids and t['initial_seed'] not in oldseeds for t in tasks)
    assert len({t['initial_state_hash'] for t in tasks})==24
    schedule=[(t['task_id'],m) for t in tasks for m in METHODS];random.Random(170917).shuffle(schedule)
    files={p:sha(ROOT/p) for p in subprocess.check_output(['git','ls-files','*.py'],cwd=ROOT,text=True).splitlines()}
    for folder in ('scar_stage17','third_party_adapters'):
        for p in (ROOT/folder).rglob('*'):
            if p.is_file() and ('__pycache__' not in p.parts) and p.suffix!='.pyc':files[str(p.relative_to(ROOT))]=sha(p)
    for name in ('tasks.json','evaluator_truth.json','initial_public_histories.jsonl.gz','candidate_selection.json','candidate_sweep.json','sources.json','sources_server.json','budget_estimate.json'):
        files['results/stage17/'+name]=sha(RESULTS/name)
    freeze=dict(schema_version=1,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        prior_scar_commit=BASE_COMMIT,engine_commit=ENGINE_COMMIT,adaplanner_commit='dba187601500e7d91fee5fd786a455aaa7988677',
        methods=list(METHODS),files=files,model_config=CONFIG,tasks=[dict(task_id=t['task_id'],hash=t['task_definition_hash'],initial_state_hash=t['initial_state_hash']) for t in tasks],
        schedule=schedule,schedule_seed=170917,worker_processes=10,max_steps=100,report_budgets=[60,80,100],
        horizon_adaptation=dict(stage16_source_unchanged=True,P3_internal_budget=100,authority='User explicitly: 内部也改为 100 步，作为预算适配'),
        success_rule='Actual crafted count increases by >=1 during the episode AND actual possession >=1. Ground product alone fails.',
        action_interface='Unchanged official game actions; invalid/wait/inspect/craft/move/transfer all cost one environment action.',
        prefix_rule='Same official target-independent tutorial prefix for all methods; robot 0, quarantine 28; 100 evaluation actions after prefix.',
        termination='success, 100 actions, native terminal state, first native death event, or audited method/API/environment abort; all in denominator',
        retries='3 network/format attempts per logical call; no retry of finalized episodes; paid-response replay cache; uncertain interrupted request aborts without resampling',
        long_context='official full history, no truncation/summarization/reflection; window rejection is retained failure',
        reporting='Static closure and method-accessible evidence separate; descriptive paired task analysis and game/family/depth strata; no causal claim',
        exclusion='Any historical target object ID across all audited games; all physical seeds new; no method test performance used',
        formal_api_before_freeze=0)
    write(path,freeze);write(RESULTS/'research_state.json',dict(phase='frozen_ready_to_run',freeze_sha256=sha(path),formal_started=False))
    print('Frozen',len(schedule),'runs; source hashes',len(files))

if __name__=='__main__':main()
