import hashlib,json,os,shutil,subprocess
from pathlib import Path
R=Path('/root/agentodyssey-benchmark-20261018');repo=R/'agentodyssey';py=str(R/'.venv/bin/python')
assert not (R/'mechanism_study_status.json').exists()
protected=[repo/'eval.py']+[p for p in (repo/'agents').glob('*feedback*py') if p.name!='feedback_v4_core.py']+[repo/'agents/long_context_agent.py',repo/'agents/sentry_agent.py',repo/'agents/llm_agent_config.py']
before={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
for n in ['mechanism_study_core.py','mechanism_study_agent.py','feedback_v4_core.py']:shutil.copy2(R/n,repo/'agents'/n)
names=['mechanism_study_core.py','mechanism_study_agent.py','feedback_v4_core.py','study_selection.py','eval_mechanism_study.py','api_proxy_mechanism_study.py','run_mechanism_study.py','analyze_mechanism_study.py','study_adapter_smoke.py','test_mechanism_study.py']
for n in names:compile((R/n).read_text(),str(R/n),'exec')
checks=[]
for script in ['test_feedback_v3.py','test_mechanism_study.py','test_study_selection.py']:
    r=subprocess.run([py,str(R/script)],capture_output=True,text=True);assert r.returncode==0,r.stderr
    checks.append({'suite':script,'stderr':r.stderr,'passed':True})
for variant,disabled in [('full_reference',[]),('no_checks',[]),('no_execution',[]),('no_repeat',[]),('no_hypothesis',[]),('v4_selected',[]),('v4_selected',['joint_checks']),('v4_selected',['dependency_execution']),('v4_selected',['hard_repeat']),('v4_selected',['hypothesis'])]:
    env=os.environ.copy();env.update({'AO_API_BASE_URL':'http://127.0.0.1:1/offline/v1','AO_STUDY_VARIANT':variant,'AO_DISABLED_COMPONENTS':json.dumps(disabled),'PYTHONPATH':str(repo)})
    r=subprocess.run([py,str(R/'study_adapter_smoke.py')],env=env,capture_output=True,text=True);assert r.returncode==0,(variant,disabled,r.stderr[-4000:])
    checks.append({'variant':variant,'disabled':disabled,'passed':True,'stdout':r.stdout[-800:]})
after={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected};assert before==after
receipt={'all_passed':True,'api_calls':0,'real_game_rollouts':0,'protected_files_unchanged':before,'checks':checks}
(R/'mechanism_study_preflight.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
