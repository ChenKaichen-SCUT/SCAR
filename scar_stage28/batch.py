import concurrent.futures
import subprocess
import sys
from .common import *

def task(ident):
    (RUNTIME/'logs').mkdir(parents=True,exist_ok=True)
    with (RUNTIME/'logs'/f'{ident}.log').open('w') as f:
        p=subprocess.run([sys.executable,'-m','scar_stage28.run','--id',ident],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
    path=RESULTS/'runs'/ident/'OracleRecovery'/'summary.json';s=read(path) if path.exists() else None
    return dict(id=ident,returncode=p.returncode,summary=s)

def main():
    check_freeze()
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:records=list(pool.map(task,CASES))
    complete=all(r['returncode']==0 and r['summary'] and r['summary']['status'] in ['step_limit','native_done','agent_decision_exhausted'] for r in records)
    write(RESULTS/'completion.json',dict(complete=complete,cases=records))
    print(json.dumps(dict(complete=complete,cases=len(records))),flush=True)

if __name__=='__main__':main()
