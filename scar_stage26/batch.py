import concurrent.futures
import subprocess
import sys
from .common import *

def task(n):
    (RUNTIME/'logs').mkdir(parents=True,exist_ok=True)
    with (RUNTIME/'logs'/f'{case_id(n)}.log').open('w') as f:
        p=subprocess.run([sys.executable,'-m','scar_stage26.run','--start',str(n)],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
    out=RESULTS/'runs'/case_id(n)/'Oracle'/'summary.json'
    summary=read(out) if out.exists() else None;verification_code=None
    if p.returncode==0 and summary and summary['status'] in ['step_limit','native_done','agent_decision_exhausted']:
        with (RUNTIME/'logs'/f'{case_id(n)}_verify.log').open('w') as f:
            verification_code=subprocess.run([sys.executable,'-m','scar_stage26.verify','--start',str(n)],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT).returncode
    return dict(case=case_id(n),returncode=p.returncode,verification_returncode=verification_code,summary=summary)

def main():
    check_freeze()
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:records=list(pool.map(task,CASES))
    complete=all(r['returncode']==0 and r['verification_returncode']==0 and r['summary'] and r['summary']['status'] in ['step_limit','native_done','agent_decision_exhausted'] for r in records)
    write(RESULTS/'completion.json',dict(complete=complete,cases=records,independent_parent_episodes=1))
    print(json.dumps(dict(complete=complete,cases=len(records))),flush=True)

if __name__=='__main__':main()
