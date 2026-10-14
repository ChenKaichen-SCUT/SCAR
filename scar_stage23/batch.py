import concurrent.futures
import json
import os
import subprocess
import sys
from .common import *

def job(start):
    logs=RUNTIME/'logs';logs.mkdir(parents=True,exist_ok=True)
    with (logs/f'{case_id(start)}.log').open('a') as out:
        p=subprocess.run([sys.executable,'-m','scar_stage23.run','--start',str(start)],cwd=ROOT,
            stdout=out,stderr=subprocess.STDOUT,env=dict(os.environ,PYTHONHASHSEED='0'))
    dest=RESULTS/'case_completion'/f'{case_id(start)}.json'
    return dict(case=case_id(start),exit_code=p.returncode,**(read(dest) if dest.exists() else dict(complete=False,runs=[])))

def main():
    check_freeze();completed=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        for future in concurrent.futures.as_completed([pool.submit(job,n) for n in CASES]):
            completed.append(future.result())
            write(RESULTS/'batch_progress.json',dict(completed_cases=len(completed),total_cases=10,cases=completed))
            print(json.dumps(completed[-1],ensure_ascii=False),flush=True)
    write(RESULTS/'batch_completion.json',dict(cases=completed,complete=all(r['complete'] for r in completed),independent_parent_episodes=1))

if __name__=='__main__':main()
