"""Install new files beside frozen agents; only compile, offline tests and dry runs."""
import hashlib,json,os,shutil,socket,subprocess
from pathlib import Path
R=Path('/root/agentodyssey-benchmark-20261018');repo=R/'agentodyssey';py=str(R/'.venv/bin/python')
new_agents=['feedback_v5_core.py','feedback_v5_agent.py','compact_decision_packet.py']
names=new_agents+['api_budget_guard.py','api_proxy_budgeted.py','eval_feedback_v5.py','run_efficient_screen.py','test_feedback_v5.py','test_feedback_v5_agent_smoke.py','preflight_feedback_v5_remote.py']
protected=[repo/'eval.py']+[p for p in (repo/'agents').glob('*.py') if p.name not in new_agents]
before={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
existing_runs=sorted(p.name for p in (R/'runs').iterdir());existing_telemetry=sorted(p.name for p in (R/'telemetry').iterdir())
with socket.socket() as s:assert s.connect_ex(('127.0.0.1',8094))!=0,'Do not preflight while a v5 run is live'
for n in names:compile((R/n).read_text(),str(R/n),'exec')
for n in new_agents:shutil.copy2(R/n,repo/'agents'/n)
checks=[]
env=os.environ.copy();env.update({'AO_API_BASE_URL':'http://127.0.0.1:1/offline/v1','AO_V5_BASE_URL':'http://127.0.0.1:8094/offline/v1','PYTHONPATH':str(repo),'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'})
for script in ['test_feedback_v3.py','test_mechanism_study.py','test_study_selection.py','test_feedback_v5.py','test_feedback_v5_agent_smoke.py']:
    r=subprocess.run([py,str(R/script)],capture_output=True,text=True,env=env,timeout=90)
    assert r.returncode==0,(script,r.stdout[-2500:],r.stderr[-6000:])
    checks.append({'suite':script,'passed':True,'stdout':r.stdout[-1000:],'stderr':r.stderr[-6000:]})
for game in ['remnant','mark','metropolis']:
    r=subprocess.run([py,str(R/'run_efficient_screen.py'),'--game',game],capture_output=True,text=True,env=env,timeout=10)
    assert r.returncode==0,r.stderr;check=json.loads(r.stdout);assert check['mode']=='dry_run_no_provider_calls';checks.append(check)
after={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected};assert before==after
assert existing_runs==sorted(p.name for p in (R/'runs').iterdir());assert existing_telemetry==sorted(p.name for p in (R/'telemetry').iterdir())
with socket.socket() as s:assert s.connect_ex(('127.0.0.1',8094))!=0
receipt={'all_passed':True,'api_calls':0,'new_game_rollouts':0,'no_new_run_or_telemetry_folders':True,'no_v5_proxy_listening':True,'protected_files_unchanged':before,
    'implementation_sha256':{n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in names},'checks':checks}
(R/'feedback_v5_preflight.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
