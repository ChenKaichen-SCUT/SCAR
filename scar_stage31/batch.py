import concurrent.futures
import subprocess
import sys
from .common import *

def task(case):
    seed,method=case;ident=case_id(seed,method);(RUNTIME/'logs').mkdir(parents=True,exist_ok=True)
    if seed==42 and method=='AGC-v2':return dict(case=ident,returncode=0,summary=read(RESULTS/'runs'/ident/'summary.json'))
    with (RUNTIME/'logs'/f'{ident}.log').open('w') as f:
        r=subprocess.run([sys.executable,'-m','scar_stage31.run','--seed',str(seed),'--method',method],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
    path=RESULTS/'runs'/ident/'summary.json'
    return dict(case=ident,returncode=r.returncode,summary=read(path) if path.exists() else None)

def main():
    check_freeze()
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:results=list(pool.map(task,CASES))
    complete=all(r['returncode']==0 and r['summary'] and r['summary']['status'] in ['step_limit','native_done','agent_decision_exhausted'] for r in results)
    write(RESULTS/'completion.json',dict(complete=complete,runs=results));print(json.dumps(dict(complete=complete,statuses=[(r['case'],(r['summary'] or {}).get('status')) for r in results])),flush=True)

if __name__=='__main__':main()
