"""One user-authorized three-game batch under the existing 80-request total cap."""
import argparse,concurrent.futures,hashlib,json,os,socket,subprocess,threading,time
from pathlib import Path
from api_budget_guard import DEFAULT_LIMITS,BudgetGuard
R=Path(__file__).resolve().parent;P=R/'v5_three_games_protocol.json';S=R/'v5_three_games_status.json';LOCK=threading.Lock()
RUNS=[{'id':g+'__v5_batch_20261018','game':g,'max_steps':120} for g in ['remnant','mark','metropolis']]
LIMITS=dict(DEFAULT_LIMITS);PER={k:v//3 for k,v in LIMITS.items()};STATE={'phase':'prepared','all_processes_stopped':False,'runs':{r['id']:{**r,'status':'queued'} for r in RUNS}}
def rows(path):
    out=[]
    if path.exists():
        for line in path.read_text().splitlines():
            try:out.append(json.loads(line))
            except json.JSONDecodeError:pass
    return out
def save():
    tmp=S.with_suffix('.json.tmp');tmp.write_text(json.dumps(STATE,indent=2));tmp.replace(S)
def update(rid,**kw):
    with LOCK:STATE['runs'][rid].update(kw);save()
def verified_receipt():
    receipt=json.loads((R/'feedback_v5_preflight.json').read_text());assert receipt['all_passed']
    for group in ['implementation_sha256','protected_files_unchanged']:
        for n,h in receipt[group].items():assert hashlib.sha256((R/n).read_bytes()).hexdigest()==h,n
    for n in ['feedback_v5_core.py','feedback_v5_agent.py','compact_decision_packet.py']:
        assert hashlib.sha256((R/'agentodyssey/agents'/n).read_bytes()).hexdigest()==receipt['implementation_sha256'][n],n
    return receipt
def run_one(spec):
    rid=spec['id'];game=spec['game'];run=R/'runs'/rid;assert not run.exists()
    conf=R/(rid+'_agents.json');conf.write_text(json.dumps({'agents':[{'agent_type':'LongContextAgent','agent_id':'agent_adam_davis','agent_name':'adam_davis','llm_name':'deepseek-flash','llm_provider':'openai'}]}))
    env=os.environ.copy();env.update({'PYTHONPATH':str(R/'agentodyssey'),'AO_API_BASE_URL':'http://127.0.0.1:8094/'+rid+'/v1','AO_V5_BASE_URL':'http://127.0.0.1:8094/'+rid+'/v1','AO_CONTROL_AUDIT':str(R/'control_audit'/(rid+'.jsonl')),'PYTHONHASHSEED':'42','PYTHONUNBUFFERED':'1','OMP_NUM_THREADS':'2','MKL_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'2','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'})
    command=[str(R/'.venv/bin/python'),'-u',str(R/'eval_feedback_v5.py'),'--agents_config',str(conf),'--game_name',game,'--max_steps',str(spec['max_steps']),'--seed','42','--run_dir',str(run),'--cumulative_config_save']
    with (R/(rid+'.log')).open('w') as out:
        p=subprocess.Popen(command,cwd=R/'agentodyssey',env=env,stdout=out,stderr=subprocess.STDOUT);update(rid,status='running',pid=p.pid)
        try:code=p.wait(timeout=1800)
        except subprocess.TimeoutExpired:p.kill();p.wait();code=-9
    log=rows(run/'agent_adam_davis/agent_log.jsonl');tail=(R/(rid+'.log')).read_text(errors='replace')[-8000:]
    events=rows(R/'telemetry'/rid/'api_calls.jsonl');denials=[x.get('reason') for x in events if x.get('event')=='budget_or_safety_stop']
    reason='environment_done' if log and log[-1].get('episode_done') else 'step_limit' if len(log)>=spec['max_steps'] else 'execution_error'
    if 'BudgetStopped' in tail:reason=denials[-1] if denials else 'budget_or_transport_stop'
    elif 'ScreenStopped' in tail:reason='stagnation_after_replan' if 'stagnation_after_one_replan' in tail else 'no_admissible_action_after_bounded_correction'
    fields={'status':'finished','returncode':code,'stop_reason':reason,'steps':len(log),'main_quest':sum(x['reward'].get('quest',0) for x in log),'supplementary':sum(sum(x['reward'].get(k,0) for k in ['side_quest','exploration','craft','unique_kill']) for x in log),'budget':BudgetGuard(R/'v5_three_games_budget.sqlite',LIMITS,PER).usage(rid)}
    if code:fields['error_tail']=tail[-2200:]
    if (run/'config.jsonl').exists():
        scored=subprocess.run([str(R/'.venv/bin/python'),'challenge_eval.py','--'+game,str(run),'--json'],cwd=R/'agentodyssey',capture_output=True,text=True,timeout=30)
        (R/(rid+'_official_score.json')).write_text(scored.stdout)
        if not scored.returncode:fields['official_score']=json.loads(scored.stdout)
        else:fields['score_error']=scored.stderr[-1000:]
    update(rid,**fields)
def main():
    global P
    ap=argparse.ArgumentParser();ap.add_argument('--execute',action='store_true');ap.add_argument('--resume-startup-fix',action='store_true');args=ap.parse_args();receipt=verified_receipt()
    if not args.execute:print(json.dumps({'mode':'dry_run','runs':RUNS,'batch_limits':LIMITS,'per_game_limits':PER,'algorithm_unchanged':True}));return
    if args.resume_startup_fix:
        P=R/'v5_three_games_recovery_protocol.json';assert P.exists() and (R/'v5_three_games_budget.sqlite').exists()
        old=json.loads(S.read_text());assert old['phase']=='stopped' and all(x.get('steps')==0 for x in old['runs'].values())
    else:assert not P.exists() and not S.exists() and not (R/'v5_three_games_budget.sqlite').exists(),'Batch already registered; refuse automatic repeat'
    assert not (R/'feedback_v5_screen_budget.sqlite').exists(),'Existing paid v5 usage must be accounted before a new batch'
    for spec in RUNS:assert not (R/'runs'/spec['id']).exists()
    with socket.socket() as sock:assert sock.connect_ex(('127.0.0.1',8094))!=0
    protocol={'paid_execution_explicitly_enabled':True,'authorization':'User requested v5 once in all three games; keep prior shared total budget, split evenly.','runs':RUNS,'limits':LIMITS,'per_run_limits':PER,'budget_db':'v5_three_games_budget.sqlite','seed':42,'model':'deepseek-flash','thinking':'disabled','workers':3,'development_screen':True,'automatic_repeats':False,'no_automatic_budget_increase':True,'v5_implementation_sha256':receipt['implementation_sha256'],'batch_source_sha256':{n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in ['api_proxy_v5_batch.py','run_v5_three_games.py','test_v5_batch_transport.py']}}
    if args.resume_startup_fix:
        protocol=json.loads(P.read_text());assert protocol['limits']==LIMITS and protocol['per_run_limits']==PER
        assert protocol['v5_implementation_sha256']==receipt['implementation_sha256']
        assert BudgetGuard(R/protocol['budget_db'],LIMITS,PER).usage()['calls']==3
    else:
        with P.open('x') as f:json.dump(protocol,f,indent=2)
    BudgetGuard(R/protocol['budget_db'],LIMITS,PER);save();proxy=None
    try:
        with (R/'v5_three_games_proxy.log').open('w') as out:proxy=subprocess.Popen([str(R/'.venv/bin/python'),'-u',str(R/'api_proxy_v5_batch.py'),'--protocol',str(P)],cwd=R,stdout=out,stderr=subprocess.STDOUT)
        for _ in range(50):
            with socket.socket() as sock:
                if sock.connect_ex(('127.0.0.1',8094))==0:break
            assert proxy.poll() is None,'Proxy failed before ready';time.sleep(.1)
        else:raise RuntimeError('Proxy not ready')
        STATE['phase']='running';STATE['proxy_pid']=proxy.pid;save()
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            tasks={pool.submit(run_one,s):s['id'] for s in RUNS}
            for f in concurrent.futures.as_completed(tasks):
                try:f.result()
                except Exception as e:update(tasks[f],status='runner_error',error=repr(e))
    finally:
        if proxy and proxy.poll() is None:
            proxy.terminate()
            try:proxy.wait(timeout=10)
            except subprocess.TimeoutExpired:proxy.kill();proxy.wait()
        STATE['phase']='stopped';STATE['all_processes_stopped']=True;STATE['batch_budget']=BudgetGuard(R/'v5_three_games_budget.sqlite',LIMITS,PER).usage();save()
    print(json.dumps(STATE),flush=True)
if __name__=='__main__':main()
