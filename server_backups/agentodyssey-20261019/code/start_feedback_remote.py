import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import time
R=Path('/root/agentodyssey-benchmark-20261018')
assert json.loads((R/'feedback_preflight.json').read_text())['offline_integration_passed']
assert not (R/'feedback_status.json').exists() and not (R/'runner_feedback.pid').exists()
for game in ['remnant','mark','metropolis']:
    assert not (R/'runs'/(game+'__feedback_v1')).exists()
    assert not (R/'telemetry'/(game+'__feedback_v1')).exists()
with socket.socket() as s:assert s.connect_ex(('127.0.0.1',8089))!=0
proto={'algorithm':'feedback_v1','description':'Full-history ReAct plus observation-grounded, event-triggered feedback control; inspired adaptation, not Sentry reproduction.',
    'games':['remnant','mark','metropolis'],'runs_per_game':1,'max_steps':500,'environment_seed':42,
    'api_model':'deepseek-flash','thinking':'disabled','actor_temperature':0.7,
    'actor_presence_penalty':1.5,'actor_max_tokens':4096,'controller_temperature':0.0,
    'controller_presence_penalty':0.0,'controller_max_tokens':2048,
    'max_controller_calls_per_game':80,'max_repair_calls_per_game':32,
    'max_successful_llm_calls_per_game':612,'transport_retries_max':2,
    'source_commit':'248430692a9d4a61d38c6c03ab2126287faaf450',
    'base_method':'long_context','baseline_reruns':False,'game_specific_rules':False,
    'controller_access':['declared action schema','current and past text observations','past executed actions and reasoning'],
    'no_access':['environment reward','hidden world state','valid-action oracle','baseline trajectories','future observations'],
    'review_trigger':{'denial_prefixes':['Cannot',"Can\'t",'Invalid','Failed','Not enough'],
        'identical_action_feedback_threshold':3,'window_transitions':8,'minimum_review_interval':3,
        'periodic_check_interval':12,'effect_check_horizon_min':2,'effect_check_horizon_max':12},
    'retrieval':{'method':'lexical word overlap, recent tie break','max_rules_to_controller':12,'max_rules_to_actor':5},
    'repair':{'max_per_step':1,'triggers':['declared schema mismatch','two recent identical denied actions under identical visible state projection'],
        'same_state_window':4,'time_and_hidden_state_change':'retry remains allowed; warning does not permanently ban an action'},
    'evidence_validation':'Exact observation quotes and source step IDs; does not verify semantic entailment.',
    'state_reset':'All learned control state and history start empty in each game.',
    'execution':{'parallel_trajectories':3,'api_concurrency_ceiling':128,'cpu_threads_per_process':2},
    'comparison':{'frozen_full_history_main':[2,17,10],'frozen_main_mean':29/3,
        'paired_seed_only_not_paired_randomness':True,'extra_compute_is_reported_not_matched':True},
    'references':['https://arxiv.org/abs/2610.02994','https://arxiv.org/abs/2402.12275','https://arxiv.org/abs/2402.15809']}
names=['feedback_control_core.py','feedback_control_agent.py','eval_feedback.py','run_feedback.py','api_proxy_feedback.py','test_feedback_control.py']
proto['implementation_sha256']={name:hashlib.sha256((R/name).read_bytes()).hexdigest() for name in names}
(R/'protocol_feedback_v1.json').write_text(json.dumps(proto,indent=2))
for script,stem in [('api_proxy_feedback.py','proxy_feedback'),('run_feedback.py','runner_feedback')]:
    with (R/(stem+'.log')).open('w') as out:
        proc=subprocess.Popen([str(R/'.venv/bin/python'),'-u',str(R/script)],cwd=R,stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
    (R/(stem+'.pid')).write_text(str(proc.pid))
    print(json.dumps({'script':script,'pid':proc.pid}))
    if stem=='proxy_feedback':
        for _ in range(50):
            with socket.socket() as s:
                if s.connect_ex(('127.0.0.1',8089))==0:break
            if proc.poll() is not None:raise RuntimeError('Proxy failed; no games started')
            time.sleep(.1)
        else:raise RuntimeError('Proxy not ready')
