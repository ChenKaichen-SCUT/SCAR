"""Register and launch exactly one authorized Remnant trial, no old run changes."""
import hashlib,json,socket,subprocess,sys
from pathlib import Path
R=Path('/root/agentodyssey-benchmark-20261018');sys.path.insert(0,str(R))
from budget_guard_v5_full import BudgetGuard
dest=R/'feedback_v3r7_300_protocol.json';db=R/'feedback_v3r7_300_budget.sqlite';rid='remnant__v3r7_300_20261019'
assert not dest.exists() and not db.exists() and not (R/'runs'/rid).exists(),'Already registered; do not repeat/reset'
old=json.loads((R/'feedback_v3r6_300_protocol.json').read_text());verification=json.loads((R/'feedback_v3r7_launch_verification.json').read_text());preflight=json.loads((R/'feedback_v3r7_preflight.json').read_text())
assert verification['passed'] and preflight['passed'] and verification['provider_calls']==preflight['provider_calls']==0
assert json.loads((R/'feedback_v3r7_public_path_verification.json').read_text())['passed']
assert json.loads((R/'feedback_v3r7_historical_verification.json').read_text())['passed']
assert verification['actual_runner_evaluator']=='eval_feedback_v3r7.py' and verification['production_max_steps']==300
assert all(x['agent_module']=='agents.feedback_v3r7_agent' and x['ledger_module']=='agents.feedback_v3r7_core' and x['dispatch_module']=='agents.feedback_v3r7_core' for x in verification['instantiated_policy_checks'])
sources={**old['source_sha256'],**verification['source_sha256'],**preflight['source_sha256']}
sources['agentodyssey/agents/feedback_v3r5_core.py']=hashlib.sha256((R/'agentodyssey/agents/feedback_v3r5_core.py').read_bytes()).hexdigest()
for name,expected in sources.items():assert hashlib.sha256((R/name).read_bytes()).hexdigest()==expected,name
for name in ['feedback_v3r7_core.py','feedback_v3r7_agent.py']:assert (R/name).read_bytes()==(R/'agentodyssey/agents'/name).read_bytes()
assert json.loads((R/'feedback_v3r6_300_status.json').read_text())['all_processes_stopped']
with socket.socket() as sock:assert sock.connect_ex(('127.0.0.1',8094))!=0,'Proxy already running'
preserved=dict(old['previous_artifacts_preserved_sha256'])
for n in ['feedback_v3r6_300_budget.sqlite','feedback_v3r6_300_protocol.json','feedback_v3r6_300_status.json','runs/remnant__v3r6_300_20261019/agent_adam_davis/agent_log.jsonl','control_audit/remnant__v3r6_300_20261019.jsonl']:
    preserved[n]=hashlib.sha256((R/n).read_bytes()).hexdigest()
protocol={**old,'method':'v3r7','parent':'frozen v3r6',
 'authorization':'User requested implementing controller judgment corrections and verifying performance. One Remnant episode, 300 steps for direct comparison to preceding frozen v3r6; no baseline reruns.',
 'runs':[{'id':rid,'game':'remnant','budget_scope':rid,'cache_sources':[],'cached_calls':0,'max_steps':300}],
 'max_steps_each':300,'workers':1,'budget_db':db.name,'source_sha256':sources,
 'actual_runner':'run_feedback_v3r7.py','actual_evaluator':'eval_feedback_v3r7.py','expected_agent_module':'agents.feedback_v3r7_agent','expected_dispatch_module':'agents.feedback_v3r7_core',
 'launch_verification_sha256':hashlib.sha256((R/'feedback_v3r7_launch_verification.json').read_bytes()).hexdigest(),
 'previous_artifacts_preserved_sha256':preserved,
 'comparison':'Frozen v3r6 300 steps (2/24), same seed and budget settings; single stochastic episode, no causal attribution to individual components.',
 'changes':['Check known constraints independently of unknown visibility; conditionally validate later resource effects without adding predicted facts.', 'Separate suffix conflict from first-action impossibility; bounded repair to the selected craft/transfer target.', 'Use only observed operation schemas and public resources; reject known dangerous repair routes; preserve old emergency and authority rules.'],
 'planned_checks':['Main quest score, gain steps, deaths, environmental denials','Independent capacity checks, preserved successful path, bounded repair attempts and subsequent outcomes','No attack/heal veto solely from parent-task nonprogress','Resource cycle recognition and automatic pauses; fresh actor overrides','Repeated actions after advisory override and next actual feedback','API counts, truncations, total/uncached input and output tokens','Source and old budget hashes unchanged'],
 'no_early_stagnation_stop':True}
for k in ['limits','per_run_limits','output_tokens_per_call','max_single_input_reservation']:assert protocol[k]==old[k]
for n,h in preserved.items():assert hashlib.sha256((R/n).read_bytes()).hexdigest()==h,n
BudgetGuard(db,protocol['limits'],protocol['per_run_limits'])
with dest.open('x') as f:json.dump(protocol,f,ensure_ascii=False,indent=2)
with (R/'feedback_v3r7_300_supervisor.log').open('x') as out:
    p=subprocess.Popen([str(R/'.venv/bin/python'),'-u',str(R/'run_feedback_v3r7.py')],cwd=R,stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps({'pid':p.pid,'run_id':rid,'max_steps':300,'numeric_quota_unchanged':True,'no_baseline_rerun':True}))
