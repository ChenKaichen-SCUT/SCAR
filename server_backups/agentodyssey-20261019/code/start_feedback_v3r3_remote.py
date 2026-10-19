"""One authorized Remnant 300-step trial; preserve every previous source and ledger."""
import hashlib,json,socket,subprocess,sys
from pathlib import Path
R=Path('/root/agentodyssey-benchmark-20261018');sys.path.insert(0,str(R))
from budget_guard_v5_full import BudgetGuard
dest=R/'feedback_v3r3_300_protocol.json';db=R/'feedback_v3r3_300_budget.sqlite';rid='remnant__v3r3_300_20261019'
assert not dest.exists() and not db.exists() and not (R/'runs'/rid).exists(),'Already registered; no automatic rerun/reset'
old=json.loads((R/'feedback_v3r2_verified_protocol.json').read_text())
verification=json.loads((R/'feedback_v3r3_launch_verification.json').read_text());preflight=json.loads((R/'feedback_v3r3_preflight.json').read_text())
assert verification['passed'] and preflight['passed'] and verification['provider_calls']==preflight['provider_calls']==0
assert verification['actual_runner_evaluator']=='eval_feedback_v3r3.py' and verification['production_max_steps']==300
assert all(x['agent_module']=='agents.feedback_v3r3_agent' and x['ledger_module']=='agents.feedback_v3r3_core' and x['dispatch_module']=='agents.feedback_v3r3_core' for x in verification['instantiated_policy_checks'])
sources={**old['source_sha256'],**verification['source_sha256'],**preflight['source_sha256']}
for name,expected in sources.items():assert hashlib.sha256((R/name).read_bytes()).hexdigest()==expected,name
for name in ['feedback_v3r3_core.py','feedback_v3r3_agent.py']:assert (R/name).read_bytes()==(R/'agentodyssey/agents'/name).read_bytes()
assert json.loads((R/'feedback_v3r2_verified_status.json').read_text())['all_processes_stopped']
with socket.socket() as sock:assert sock.connect_ex(('127.0.0.1',8094))!=0,'A proxy is already running'
names=['feedback_v3r2_verified_budget.sqlite','feedback_v3r2_verified_protocol.json','feedback_v3r2_verified_status.json','feedback_v3r2_budget.sqlite','feedback_v3r2_validity.json','feedback_v3r_budget.sqlite']
preserved={n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in names}
protocol={**old,'authorization':'User requested completion-predicate repair plus three cooperating mechanisms, one Remnant 300-step validation. No baselines rerun; existing numeric quota ceilings unchanged.',
 'runs':[{'id':rid,'game':'remnant','budget_scope':rid,'cache_sources':[],'cached_calls':0,'max_steps':300}],
 'budget_db':db.name,'source_sha256':sources,'quota_values_unchanged_from':'feedback_v3r2_verified_protocol.json',
 'actual_runner':'run_feedback_v3r3.py','actual_evaluator':'eval_feedback_v3r3.py','expected_agent_module':'agents.feedback_v3r3_agent','expected_dispatch_module':'agents.feedback_v3r3_core',
 'launch_verification_sha256':hashlib.sha256((R/'feedback_v3r3_launch_verification.json').read_bytes()).hexdigest(),
 'previous_artifacts_preserved_sha256':preserved,'comparison':'Frozen verified v3r2 first 300 steps; one stochastic trajectory per method, not an ablation or statistical evidence.',
 'planned_checks':['Explicit completion receipts distinct from task reward','Bounded operation probes with confounded outcomes','Persistent resource-feasible plans and suffix repair','Context-scoped failed strategies and observed step costs'],
 'no_early_stagnation_stop':True}
for k in ['limits','per_run_limits','output_tokens_per_call','max_single_input_reservation']:assert protocol[k]==old[k]
assert len(protocol['runs'])==1 and protocol['workers']==1
BudgetGuard(db,protocol['limits'],protocol['per_run_limits'])
with dest.open('x') as f:json.dump(protocol,f,ensure_ascii=False,indent=2)
for n,h in preserved.items():assert hashlib.sha256((R/n).read_bytes()).hexdigest()==h,n
with (R/'feedback_v3r3_300_supervisor.log').open('x') as out:
    process=subprocess.Popen([str(R/'.venv/bin/python'),'-u',str(R/'run_feedback_v3r3.py')],cwd=R,stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps({'pid':process.pid,'run_id':rid,'game':'remnant','max_steps':300,'runner':protocol['actual_runner'],'evaluator':protocol['actual_evaluator'],'quota_values_unchanged':True,'per_run_limits':protocol['per_run_limits'],'previous_usage_preserved':True}))
