"""Six independent trajectories: one per method in each remaining game."""
import pathlib,json,subprocess,os,time,concurrent.futures,threading,signal
import psutil
ROOT=pathlib.Path(__file__).resolve().parent
PROTO=json.loads((ROOT/'protocol_remaining.json').read_text())
LOCK=threading.Lock()
STATE={'games':PROTO['games'],'api_concurrency_limit':128,'independent_trajectory_concurrency':6,'runs':{}}

def status(run_id,**changes):
 with LOCK:
  STATE['runs'].setdefault(run_id,{}).update(changes)
  tmp=ROOT/'remaining_status.json.tmp';tmp.write_text(json.dumps(STATE,indent=2));tmp.replace(ROOT/'remaining_status.json')

def run_one(game,spec):
 method=spec['id'];run_id=game+'__'+method;run_dir=ROOT/'runs'/run_id
 if run_dir.exists():raise RuntimeError('Refusing duplicate trajectory: '+str(run_dir))
 agent_spec={'agents':[{'agent_type':spec['agent'],'agent_id':'agent_adam_davis','agent_name':'adam_davis','llm_name':PROTO['api_model'],'llm_provider':'openai'}]}
 path=ROOT/(run_id+'_agents.json');path.write_text(json.dumps(agent_spec,indent=2))
 threads='4' if method=='mem0' else '1'
 env=os.environ.copy();env.update({'AO_API_BASE_URL':'http://127.0.0.1:8088/'+run_id+'/v1','AO_EMBED_PATH':str(ROOT/'models/Qwen3-Embedding-0.6B'),'MEM0_TELEMETRY':'False','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','TOKENIZERS_PARALLELISM':'false','OMP_NUM_THREADS':threads,'MKL_NUM_THREADS':threads,'OPENBLAS_NUM_THREADS':threads,'OMP_WAIT_POLICY':'PASSIVE','PYTHONUNBUFFERED':'1','PYTHONHASHSEED':'42'})
 cmd=[str(ROOT/'.venv/bin/python'),'-u','eval.py','--agents_config',str(path),'--game_name',game,'--max_steps',str(PROTO['max_steps']),'--seed',str(PROTO['environment_seed']),'--run_dir',str(run_dir),'--cumulative_config_save']
 log=(ROOT/(run_id+'.log')).open('w')
 p=subprocess.Popen(cmd,cwd=ROOT/'agentodyssey',env=env,stdout=log,stderr=subprocess.STDOUT)
 monitor=psutil.Process(p.pid);rss_max=0
 status(run_id,status='running',game=game,method=method,pid=p.pid,command=cmd,steps=0,compute_threads=int(threads),run_dir=str(run_dir))
 while p.poll() is None:
  try:
   rss=monitor.memory_info().rss;rss_max=max(rss_max,rss)
   path_log=run_dir/'agent_adam_davis/agent_log.jsonl';rows=[]
   if path_log.exists():
    for line in path_log.read_text().splitlines():
     try:rows.append(json.loads(line))
     except json.JSONDecodeError:pass
   status(run_id,steps=len(rows),main_quest=sum(r['reward'].get('quest',0) for r in rows),peak_rss_bytes=rss_max,last_action=rows[-1]['action'] if rows else None)
  except (psutil.NoSuchProcess,ProcessLookupError):pass
  time.sleep(5)
 returncode=p.wait();log.close()
 result={'status':'finished' if returncode==0 else 'failed','returncode':returncode,'peak_rss_bytes':rss_max}
 if (run_dir/'config.jsonl').exists():
  score=subprocess.run([str(ROOT/'.venv/bin/python'),'challenge_eval.py','--'+game,str(run_dir),'--json'],cwd=ROOT/'agentodyssey',capture_output=True,text=True)
  (ROOT/(run_id+'_official_score.json')).write_text(score.stdout)
  if score.returncode:result['scoring_error']=score.stderr
  elif score.stdout:result['official_score']=json.loads(score.stdout)
  rows=[json.loads(l) for l in (run_dir/'agent_adam_davis/agent_log.jsonl').read_text().splitlines() if l.strip()]
  result['steps']=len(rows);result['main_quest']=sum(r['reward'].get('quest',0) for r in rows)
  result['completion_reason']='step_limit' if len(rows)==PROTO['max_steps'] else 'environment_done' if rows and rows[-1].get('episode_done') else 'error_or_early_stop'
 status(run_id,**result)

def main():
 assert not (ROOT/'remaining_status.json').exists(),'Do not restart the suite or duplicate episodes.'
 for game in PROTO['games']:
  assert (ROOT/'agentodyssey/assets/env_configs/generated'/game/'initial.json').exists()
  for spec in PROTO['methods']:
   assert not (ROOT/'runs'/(game+'__'+spec['id'])).exists()
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
  futures={pool.submit(run_one,g,s):g+'__'+s['id'] for g in PROTO['games'] for s in PROTO['methods']}
  for f in concurrent.futures.as_completed(futures):
   try:f.result()
   except Exception as e:status(futures[f],status='runner_error',error=repr(e))
 if all(s['status']=='finished' for s in STATE['runs'].values()) and len(STATE['runs'])==6:
  for spec in PROTO['methods']:
   m=spec['id'];cmd=[str(ROOT/'.venv/bin/python'),'challenge_eval.py','--remnant',str(ROOT/'runs'/m),'--mark',str(ROOT/'runs'/('mark__'+m)),'--metropolis',str(ROOT/'runs'/('metropolis__'+m)),'--json']
   score=subprocess.run(cmd,cwd=ROOT/'agentodyssey',capture_output=True,text=True)
   (ROOT/(m+'_three_games_official_score.json')).write_text(score.stdout)
   if score.returncode:STATE.setdefault('aggregate_errors',{})[m]=score.stderr
  STATE['completed']=True
 (ROOT/'remaining_status.json').write_text(json.dumps(STATE,indent=2))
 proxy=int((ROOT/'proxy_remaining.pid').read_text());proc=pathlib.Path('/proc')/str(proxy)
 if proc.exists() and b'api_proxy_remaining.py' in (proc/'cmdline').read_bytes():os.kill(proxy,signal.SIGTERM)
 print(json.dumps(STATE),flush=True)
if __name__=='__main__':main()
