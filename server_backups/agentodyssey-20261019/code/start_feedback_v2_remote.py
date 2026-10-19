import hashlib,json,socket,subprocess,time
from pathlib import Path
R=Path('/root/agentodyssey-benchmark-20261018')
assert json.loads((R/'feedback_v2_preflight.json').read_text())['offline_adapter_integration_passed']
assert not (R/'feedback_v2_status.json').exists() and not (R/'runner_feedback_v2.pid').exists()
for game in ['remnant','mark','metropolis']:
    assert not (R/'runs'/(game+'__feedback_v2')).exists()
    assert not (R/'telemetry'/(game+'__feedback_v2')).exists()
with socket.socket() as s:assert s.connect_ex(('127.0.0.1',8091))!=0
names=['feedback_v2_core.py','feedback_v2_agent.py','eval_feedback_v2.py','run_feedback_v2.py','api_proxy_feedback_v2.py','test_feedback_v2.py','analyze_feedback_v2.py']
proto={'algorithm':'feedback_v2','games':['remnant','mark','metropolis'],'runs_per_game':1,'max_steps':500,'environment_seed':42,
 'api_model':'deepseek-flash','thinking':'disabled','actor_temperature':0.7,'actor_presence_penalty':1.5,'actor_max_tokens':4096,
 'controller_temperature':0.,'controller_max_tokens':4096,'controller_presence_penalty':0.,'max_controller_calls_per_game':80,'max_repair_calls_per_game':32,
 'max_successful_llm_calls_per_game':612,'transport_retries_max':2,'parallel_trajectories':3,'api_concurrency_ceiling':128,'cpu_threads_per_process':2,
 'base_method':'full-history ReAct','source_commit':'248430692a9d4a61d38c6c03ab2126287faaf450','baseline_reruns':False,
 'changes':['persistent public-text facts with exact recipe quantities and distinct task parameters','task-linked plans and executable local predicates','conservative hypotheses: confounded failure is indeterminate, no model-certified universal rule','joint action check, at most one model repair, then observational inspection fallback for explicit known contradictions','net possession/task-state recurrence detection','80 reviews released gradually over 500 steps; ledger injected on every action'],
 'data_access':['text observations','declared action schema','own executed actions'],
 'no_access':['reward during decision','hidden environment state','valid-action oracle','old trajectories during runs','preloaded recipes, entities, maps or solutions'],
 'evaluation':['official main/supplementary scores','task parameter preservation and actual task completion','known quantity deficits before attempted tests','indeterminate versus unjustified hypothesis promotion','net-state cycle recurrence after warnings','blocked actions still executed','API tokens and auxiliary call counts'],
 'limits':['single trajectory per game cannot estimate significance','controller output cap increased from v1 2048 to 4096, so compute is not exactly matched','text parsing and relation matching are interface-specific and incomplete','formal local checks do not prove global correctness or causal improvement','observational fallback may spend steps without progressing the task'],
 'implementation_sha256':{n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in names}}
(R/'protocol_feedback_v2.json').write_text(json.dumps(proto,indent=2))
for script,stem in [('api_proxy_feedback_v2.py','proxy_feedback_v2'),('run_feedback_v2.py','runner_feedback_v2')]:
    with (R/(stem+'.log')).open('w') as out:
        proc=subprocess.Popen([str(R/'.venv/bin/python'),'-u',str(R/script)],cwd=R,stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
    (R/(stem+'.pid')).write_text(str(proc.pid));print(json.dumps({'script':script,'pid':proc.pid}))
    if stem=='proxy_feedback_v2':
        for _ in range(50):
            with socket.socket() as s:
                if s.connect_ex(('127.0.0.1',8091))==0:break
            if proc.poll() is not None:raise RuntimeError('Proxy failed; no games started')
            time.sleep(.1)
        else:raise RuntimeError('Proxy not ready')
