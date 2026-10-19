"""Continue each paid prefix once to at most 500 steps. Policy stop rules preserved."""
import concurrent.futures,hashlib,json,os,socket,subprocess,threading,time
from pathlib import Path
from budget_guard_v5_full import BudgetGuard
R=Path(__file__).resolve().parent;PROTO=json.loads((R/'v5_full500_protocol.json').read_text());LOCK=threading.Lock();S=R/'v5_full500_status.json'
STATE={'phase':'prepared','all_processes_stopped':False,'runs':{s['id']:{**s,'status':'queued'} for s in PROTO['runs']}}
def rows(p):
    out=[]
    if p.exists():
        for line in p.read_text().splitlines():
            try:out.append(json.loads(line))
            except json.JSONDecodeError:pass
    return out
def save():
    t=S.with_suffix('.json.tmp');t.write_text(json.dumps(STATE,indent=2));t.replace(S)
def update(rid,**kw):
    with LOCK:STATE['runs'][rid].update(kw);save()
def run_one(spec):
    rid=spec['id'];g=spec['game'];run=R/'runs'/rid;assert not run.exists()
    conf=R/(rid+'_agents.json');conf.write_text(json.dumps({'agents':[{'agent_type':'LongContextAgent','agent_id':'agent_adam_davis','agent_name':'adam_davis','llm_name':'deepseek-flash','llm_provider':'openai'}]}))
    env=os.environ.copy();env.update({'PYTHONPATH':str(R/'agentodyssey'),'AO_API_BASE_URL':'http://127.0.0.1:8094/'+rid+'/v1','AO_V5_BASE_URL':'http://127.0.0.1:8094/'+rid+'/v1','AO_CONTROL_AUDIT':str(R/'control_audit'/(rid+'.jsonl')),
        'AO_REPLAY_AGENT_LOG':str(R/'runs'/spec['source_run']/'agent_adam_davis/agent_log.jsonl'),'AO_REPLAY_RECEIPT':str(R/(rid+'_prefix_receipt.json')),
        'PYTHONHASHSEED':'42','PYTHONUNBUFFERED':'1','OMP_NUM_THREADS':'2','MKL_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'2','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'})
    cmd=[str(R/'.venv/bin/python'),'-u',str(R/'eval_v5_continue.py'),'--agents_config',str(conf),'--game_name',g,'--max_steps','500','--seed','42','--run_dir',str(run),'--cumulative_config_save']
    with (R/(rid+'.log')).open('w') as out:
        p=subprocess.Popen(cmd,cwd=R/'agentodyssey',env=env,stdout=out,stderr=subprocess.STDOUT);update(rid,status='running',pid=p.pid)
        code=p.wait()
    log=rows(run/'agent_adam_davis/agent_log.jsonl');tail=(R/(rid+'.log')).read_text(errors='replace')[-8000:];api=rows(R/'telemetry'/rid/'api_calls.jsonl')
    stops=[x['reason'] for x in api if x.get('event')=='budget_or_safety_stop']
    reason='environment_done' if log and log[-1].get('episode_done') else '500_step_limit' if len(log)==500 else 'execution_error'
    if 'BudgetStopped' in tail:reason=stops[-1] if stops else 'budget_stop'
    elif 'ScreenStopped' in tail:reason='v5_stagnation_after_replan' if 'stagnation_after_one_replan' in tail else 'v5_no_admissible_action'
    info={'status':'finished','returncode':code,'stop_reason':reason,'steps':len(log),'main_quest':sum(x['reward'].get('quest',0) for x in log),
        'supplementary':sum(sum(x['reward'].get(k,0) for k in ['side_quest','exploration','craft','unique_kill']) for x in log),
        'total_lifetime_budget':BudgetGuard(R/PROTO['budget_db'],PROTO['limits'],PROTO['per_run_limits']).usage(spec['budget_scope'])}
    if code:info['error_tail']=tail[-2200:]
    pr=R/(rid+'_prefix_receipt.json');info['prefix_reconstruction']=json.loads(pr.read_text()) if pr.exists() else None
    if (run/'config.jsonl').exists() and (run/'config.jsonl').stat().st_size:
        score=subprocess.run([str(R/'.venv/bin/python'),'challenge_eval.py','--'+g,str(run),'--json'],cwd=R/'agentodyssey',capture_output=True,text=True,timeout=30)
        (R/(rid+'_official_score.json')).write_text(score.stdout)
        if not score.returncode:info['official_score']=json.loads(score.stdout)
        else:info['score_error']=score.stderr[-1500:]
    update(rid,**info)
def main():
    assert not S.exists(),'Already registered; do not repeat a continuation'
    for n,h in PROTO['frozen_policy_sha256'].items():assert hashlib.sha256((R/n).read_bytes()).hexdigest()==h,n
    for n,h in PROTO['continuation_source_sha256'].items():assert hashlib.sha256((R/n).read_bytes()).hexdigest()==h,n
    with socket.socket() as sock:assert sock.connect_ex(('127.0.0.1',8094))!=0
    proxy=None;save()
    try:
        with (R/'v5_full500_proxy.log').open('x') as out:proxy=subprocess.Popen([str(R/'.venv/bin/python'),'-u',str(R/'api_proxy_v5_full.py'),'--protocol',str(R/'v5_full500_protocol.json')],cwd=R,stdout=out,stderr=subprocess.STDOUT)
        for _ in range(60):
            with socket.socket() as sock:
                if sock.connect_ex(('127.0.0.1',8094))==0:break
            assert proxy.poll() is None;time.sleep(.1)
        else:raise RuntimeError('Proxy not ready')
        STATE['phase']='running';STATE['proxy_pid']=proxy.pid;save()
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            futures={pool.submit(run_one,s):s['id'] for s in PROTO['runs']}
            for f in concurrent.futures.as_completed(futures):
                try:f.result()
                except Exception as e:update(futures[f],status='runner_error',error=repr(e))
    finally:
        if proxy and proxy.poll() is None:
            proxy.terminate()
            try:proxy.wait(timeout=10)
            except subprocess.TimeoutExpired:proxy.kill();proxy.wait()
        STATE['phase']='stopped';STATE['all_processes_stopped']=True;STATE['total_lifetime_budget']=BudgetGuard(R/PROTO['budget_db'],PROTO['limits'],PROTO['per_run_limits']).usage();save()
    print(json.dumps(STATE))
if __name__=='__main__':main()
