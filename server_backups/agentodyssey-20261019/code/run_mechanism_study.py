"""Registered two-stage single-trajectory study; never repeat historical baselines."""
import concurrent.futures,json,os,signal,subprocess,threading,time,urllib.request
from pathlib import Path
from study_selection import select
from mechanism_study_core import VARIANTS
R=Path(__file__).resolve().parent
PROTO=json.loads((R/'protocol_mechanism_study.json').read_text())
LOCK=threading.Lock();STATE={'phase':'ablation','all_processes_stopped':False,'runs':{}}
for spec in PROTO['runs']:STATE['runs'][spec['id']]={**spec,'status':'queued'}

def save():
    p=R/'mechanism_study_status.json.tmp';p.write_text(json.dumps(STATE,indent=2));p.replace(R/'mechanism_study_status.json')
def record(rid,**kw):
    with LOCK:STATE['runs'][rid].update(kw);save()
def rows(path):
    result=[]
    if path.exists():
        for line in path.read_text(encoding='utf-8').splitlines():
            try:result.append(json.loads(line))
            except json.JSONDecodeError:pass
    return result
def balance(label):
    key=(R/'.deepseek-key').read_text().strip()
    with urllib.request.urlopen(urllib.request.Request('https://api.deepseek.com/user/balance',headers={'Authorization':'Bearer '+key}),timeout=30) as response:b=json.load(response)
    (R/('mechanism_study_balance_'+label+'.json')).write_text(json.dumps(b,indent=2));return b
def run_one(spec,disabled):
    rid=spec['id'];run_dir=R/'runs'/rid;game=spec['game'];budget=spec['max_steps']
    disabled=disabled if spec['variant']=='v4_selected' else sorted(VARIANTS[spec['variant']])
    assert not run_dir.exists(),'Refusing to overwrite or repeat a trajectory'
    conf=R/(rid+'_agents.json');conf.write_text(json.dumps({'agents':[{'agent_type':'LongContextAgent','agent_id':'agent_adam_davis','agent_name':'adam_davis','llm_name':'deepseek-flash','llm_provider':'openai'}]}))
    env=os.environ.copy();env.update({'AO_API_BASE_URL':'http://127.0.0.1:8093/'+rid+'/v1','AO_CONTROL_AUDIT':str(R/'control_audit'/f'{rid}.jsonl'),
        'AO_STUDY_VARIANT':spec['variant'],'AO_DISABLED_COMPONENTS':json.dumps(disabled),'PYTHONPATH':str(R/'agentodyssey'),
        'PYTHONHASHSEED':'42','PYTHONUNBUFFERED':'1','OMP_NUM_THREADS':'2','MKL_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'2',
        'TOKENIZERS_PARALLELISM':'false','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'})
    command=[str(R/'.venv/bin/python'),'-u',str(R/'eval_mechanism_study.py'),'--agents_config',str(conf),'--game_name',game,'--max_steps',str(budget),'--seed','42','--run_dir',str(run_dir),'--cumulative_config_save']
    logfile=R/(rid+'.log');agentlog=run_dir/'agent_adam_davis/agent_log.jsonl'
    with logfile.open('w') as out:
        p=subprocess.Popen(command,cwd=R/'agentodyssey',env=env,stdout=out,stderr=subprocess.STDOUT)
        record(rid,status='running',pid=p.pid,steps=0,selected_disabled_components=disabled,command=command)
        while p.poll() is None:
            log=rows(agentlog);record(rid,steps=len(log),main_quest=sum(r['reward'].get('quest',0) for r in log),last_action=log[-1]['action'] if log else None)
            time.sleep(15)
        code=p.wait()
    log=rows(agentlog);err=logfile.read_text(errors='replace')[-10000:]
    reason='environment_done' if log and log[-1].get('episode_done') else 'step_limit' if len(log)==budget else 'early_stop_or_error'
    if code and 'NoAdmissibleAction' in err:reason='algorithm_stalled_no_admissible_candidate'
    elif code and 'Insufficient Balance' in err:reason='api_balance_exhausted'
    fields={'status':'finished' if code==0 else 'failed','returncode':code,'steps':len(log),'main_quest':sum(r['reward'].get('quest',0) for r in log),
        'supplementary':sum(sum(r['reward'].get(k,0) for k in ['side_quest','exploration','craft','unique_kill']) for r in log),'completion_reason':reason,
        'last_action':log[-1]['action'] if log else None}
    if code:fields['error_tail']=err[-1500:]
    if (run_dir/'config.jsonl').exists():
        score=subprocess.run([str(R/'.venv/bin/python'),'challenge_eval.py','--'+game,str(run_dir),'--json'],cwd=R/'agentodyssey',text=True,capture_output=True)
        (R/(rid+'_official_score.json')).write_text(score.stdout)
        if score.returncode:fields['scoring_error']=score.stderr
        else:fields['official_score']=json.loads(score.stdout)
    else:fields['scoring_error']='No cumulative config produced'
    record(rid,**fields)
def phase(specs,workers,disabled):
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        fs={pool.submit(run_one,s,disabled):s['id'] for s in specs}
        for f in concurrent.futures.as_completed(fs):
            try:f.result()
            except Exception as e:record(fs[f],status='runner_error',error=str(e))
def main():
    assert not (R/'mechanism_study_status.json').exists()
    for spec in PROTO['runs']:assert not (R/'runs'/spec['id']).exists()
    save();phase([s for s in PROTO['runs'] if s['phase']=='ablation'],4,[])
    selection=select(PROTO['reference_at_300'],STATE['runs']);(R/'mechanism_study_selection.json').write_text(json.dumps(selection,indent=2))
    STATE['selection']=selection;STATE['phase']='v4_validation';save()
    try:b=balance('before_v4');available=b.get('is_available',False)
    except Exception as e:available=False;STATE['balance_check_error']=type(e).__name__
    if available:phase([s for s in PROTO['runs'] if s['phase']=='v4_validation'],3,selection['disabled_components'])
    else:
        for s in PROTO['runs']:
            if s['phase']=='v4_validation':record(s['id'],status='not_started',completion_reason='balance_unavailable_or_check_failed')
    STATE['phase']='stopped';STATE['all_processes_stopped']=True;save()
    result=subprocess.run([str(R/'.venv/bin/python'),str(R/'analyze_mechanism_study.py')],capture_output=True,text=True)
    (R/'mechanism_study_analysis.log').write_text(result.stdout+'\n'+result.stderr);STATE['analysis_returncode']=result.returncode;save()
    proxy=int((R/'proxy_mechanism_study.pid').read_text());p=Path('/proc')/str(proxy)/'cmdline'
    if p.exists() and b'api_proxy_mechanism_study.py' in p.read_bytes():os.kill(proxy,signal.SIGTERM)
    print(json.dumps(STATE),flush=True)
if __name__=='__main__':main()
