import hashlib,json,os,socket,subprocess,sys
from pathlib import Path
sys.path.insert(0,'/root/agentodyssey-benchmark-20261018')
from budget_guard_v5_full import BudgetGuard
R=Path('/root/agentodyssey-benchmark-20261018');dest=R/'feedback_v3r_protocol.json'
assert not dest.exists() and not (R/'feedback_v3r_budget.sqlite').exists(),'Already registered; never overwrite or reset an experiment'
check=json.loads((R/'feedback_v3r_preflight.json').read_text());assert check['all_passed']
for n,h in {**check['source_sha256'],**check['protected_unchanged']}.items():assert hashlib.sha256((R/n).read_bytes()).hexdigest()==h,n
for n in ['feedback_v3r_core.py','feedback_v3r_agent.py']:assert (R/n).read_bytes()==(R/'agentodyssey/agents'/n).read_bytes()
old=json.loads((R/'v5_full500_repair_protocol.json').read_text())
assert json.loads((R/'v5_full500_repair_status.json').read_text())['all_processes_stopped']
with socket.socket() as sock:assert sock.connect_ex(('127.0.0.1',8094))!=0
runs=[{'id':g+'__v3r_20261018','game':g,'budget_scope':g+'__v3r_20261018','cache_sources':[],'cached_calls':0,'max_steps':500} for g in ['remnant','mark','metropolis']]
protocol={'method':'v3r','parent':'v3 (1/24, 17/17, 20/31)','authorization':'User requested abandoning v4/v5, improving v3 on Remnant, and complete normal 500-step experiments without changing quota ceilings.',
 'paid_execution_explicitly_enabled':True,'runs':runs,'seed':42,'model':'deepseek-flash','max_steps_each':500,'workers':3,'thinking_disabled':True,
 'budget_db':'feedback_v3r_budget.sqlite','limits':old['limits'],'per_run_limits':old['per_run_limits'],'max_single_input_reservation':old['max_single_input_reservation'],'output_tokens_per_call':old['output_tokens_per_call'],
 'quota_values_unchanged_from':'v5_full500_repair_protocol.json','new_authorized_experiment_separate_ledger':True,'previous_paid_usage_not_deleted_or_reset':True,
 'no_baseline_reruns':True,'no_v4_or_v5_agent_imports':True,'max_paid_correction_calls':0,'no_stagnation_or_no_admissible_termination':True,
 'local_first_preserves_v3_queued_and_dependency_choices':True,'full_raw_observation_history':True,'audit_not_in_prompt':True,
 'source_sha256':{**check['source_sha256'],**{n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in ['agentodyssey/agents/feedback_v3r_core.py','agentodyssey/agents/feedback_v3r_agent.py','agentodyssey/agents/feedback_v3_core.py','agentodyssey/agents/feedback_v3_agent.py','agentodyssey/agents/feedback_v2_core.py','api_budget_guard.py','budget_guard_v5_full.py']}},
 'preflight_sha256':hashlib.sha256((R/'feedback_v3r_preflight.json').read_bytes()).hexdigest(),
 'interpretation_limit':'Single development trajectory per game. Core changes and cost controls are a combined candidate, not isolated causal evidence for individual components.'}
assert protocol['limits']==old['limits'] and protocol['per_run_limits']==old['per_run_limits']
BudgetGuard(R/protocol['budget_db'],protocol['limits'],protocol['per_run_limits'])
with dest.open('x') as f:json.dump(protocol,f,ensure_ascii=False,indent=2)
with (R/'feedback_v3r_supervisor.log').open('x') as out:p=subprocess.Popen([str(R/'.venv/bin/python'),'-u',str(R/'run_feedback_v3r.py')],cwd=R,stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps({'launched_pid':p.pid,'games':[s['game'] for s in runs],'max_steps_each':500,'quota_values_unchanged':True,'per_game_limits':protocol['per_run_limits'],'batch_limits':protocol['limits'],'algorithm_early_stops_removed':True,'paid_correction_calls':0}))
