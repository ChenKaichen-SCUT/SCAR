"""One opt-in bounded screen. No automatic full evaluation or next-game stage."""
import argparse,hashlib,json,os,socket,subprocess,time,uuid
from pathlib import Path
from api_budget_guard import DEFAULT_LIMITS,BudgetGuard
R=Path(__file__).resolve().parent
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--game',required=True,choices=['remnant','mark','metropolis']);ap.add_argument('--execute',action='store_true');args=ap.parse_args()
    limits=dict(DEFAULT_LIMITS)
    if not args.execute:
        print(json.dumps({'mode':'dry_run_no_provider_calls','game':args.game,'max_steps':120,'shared_batch_limits':limits,'budget_file':'feedback_v5_screen_budget.sqlite','budget_persists_across_game_launches':True,'no_automatic_next_stage':True}));return
    receipt=json.loads((R/'feedback_v5_preflight.json').read_text());assert receipt['all_passed']
    for n,h in receipt['implementation_sha256'].items():assert hashlib.sha256((R/n).read_bytes()).hexdigest()==h,n
    for n,h in receipt['protected_files_unchanged'].items():assert hashlib.sha256((R/n).read_bytes()).hexdigest()==h,n
    with socket.socket() as sock:assert sock.connect_ex(('127.0.0.1',8094))!=0
    rid=args.game+'__v5_screen_'+uuid.uuid4().hex[:10];run=R/'runs'/rid;assert not run.exists()
    protocol={'run_id':rid,'game':args.game,'paid_execution_explicitly_enabled':True,'max_steps':120,'limits':limits,'per_run_limits':limits,'budget_db':'feedback_v5_screen_budget.sqlite',
       'stop_rule':'one recovery decision after repeated net cycle or 40 steps without novel information/best dependency improvement; stop after 12 further steps without improvement',
       'warning':'development screen only, not a full 500-step comparable score; no automatic continuation or other game',
       'implementation_sha256':receipt['implementation_sha256']}
    path=R/(rid+'_protocol.json');path.write_text(json.dumps(protocol,indent=2));BudgetGuard(R/protocol['budget_db'],limits)
    conf=R/(rid+'_agents.json');conf.write_text(json.dumps({'agents':[{'agent_type':'LongContextAgent','agent_id':'agent_adam_davis','agent_name':'adam_davis','llm_name':'deepseek-flash','llm_provider':'openai'}]}))
    env=os.environ.copy();env.update({'PYTHONPATH':str(R/'agentodyssey'),'AO_API_BASE_URL':'http://127.0.0.1:8094/'+rid+'/v1','AO_V5_BASE_URL':'http://127.0.0.1:8094/'+rid+'/v1','AO_CONTROL_AUDIT':str(R/'control_audit'/(rid+'.jsonl')),'PYTHONHASHSEED':'42','OMP_NUM_THREADS':'2','MKL_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'2','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'})
    proxy=None;status={'run_id':rid,'started':False}
    try:
        with (R/(rid+'_proxy.log')).open('w') as out:proxy=subprocess.Popen([str(R/'.venv/bin/python'),str(R/'api_proxy_budgeted.py'),'--protocol',str(path)],cwd=R,stdout=out,stderr=subprocess.STDOUT)
        for _ in range(50):
            with socket.socket() as sock:
                if sock.connect_ex(('127.0.0.1',8094))==0:break
            assert proxy.poll() is None,'Proxy exited before ready';time.sleep(.1)
        else:raise RuntimeError('Proxy not ready')
        status['started']=True
        with (R/(rid+'.log')).open('w') as out:
            result=subprocess.run([str(R/'.venv/bin/python'),str(R/'eval_feedback_v5.py'),'--agents_config',str(conf),'--game_name',args.game,'--max_steps','120','--seed','42','--run_dir',str(run),'--cumulative_config_save'],cwd=R/'agentodyssey',env=env,stdout=out,stderr=subprocess.STDOUT)
        tail=(R/(rid+'.log')).read_text(errors='replace')[-10000:]
        status.update(returncode=result.returncode,stop_reason='budget_stop' if 'BudgetStopped' in tail else 'stagnation_or_no_admissible_action' if 'ScreenStopped' in tail else 'normal_screen_end' if result.returncode==0 else 'execution_error')
        log=run/'agent_adam_davis/agent_log.jsonl';rs=[json.loads(x) for x in log.read_text().splitlines()] if log.exists() else []
        status.update(steps=len(rs),main_quest=sum(r['reward'].get('quest',0) for r in rs),budget=BudgetGuard(R/protocol['budget_db'],limits).usage())
    finally:
        if proxy and proxy.poll() is None:
            proxy.terminate()
            try:proxy.wait(timeout=10)
            except subprocess.TimeoutExpired:proxy.kill();proxy.wait(timeout=5)
        status['no_next_stage_started']=True;(R/(rid+'_status.json')).write_text(json.dumps(status,indent=2))
    print(json.dumps(status))
if __name__=='__main__':main()
