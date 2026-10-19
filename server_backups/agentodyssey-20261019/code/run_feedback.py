"""One improved trajectory in each game. Never launch any baseline."""
import concurrent.futures
import json
import os
from pathlib import Path
import signal
import subprocess
import threading
import time
R=Path(__file__).resolve().parent
PROTO=json.loads((R/'protocol_feedback_v1.json').read_text())
LOCK=threading.Lock()
STATE={'method':'feedback_v1','completed':False,'runs':{}}

def record(run_id, **values):
    with LOCK:
        STATE['runs'].setdefault(run_id,{}).update(values)
        temp=R/'feedback_status.json.tmp'
        temp.write_text(json.dumps(STATE,indent=2));temp.replace(R/'feedback_status.json')

def run_one(game):
    run_id=game+'__feedback_v1';run_dir=R/'runs'/run_id
    assert not run_dir.exists(), 'Refusing to repeat or overwrite a trajectory'
    spec=R/(run_id+'_agents.json')
    spec.write_text(json.dumps({'agents':[{'agent_type':'LongContextAgent','agent_id':'agent_adam_davis',
        'agent_name':'adam_davis','llm_name':'deepseek-flash','llm_provider':'openai'}]}))
    env=os.environ.copy();env.update({'AO_API_BASE_URL':'http://127.0.0.1:8089/'+run_id+'/v1',
        'AO_CONTROL_AUDIT':str(R/'control_audit'/f'{run_id}.jsonl'),
        'PYTHONPATH':str(R/'agentodyssey'), 'PYTHONHASHSEED':'42', 'PYTHONUNBUFFERED':'1',
        'OMP_NUM_THREADS':'2','MKL_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'2',
        'TOKENIZERS_PARALLELISM':'false','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'})
    command=[str(R/'.venv/bin/python'),'-u',str(R/'eval_feedback.py'),'--agents_config',str(spec),
             '--game_name',game,'--max_steps','500','--seed','42','--run_dir',str(run_dir),'--cumulative_config_save']
    with (R/(run_id+'.log')).open('w') as out:
        p=subprocess.Popen(command,cwd=R/'agentodyssey',env=env,stdout=out,stderr=subprocess.STDOUT)
        record(run_id,status='running',game=game,pid=p.pid,steps=0,command=command)
        while p.poll() is None:
            path=run_dir/'agent_adam_davis/agent_log.jsonl'
            rows=[]
            if path.exists():
                for line in path.read_text().splitlines():
                    try:rows.append(json.loads(line))
                    except json.JSONDecodeError:pass
            record(run_id,steps=len(rows),main_quest=sum(r['reward'].get('quest',0) for r in rows),
                   last_action=rows[-1]['action'] if rows else None)
            time.sleep(10)
        code=p.wait()
    rows=[json.loads(s) for s in (run_dir/'agent_adam_davis/agent_log.jsonl').read_text().splitlines()] if (run_dir/'agent_adam_davis/agent_log.jsonl').exists() else []
    fields={'status':'finished' if code==0 else 'failed','returncode':code,'steps':len(rows),
            'completion_reason':'step_limit' if len(rows)==500 else 'environment_done' if rows and rows[-1].get('episode_done') else 'early_stop_or_error'}
    if (run_dir/'config.jsonl').exists():
        result=subprocess.run([str(R/'.venv/bin/python'),'challenge_eval.py','--'+game,str(run_dir),'--json'],cwd=R/'agentodyssey',text=True,capture_output=True)
        (R/(run_id+'_official_score.json')).write_text(result.stdout)
        if result.returncode:fields['scoring_error']=result.stderr
        else:fields['official_score']=json.loads(result.stdout)
    record(run_id,**fields)

def main():
    assert not (R/'feedback_status.json').exists()
    assert PROTO['games']==['remnant','mark','metropolis']
    for g in PROTO['games']:assert not (R/'runs'/(g+'__feedback_v1')).exists()
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures={pool.submit(run_one,g):g for g in PROTO['games']}
        for f in concurrent.futures.as_completed(futures):
            try:f.result()
            except Exception as e:record(futures[f]+'__feedback_v1',status='runner_error',error=str(e))
    if len(STATE['runs'])==3 and all(r['status']=='finished' for r in STATE['runs'].values()):
        cmd=[str(R/'.venv/bin/python'),'challenge_eval.py']
        for g in PROTO['games']:cmd+=['--'+g,str(R/'runs'/(g+'__feedback_v1'))]
        result=subprocess.run(cmd+['--json'],cwd=R/'agentodyssey',capture_output=True,text=True)
        (R/'feedback_v1_three_games_official_score.json').write_text(result.stdout)
        STATE['completed']=result.returncode==0
    (R/'feedback_status.json').write_text(json.dumps(STATE,indent=2))
    proxy=int((R/'proxy_feedback.pid').read_text())
    path=Path('/proc')/str(proxy)/'cmdline'
    if path.exists() and b'api_proxy_feedback.py' in path.read_bytes():os.kill(proxy,signal.SIGTERM)
    print(json.dumps(STATE),flush=True)

if __name__=='__main__':main()
