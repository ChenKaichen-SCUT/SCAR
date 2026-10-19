import hashlib,json,os,sqlite3,subprocess,tempfile
from pathlib import Path
R=Path('/root/agentodyssey-benchmark-20261018');repo=R/'agentodyssey';py=str(R/'.venv/bin/python')
protocol_path=R/'v5_full500_repair_protocol.json'
assert not protocol_path.exists(),'Never repeat a registered continuation'
old=json.loads((R/'v5_full500_protocol.json').read_text());state=json.loads((R/'v5_full500_status.json').read_text())
assert state['phase']=='stopped' and state['all_processes_stopped']
for n,h in old['frozen_policy_sha256'].items():assert hashlib.sha256((R/n).read_bytes()).hexdigest()==h,n
files=['api_proxy_v5_full_repair.py','run_v5_full500_repair.py','eval_v5_repair_continue.py','eval_v5_repair_offline.py','v5_full500_runtime.py','test_v5_full500_runtime.py','launch_v5_full500_repair_remote.py']
for n in files:compile((R/n).read_text(),str(R/n),'exec')
env=os.environ.copy();env['PYTHONPATH']=str(repo)
test=subprocess.run([py,str(R/'test_v5_full500_runtime.py')],env=env,capture_output=True,text=True);assert test.returncode==0,test.stderr
runs=[];checks=[]
for rid,item in state['runs'].items():
    g=item['game'];sources=[item['source_run'],rid]
    count=sum(sum(json.loads(x)['event']=='completed' for x in (R/'telemetry'/s/'api_calls.jsonl').read_text().splitlines()) for s in sources)
    extra=1 if item['stop_reason']=='execution_error' else 0
    with tempfile.TemporaryDirectory(prefix='v5-repair-prefix-') as temp:
        temp=Path(temp);env=os.environ.copy();env.update({'PYTHONPATH':str(repo),'PYTHONHASHSEED':'42','AO_API_BASE_URL':'http://127.0.0.1:1/offline/v1','AO_V5_BASE_URL':'http://127.0.0.1:8094/offline/v1',
          'AO_PREFIX_SOURCES':json.dumps(sources),'AO_REPLAY_AGENT_LOG':str(R/'runs'/rid/'agent_adam_davis/agent_log.jsonl'),'AO_REPLAY_RECEIPT':str(temp/'receipt.json'),'AO_CONTROL_AUDIT':str(temp/'audit.jsonl'),'AO_RUNTIME_AUDIT':str(temp/'runtime.jsonl'),'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'})
        result=subprocess.run([py,str(R/'eval_v5_repair_offline.py'),'--agents_config',str(R/(rid+'_agents.json')),'--game_name',g,'--max_steps',str(item['steps']+extra),'--seed','42','--run_dir',str(temp/'run'),'--cumulative_config_save'],env=env,cwd=repo,capture_output=True,text=True,timeout=90)
        assert result.returncode==0,(g,result.stderr[-7000:],result.stdout[-1500:])
        checks.append({'game':g,**json.loads((temp/'receipt.json').read_text()),'paid_responses_reused':count,'pending_response_executed_offline':bool(extra)})
    runs.append({'id':g+'__v5_full500_repaired_20261018','game':g,'source_run':rid,'cache_sources':sources,'budget_scope':item['budget_scope'],'prefix_steps':item['steps'],'cached_calls':count,'max_steps':500})
conn=sqlite3.connect(R/old['budget_db']);assert not conn.execute('SELECT * FROM halt').fetchall();assert conn.execute("SELECT COUNT(*) FROM requests WHERE state!='completed'").fetchone()[0]==0;conn.close()
protocol={**old,'runs':runs,'prior_paid_usage_carried_forward':state['total_lifetime_budget'],'prefix_reconstruction_checks':checks,
  'policy_stagnation_and_no_admissible_stop_unchanged':False,'runtime_repairs':{'malformed_hypothesis_arrays':'reject without semantic coercion; retain actual action','screen_stagnation_stop':'record only for requested 500-step evaluation; recovery and action checks unchanged','no_admissible_action_stop':'unchanged'},
  'budget_database_reused_without_reset':True,'continuation_source_sha256':{n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in files}}
with protocol_path.open('x') as f:json.dump(protocol,f,indent=2)
with (R/'v5_full500_repair_supervisor.log').open('x') as out:p=subprocess.Popen([py,'-u',str(R/'run_v5_full500_repair.py')],cwd=R,stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps({'launched_pid':p.pid,'checks':checks,'same_budget_db':old['budget_db'],'prior_paid_usage':state['total_lifetime_budget'],'repairs':protocol['runtime_repairs']}))
