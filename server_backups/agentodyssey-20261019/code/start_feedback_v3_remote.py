"""Freeze reviewed v3, then launch exactly one trajectory per game."""
import hashlib,json,socket,subprocess,time,urllib.request
from pathlib import Path
R=Path('/root/agentodyssey-benchmark-20261018')
pre=json.loads((R/'feedback_v3_preflight.json').read_text())
assert pre['offline_adapter_integration_passed'] and pre['required_frozen_trace_tests_included']
assert not (R/'feedback_v3_status.json').exists() and not (R/'runner_feedback_v3.pid').exists()
for game in ['remnant','mark','metropolis']:
    for path in [R/'runs'/(game+'__feedback_v3'),R/'telemetry'/(game+'__feedback_v3'),R/'control_audit'/(game+'__feedback_v3.jsonl')]:assert not path.exists()
for relative,digest in pre['protected_files_unchanged'].items():assert hashlib.sha256((R/relative).read_bytes()).hexdigest()==digest
for n in ['feedback_v3_core.py','feedback_v3_agent.py']:assert (R/n).read_bytes()==(R/'agentodyssey/agents'/n).read_bytes()
with socket.socket() as s:assert s.connect_ex(('127.0.0.1',8092))!=0
key=(R/'.deepseek-key').read_text().strip()
with urllib.request.urlopen(urllib.request.Request('https://api.deepseek.com/user/balance',headers={'Authorization':'Bearer '+key}),timeout=30) as response:balance=json.load(response)
assert balance.get('is_available'), 'No spendable provider balance; do not start a doomed run'
(R/'feedback_v3_balance_at_start.json').write_text(json.dumps(balance,indent=2))
names=['feedback_v3_core.py','feedback_v3_agent.py','eval_feedback_v3.py','run_feedback_v3.py','api_proxy_feedback_v3.py','test_feedback_v3.py','analyze_feedback_v3.py','feedback_v2_core.py','api_proxy.py','deepseek_adapter.py','v3_validation_cases.json','preflight_feedback_v3_remote.py','start_feedback_v3_remote.py']
proto={'algorithm':'feedback_v3','games':['remnant','mark','metropolis'],'runs_per_game':1,'max_steps':500,'environment_seed':42,
 'api_model':'deepseek-flash','thinking':'disabled','actor_temperature':0.7,'actor_presence_penalty':1.5,'actor_max_tokens':4096,
 'controller_temperature':0.,'controller_max_tokens':4096,'controller_presence_penalty':0.,'max_controller_calls_per_game':60,'max_repair_calls_per_game':32,
 'max_successful_llm_calls_per_game':592,'transport_retries_max':2,'parallel_trajectories':3,'api_concurrency_ceiling':128,'cpu_threads_per_process':2,
 'base_method':'full-history ReAct; raw observations retained, dispatcher interventions also retained',
 'source_commit':'248430692a9d4a61d38c6c03ab2126287faaf450','baseline_reruns':False,
 'changes':['persistent terminal action and observation-derived recipe/access preparation','receding short action paths rechecked after each observation','transitive demand rejects surplus ingredient crafting','explicit test id, required preconditions and predicted postconditions; no action-string matching or acceptance-as-proof','same-state action and unchanged-inspection veto applies to every dispatch source','veto causes and proposed/executed distinction retained in full history','ingredient listing correctly typed; object location freshness and visibility tracked','no arbitrary inspection fallback; explicit algorithm-stalled early stop if a correction yields no admissible candidate'],
 'data_access':['public text observations','declared action schema','own proposals and executed actions'],
 'no_access_during_decisions':['reward','hidden environment state','valid-action oracle','historical baseline or v2 trajectories','game-specific preloaded recipes, named objects, maps or answers'],
 'validation':{'offline_behavior_tests':23,'server_fake_model_integration_cases':2,'real_api_calls_in_tests':0,'frozen_trace_cases':'two prior v2 public-observation prefixes used only by test_feedback_v3.py','synthetic_name_recipe_variants':3},
 'evaluation':['official main and supplementary score','dependency preparations and actual product/equipment/write effects','test preconditions and predicted versus observed effects','repeated-state and inspection vetoes including dispatcher-caused loops','API tokens, repair/controller call counts, transport failures','all early exits recorded as incomplete trajectories, never reclassified as success'],
 'limits':['same games used for development and evaluation; not held-out generalization evidence','one trajectory per method/game; no statistical significance or guarantee of higher score','observed quantities/access models remain partial and can be invalidated by changing world rules','zero admissible candidate after one correction is an explicit method failure; no automatic outcome-selected rerun','controller cap reduced from v2 80 to 60; prompt/schema and planning differ, compute is not matched'],
 'implementation_sha256':{n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in names}}
(R/'protocol_feedback_v3.json').write_text(json.dumps(proto,indent=2))
for script,stem in [('api_proxy_feedback_v3.py','proxy_feedback_v3'),('run_feedback_v3.py','runner_feedback_v3')]:
    with (R/(stem+'.log')).open('w') as out:proc=subprocess.Popen([str(R/'.venv/bin/python'),'-u',str(R/script)],cwd=R,stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
    (R/(stem+'.pid')).write_text(str(proc.pid));print(json.dumps({'script':script,'pid':proc.pid}),flush=True)
    if stem=='proxy_feedback_v3':
        for _ in range(50):
            with socket.socket() as s:
                if s.connect_ex(('127.0.0.1',8092))==0:break
            if proc.poll() is not None:raise RuntimeError('Proxy failed; no games started')
            time.sleep(.1)
        else:raise RuntimeError('Proxy not ready')
