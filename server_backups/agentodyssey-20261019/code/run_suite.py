"""Exactly one fresh trajectory per method; no seed search or silent restarts."""
import pathlib,json,subprocess,os,time,concurrent.futures,threading,statistics,sys
ROOT=pathlib.Path(__file__).resolve().parent
PROTO=json.loads((ROOT/'protocol.json').read_text())
LOCK=threading.Lock();STATE={'started_at':time.time(),'game':PROTO['game'],'runs':{}}
def status(method,**changes):
 with LOCK:
  STATE['runs'].setdefault(method,{}).update(changes);STATE['updated_at']=time.time()
  tmp=ROOT/'suite_status.json.tmp';tmp.write_text(json.dumps(STATE,indent=2));tmp.replace(ROOT/'suite_status.json')
def run_method(spec):
 method=spec['id'];status(method,status='waiting_for_dependencies',steps=0)
 deadline=time.monotonic()+3600
 flags=['base_ready.flag']+(['mem0_installed.flag','embedding_ready.flag'] if method=='mem0' else [])
 while not all((ROOT/f).exists() for f in flags):
  if time.monotonic()>deadline:return status(method,status='setup_timeout',missing=[f for f in flags if not (ROOT/f).exists()])
  time.sleep(5)
 import psutil
 run_dir=ROOT/'runs'/method
 if run_dir.exists():raise RuntimeError('Refusing duplicate run or overwrite: '+str(run_dir))
 agent_spec={'agents':[{'agent_type':spec['agent'],'agent_id':'agent_adam_davis','agent_name':'adam_davis','llm_name':PROTO['api_model'],'llm_provider':'openai'}]}
 path=ROOT/(method+'_agents.json');path.write_text(json.dumps(agent_spec,indent=2))
 env=os.environ.copy();env.update({'AO_API_BASE_URL':'http://127.0.0.1:8088/'+method+'/v1','AO_EMBED_PATH':str(ROOT/'models/Qwen3-Embedding-0.6B'),'MEM0_TELEMETRY':'False','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','TOKENIZERS_PARALLELISM':'false','OMP_NUM_THREADS':'4','MKL_NUM_THREADS':'4','PYTHONUNBUFFERED':'1','PYTHONHASHSEED':'42'})
 cmd=[str(ROOT/'.venv/bin/python'),'-u','eval.py','--agents_config',str(path),'--game_name',PROTO['game'],'--max_steps',str(PROTO['max_steps']),'--seed',str(PROTO['environment_seed']),'--run_dir',str(run_dir),'--cumulative_config_save']
 log=(ROOT/(method+'.log')).open('w');started=time.time()
 p=subprocess.Popen(cmd,cwd=ROOT/'agentodyssey',env=env,stdout=log,stderr=subprocess.STDOUT)
 monitor=psutil.Process(p.pid);rss_max=0;cpu_seconds=0
 status(method,status='running',pid=p.pid,command=cmd,started_at=started,run_dir=str(run_dir))
 resource_file=ROOT/(method+'_resources.jsonl')
 while p.poll() is None:
  try:
   rss=monitor.memory_info().rss;ct=monitor.cpu_times();cpu_seconds=ct.user+ct.system;rss_max=max(rss_max,rss)
   with resource_file.open('a') as f:f.write(json.dumps({'time':time.time(),'rss_bytes':rss,'cpu_seconds':cpu_seconds})+'\n')
   step_path=run_dir/'agent_adam_davis/agent_log.jsonl';steps=0;last=None
   if step_path.exists():
    with step_path.open() as f:
     for line in f:
      if line.strip():steps+=1;last=line
   status(method,steps=steps,wall_s=time.time()-started,peak_rss_bytes=rss_max,cpu_seconds=cpu_seconds)
  except (psutil.NoSuchProcess,ProcessLookupError):pass
  time.sleep(5)
 returncode=p.wait();log.close();elapsed=time.time()-started
 result={'status':'finished' if returncode==0 else 'failed','returncode':returncode,'finished_at':time.time(),'wall_s':elapsed,'peak_rss_bytes':rss_max,'cpu_seconds':cpu_seconds}
 if (run_dir/'config.jsonl').exists():
  score=subprocess.run([str(ROOT/'.venv/bin/python'),'challenge_eval.py','--remnant',str(run_dir),'--json'],cwd=ROOT/'agentodyssey',capture_output=True,text=True)
  (ROOT/(method+'_official_score.json')).write_text(score.stdout)
  if score.returncode:result['scoring_error']=score.stderr
  elif score.stdout:result['official_score']=json.loads(score.stdout)
  with (run_dir/'agent_adam_davis/agent_log.jsonl').open() as f:rows=[json.loads(l) for l in f if l.strip()]
  result['steps']=len(rows)
  result['completion_reason']='step_limit' if len(rows)==PROTO['max_steps'] else 'environment_done' if rows and rows[-1].get('episode_done') else 'error_or_early_stop'
 status(method,**result)
def main():
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
  futures={pool.submit(run_method,s):s['id'] for s in PROTO['methods']}
  for f in concurrent.futures.as_completed(futures):
   try:f.result()
   except Exception as e:status(futures[f],status='runner_error',error=repr(e))
 STATE['finished_at']=time.time()
 (ROOT/'suite_status.json').write_text(json.dumps(STATE,indent=2))
 print(json.dumps(STATE),flush=True)
if __name__=='__main__':main()
