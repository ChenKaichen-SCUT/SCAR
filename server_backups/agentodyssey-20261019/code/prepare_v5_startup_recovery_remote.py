import gzip,hashlib,json,os,shutil,subprocess,tempfile
from pathlib import Path
R=Path('/root/agentodyssey-benchmark-20261018');repo=R/'agentodyssey';py=str(R/'.venv/bin/python')
state=json.loads((R/'v5_three_games_status.json').read_text());assert state['phase']=='stopped' and state['all_processes_stopped']
archive=R/'v5_startup_save_interface_failure';assert not archive.exists();archive.mkdir()
for n in ['feedback_v5_preflight.json','v5_three_games_status.json','v5_three_games_protocol.json','v5_three_games_supervisor.log','v5_startup_failure.json']:
    shutil.copy2(R/n,archive/n)
shutil.copy2(repo/'agents/feedback_v5_agent.py',archive/'feedback_v5_agent_before_fix.py')
expected=(archive/'feedback_v5_agent_before_fix.py').read_text().replace('def save_memory(self,path):','def save_memory(self,full_memory_dir):').replace("super().save_memory(path);(Path(path)/'feedback_v5_state.json')","super().save_memory(full_memory_dir);(Path(full_memory_dir)/'feedback_v5_state.json')")
assert expected==(R/'feedback_v5_agent.py').read_text(),'Recovery must only rename the save interface parameter'
shutil.copy2(R/'feedback_v5_agent.py',repo/'agents/feedback_v5_agent.py')
env=os.environ.copy();env.update({'PYTHONPATH':str(repo),'AO_API_BASE_URL':'http://127.0.0.1:1/offline/v1','AO_V5_BASE_URL':'http://127.0.0.1:8094/offline/v1','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'})
checks=[]
for game in ['remnant','mark','metropolis']:
    with tempfile.TemporaryDirectory(prefix='v5-evaluator-smoke-') as temp:
        env['AO_CONTROL_AUDIT']=str(Path(temp)/'audit.jsonl')
        r=subprocess.run([py,str(R/'eval_v5_offline_adapter_smoke.py'),'--agent','LongContextAgent','--llm_name','deepseek-flash','--llm_provider','openai','--game_name',game,'--max_steps','2','--seed','42','--run_dir',str(Path(temp)/'run'),'--cumulative_config_save'],cwd=repo,env=env,capture_output=True,text=True,timeout=40)
        assert r.returncode==0,(game,r.stderr[-5000:],r.stdout[-2000:]);checks.append({'game':game,'real_evaluator_steps':2,'provider_calls':0,'passed':True})
pre=subprocess.run([py,str(R/'preflight_feedback_v5_remote.py')],capture_output=True,text=True,env=env,timeout=90);assert pre.returncode==0,pre.stderr[-5000:]
transport=subprocess.run([py,str(R/'test_v5_batch_transport.py')],capture_output=True,text=True);assert transport.returncode==0,transport.stderr
original=json.loads((R/'v5_three_games_protocol.json').read_text());reuse={}
for rid,item in state['runs'].items():
    assert item['steps']==0 and item['budget']['calls']==1 and item['returncode']==1
    run=R/'runs'/rid;assert run.resolve().is_relative_to((R/'runs').resolve())
    log=run/'agent_adam_davis/agent_log.jsonl';assert not log.exists() or not log.read_text().strip()
    files=list((R/'telemetry'/rid).glob('*.response.json.gz'));assert len(files)==1;reuse[rid]=files[0].name.split('.')[0]
    destination=archive/rid;assert destination.resolve().is_relative_to(archive.resolve()) and not destination.exists();run.rename(destination)
    audit=R/'control_audit'/(rid+'.jsonl')
    if audit.exists():audit.rename(archive/(rid+'_audit.jsonl'))
    shutil.copy2(R/(rid+'.log'),archive/(rid+'.log'))
receipt=json.loads((R/'feedback_v5_preflight.json').read_text())
original['startup_recovery']={'reason':'keyword save_memory interface mismatch before any environment step','reuse_completed_call':reuse,'budget_reset':False,'new_paid_first_responses':False,'adapter_checks':checks,'original_protocol':'v5_three_games_protocol.json'}
original['v5_implementation_sha256']=receipt['implementation_sha256'];original['batch_source_sha256']={n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in ['api_proxy_v5_batch.py','run_v5_three_games.py','test_v5_batch_transport.py']}
with (R/'v5_three_games_recovery_protocol.json').open('x') as f:json.dump(original,f,indent=2)
with (R/'v5_three_games_resume.log').open('x') as out:p=subprocess.Popen([py,'-u',str(R/'run_v5_three_games.py'),'--execute','--resume-startup-fix'],cwd=R,stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps({'resumed_pid':p.pid,'cached_responses_to_reuse':3,'budget_reset':False,'offline_real_evaluator_checks':checks}))
