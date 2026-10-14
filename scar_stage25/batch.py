import concurrent.futures
import subprocess
import sys
from .common import *

def task(case):
    game,seed=case;(RUNTIME/'logs').mkdir(parents=True,exist_ok=True)
    with (RUNTIME/'logs'/f'{case_id(game,seed)}.log').open('w') as f:
        r=subprocess.run([sys.executable,'-m','scar_stage25.run','--game',game,'--seed',str(seed)],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
    p=RESULTS/'runs'/case_id(game,seed)/'summary.json'
    return dict(case=case_id(game,seed),returncode=r.returncode,summary=read(p) if p.exists() else None)

def main():
    check_freeze()
    with concurrent.futures.ThreadPoolExecutor(max_workers=9) as pool:results=list(pool.map(task,CASES))
    complete=all(r['returncode']==0 and r['summary'] and r['summary']['status'] in ['step_limit','native_done','agent_decision_exhausted'] for r in results)
    write(RESULTS/'completion.json',dict(complete=complete,runs=results));print(json.dumps(dict(complete=complete,statuses=[(r['case'],(r['summary'] or {}).get('status')) for r in results])))

if __name__=='__main__':main()
