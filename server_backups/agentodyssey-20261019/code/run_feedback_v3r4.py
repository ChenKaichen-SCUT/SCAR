"""One new v3-derived trajectory per game; no baseline runs and no early stop heuristic."""
import concurrent.futures,hashlib,json,os,socket,subprocess,threading,time
from pathlib import Path
from budget_guard_v5_full import BudgetGuard
R=Path(__file__).resolve().parent;P=json.loads((R/'feedback_v3r4_300_protocol.json').read_text());S=R/'feedback_v3r4_300_status.json';LOCK=threading.Lock()
STATE={'method':'v3r4','phase':'prepared','all_processes_stopped':False,'runs':{s['id']:{**s,'status':'queued'} for s in P['runs']}}
def rows(p):
    out=[]
    if p.exists():
        for line in p.read_text().splitlines():
            try:out.append(json.loads(line))
            except json.JSONDecodeError:pass
    return out
def save():
    tmp=S.with_suffix('.tmp');tmp.write_text(json.dumps(STATE,indent=2));tmp.replace(S)
def update(rid,**data):
    with LOCK:STATE['runs'][rid].update(data);save()
def run_one(spec):
    rid=spec['id'];g=spec['game'];folder=R/'runs'/rid;assert not folder.exists()
    cfg=R/(rid+'_agents.json');cfg.write_text(json.dumps({'agents':[{'agent_type':'LongContextAgent','agent_id':'agent_adam_davis','agent_name':'adam_davis','llm_name':'deepseek-flash','llm_provider':'openai'}]}))
    env=os.environ.copy();env.update({'AO_API_BASE_URL':'http://127.0.0.1:8094/'+rid+'/v1','AO_CONTROL_AUDIT':str(R/'control_audit'/(rid+'.jsonl')),'AO_CALL_LIMIT':str(P['per_run_limits']['calls']),
       'AO_MAX_STEPS':'300','PYTHONPATH':str(R/'agentodyssey'),'PYTHONHASHSEED':'42','PYTHONUNBUFFERED':'1','OMP_NUM_THREADS':'8','MKL_NUM_THREADS':'8','OPENBLAS_NUM_THREADS':'8','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'})
    cmd=[str(R/'.venv/bin/python'),'-u',str(R/'eval_feedback_v3r4.py'),'--agents_config',str(cfg),'--game_name',g,'--max_steps','300','--seed','42','--run_dir',str(folder),'--cumulative_config_save']
    with (R/(rid+'.log')).open('x') as out:
        p=subprocess.Popen(cmd,cwd=R/'agentodyssey',env=env,stdout=out,stderr=subprocess.STDOUT);update(rid,status='running',pid=p.pid);code=p.wait()
    log=rows(folder/'agent_adam_davis/agent_log.jsonl');tail=(R/(rid+'.log')).read_text(errors='replace')[-5000:];api=rows(R/'telemetry'/rid/'api_calls.jsonl')
    reason='environment_done' if log and log[-1].get('episode_done') else '300_step_limit' if len(log)==300 else 'execution_error'
    stops=[e['reason'] for e in api if e.get('event')=='budget_or_safety_stop']
    if stops:reason=stops[-1]
    info={'status':'finished','returncode':code,'stop_reason':reason,'steps':len(log),'main_quest':sum(r['reward'].get('quest',0) for r in log),
          'budget':BudgetGuard(R/P['budget_db'],P['limits'],P['per_run_limits']).usage(rid)}
    if code:info['error_tail']=tail[-2200:]
    if (folder/'config.jsonl').exists():
        result=subprocess.run([str(R/'.venv/bin/python'),'challenge_eval.py','--'+g,str(folder),'--json'],cwd=R/'agentodyssey',capture_output=True,text=True,timeout=60)
        (R/(rid+'_official_score.json')).write_text(result.stdout)
        if result.returncode==0:info['official_score']=json.loads(result.stdout)
        else:info['scoring_error']=result.stderr[-1500:]
    update(rid,**info)
def main():
    assert not S.exists(),'Never repeat a registered experiment'
    for n,h in P['source_sha256'].items():assert hashlib.sha256((R/n).read_bytes()).hexdigest()==h,n
    proxy=None;save()
    try:
        with socket.socket() as sock:assert sock.connect_ex(('127.0.0.1',8094))!=0
        with (R/'feedback_v3r4_300_proxy.log').open('x') as out:proxy=subprocess.Popen([str(R/'.venv/bin/python'),'-u',str(R/'api_proxy_v3r.py'),'--protocol',str(R/'feedback_v3r4_300_protocol.json')],cwd=R,stdout=out,stderr=subprocess.STDOUT)
        for _ in range(100):
            with socket.socket() as sock:
                if sock.connect_ex(('127.0.0.1',8094))==0:break
            assert proxy.poll() is None;time.sleep(.1)
        else:raise RuntimeError('Proxy unavailable')
        STATE['phase']='running';STATE['proxy_pid']=proxy.pid;save()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            futures={pool.submit(run_one,s):s['id'] for s in P['runs']}
            for f in concurrent.futures.as_completed(futures):
                try:f.result()
                except Exception as e:update(futures[f],status='runner_error',error=repr(e))
    finally:
        if proxy and proxy.poll() is None:
            proxy.terminate()
            try:proxy.wait(timeout=10)
            except subprocess.TimeoutExpired:proxy.kill();proxy.wait()
        STATE['phase']='stopped';STATE['all_processes_stopped']=True
        STATE['batch_budget']=BudgetGuard(R/P['budget_db'],P['limits'],P['per_run_limits']).usage();save()
    analysis=subprocess.run([str(R/'.venv/bin/python'),str(R/'analyze_v3r4_remote.py')],cwd=R,capture_output=True,text=True,timeout=90)
    (R/'feedback_v3r4_300_analysis.log').write_text(analysis.stdout+analysis.stderr)
    print(json.dumps(STATE))
if __name__=='__main__':main()
