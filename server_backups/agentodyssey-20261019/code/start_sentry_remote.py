import hashlib
import json
from pathlib import Path
import socket
import subprocess
import time
R=Path('/root/agentodyssey-benchmark-20261018')
assert json.loads((R/'sentry_preflight.json').read_text())['adapter_integration_passed']
assert not (R/'sentry_status.json').exists() and not (R/'runner_sentry.pid').exists()
for g in ['remnant','mark','metropolis']:
    assert not (R/'runs'/(g+'__sentry_v1')).exists()
    assert not (R/'telemetry'/(g+'__sentry_v1')).exists()
with socket.socket() as s:assert s.connect_ex(('127.0.0.1',8090))!=0
proto={'algorithm':'sentry_v1','label':'Official Sentry core + full-history ReAct, DeepSeek/AgentOdyssey adapter',
    'repository':'https://github.com/nuglifeleoji/Sentry','commit':'1d91bca14fa6a4e17908856cc787eb8e8354395f',
    'official_core_modified':False,'games':['remnant','mark','metropolis'],'runs_per_game':1,
    'environment_seed':42,'max_steps':500,'backbone':'deepseek-flash','thinking':'disabled',
    'actor':{'host':'full_history_ReAct','temperature':0.7,'presence_penalty':1.5,'max_tokens':4096},
    'sentry_auxiliary':{'temperature':0.0,'presence_penalty':0.0,'max_tokens':4096,'response_format':'json_object'},
    'official_mechanism':{'trace_window':5,'recovery_horizon':10,'retrieval_top_k':5,'primary_label_cap':2,
        'schema_first':True,'only_verified_soft_recovery_enters_playbook':True,'no_full_playbook_in_actor_prompt':True},
    'game_memory_reset':True,'initial_playbook':'empty','transport_retries_max':2,
    'protocol_differences_from_paper':['DeepSeek instead of Qwen3.5-9B','AgentOdyssey instead of original paper tasks',
        'Host actor max_tokens=4096 to match existing ReAct and improved method; paper actor limit is 384',
        'Independent empty playbook per game; no cross-game training or memory transfer'],
    'adapter':{'task_objective':'Complete main quest revealed by observations; initial text observation included',
        'observed_cycles':'post-environment-step callback, including final cycle',
        'schema':'public declared verbs and arity; free text arguments may contain whitespace',
        'semantic_rejection_is_not_schema_failure':True,
        'environment_acceptance':'invalid-action flag and explicit denial text; not a success/reward oracle',
        'reward_or_hidden_state_exposed':False,'game_specific_rules':False},
    'execution':{'parallel_trajectories':3,'api_concurrency_ceiling':128,'cpu_threads_per_process':2},
    'comparison_policy':{'new_baseline_authorized':'Sentry only','no_old_baseline_reruns':True,
                         'mem0_excluded_from_future_baseline_tables':True},
    'accounting':'All actor, detector, verifier and updater calls logged; no hidden free auxiliary compute.'}
names=['sentry_agent.py','eval_sentry.py','run_sentry.py','api_proxy_sentry.py','test_sentry_integration.py']
proto['adapter_sha256']={name:hashlib.sha256((R/name).read_bytes()).hexdigest() for name in names}
proto['official_files']=json.loads((R/'sentry_source_manifest.json').read_text())['files']
(R/'protocol_sentry_v1.json').write_text(json.dumps(proto,indent=2))
for script,stem in [('api_proxy_sentry.py','proxy_sentry'),('run_sentry.py','runner_sentry')]:
    with (R/(stem+'.log')).open('w') as out:
        proc=subprocess.Popen([str(R/'.venv/bin/python'),'-u',str(R/script)],cwd=R,stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
    (R/(stem+'.pid')).write_text(str(proc.pid));print(json.dumps({'script':script,'pid':proc.pid}))
    if stem=='proxy_sentry':
        for _ in range(50):
            with socket.socket() as s:
                if s.connect_ex(('127.0.0.1',8090))==0:break
            if proc.poll() is not None:raise RuntimeError('Sentry proxy failed before game launch')
            time.sleep(.1)
        else:raise RuntimeError('Sentry proxy not ready')
