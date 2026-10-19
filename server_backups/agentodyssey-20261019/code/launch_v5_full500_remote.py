import hashlib,json,os,sqlite3,subprocess,tempfile
from pathlib import Path
R=Path('/root/agentodyssey-benchmark-20261018');repo=R/'agentodyssey';py=str(R/'.venv/bin/python');protocol_path=R/'v5_full500_protocol.json'
assert not protocol_path.exists() and not (R/'v5_full500_budget.sqlite').exists(),'Already registered: never repeat or reset usage'
source=json.loads((R/'v5_three_games_status.json').read_text());assert source['phase']=='stopped' and source['all_processes_stopped']
receipt=json.loads((R/'feedback_v5_preflight.json').read_text());assert receipt['all_passed']
frozen={**receipt['implementation_sha256'],**receipt['protected_files_unchanged']}
for n in ['feedback_v5_agent.py','feedback_v5_core.py','compact_decision_packet.py']:
    frozen['agentodyssey/agents/'+n]=receipt['implementation_sha256'][n]
for n,h in frozen.items():assert hashlib.sha256((R/n).read_bytes()).hexdigest()==h,n
files=['budget_guard_v5_full.py','api_proxy_v5_full.py','eval_v5_continue.py','eval_v5_prefix_offline.py','run_v5_full500.py','test_v5_full_budget.py','launch_v5_full500_remote.py']
for n in files:compile((R/n).read_text(),str(R/n),'exec')
check=subprocess.run([py,str(R/'test_v5_full_budget.py')],capture_output=True,text=True);assert check.returncode==0,check.stderr
checks=[];runs=[]
for rid,item in source['runs'].items():
    assert item['stop_reason']=='run_calls_budget_exceeded';g=item['game']
    with tempfile.TemporaryDirectory(prefix='v5-full-prefix-') as temp:
        temp=Path(temp);env=os.environ.copy();env.update({'PYTHONPATH':str(repo),'PYTHONHASHSEED':'42','AO_API_BASE_URL':'http://127.0.0.1:1/offline/v1','AO_V5_BASE_URL':'http://127.0.0.1:8094/offline/v1',
            'AO_PREFIX_TELEMETRY':str(R/'telemetry'/rid),'AO_REPLAY_AGENT_LOG':str(R/'runs'/rid/'agent_adam_davis/agent_log.jsonl'),'AO_REPLAY_RECEIPT':str(temp/'receipt.json'),'AO_CONTROL_AUDIT':str(temp/'audit.jsonl'),'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'})
        command=[py,str(R/'eval_v5_prefix_offline.py'),'--agents_config',str(R/(rid+'_agents.json')),'--game_name',g,'--max_steps',str(item['steps']),'--seed','42','--run_dir',str(temp/'run'),'--cumulative_config_save']
        r=subprocess.run(command,cwd=repo,env=env,capture_output=True,text=True,timeout=90);assert r.returncode==0,(g,r.stderr[-5000:],r.stdout[-1500:])
        checks.append({'game':g,**json.loads((temp/'receipt.json').read_text()),'cached_completions_verified':item['budget']['calls']})
    runs.append({'id':g+'__v5_full500_20261018','game':g,'source_run':rid,'budget_scope':rid,'prefix_steps':item['steps'],'cached_calls':item['budget']['calls'],'max_steps':500})
per=dict(calls=502,input_tokens=50_000_000,uncached_input_tokens=4_000_000,output_tokens=502*768);limits={k:v*3 for k,v in per.items()}
src=sqlite3.connect(R/'v5_three_games_budget.sqlite');dest=sqlite3.connect(R/'v5_full500_budget.sqlite')
try:
    src.backup(dest);prior=dest.execute('SELECT value FROM config WHERE id=1').fetchone()[0]
    assert dest.execute("SELECT COUNT(*) FROM requests WHERE state!='completed'").fetchone()[0]==0
    assert dest.execute('SELECT COUNT(*) FROM requests').fetchone()[0]==78
    assert not dest.execute('SELECT * FROM halt').fetchall()
    dest.execute('CREATE TABLE amendment (id INTEGER PRIMARY KEY, old_config TEXT, new_config TEXT, reason TEXT)')
    new=json.dumps([limits,per],sort_keys=True);reason='User explicitly requested 500 steps per game after rejecting 30-step screening. Keep all 78 prior paid requests; no replay billing.'
    dest.execute('INSERT INTO amendment VALUES(1,?,?,?)',(prior,new,reason));dest.execute('UPDATE config SET value=? WHERE id=1',(new,));dest.commit()
finally:src.close();dest.close()
protocol={'paid_execution_explicitly_enabled':True,'authorization':'User: 执行30步怎么够？执行500步','runs':runs,'seed':42,'model':'deepseek-flash','max_steps_each':500,'workers':3,
    'limits':limits,'per_run_limits':per,'budget_db':'v5_full500_budget.sqlite','prior_paid_usage_carried_forward':source['batch_budget'],
    'max_single_input_reservation':1_000_000,'output_tokens_per_call':768,'full_history_retained':True,'policy_stagnation_and_no_admissible_stop_unchanged':True,
    'no_baseline_reruns':True,'prefix_reconstruction_checks':checks,'frozen_policy_sha256':frozen,'continuation_source_sha256':{n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in files}}
with protocol_path.open('x') as f:json.dump(protocol,f,indent=2)
with (R/'v5_full500_supervisor.log').open('x') as out:p=subprocess.Popen([py,'-u',str(R/'run_v5_full500.py')],cwd=R,stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps({'launched_pid':p.pid,'max_steps_each':500,'prefix_reconstruction_checks':checks,'prior_paid_usage_preserved':source['batch_budget'],'limits':limits,'policy_unchanged':True}))
