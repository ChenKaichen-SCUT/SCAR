"""Twelve isolated workers; each paid response cached, never resampled."""
import concurrent.futures
import subprocess
import sys
import time
from .common import *

def task(job):
    ident,condition=job;log=RUNTIME/'logs'/f'{ident}_{condition}.log';log.parent.mkdir(parents=True,exist_ok=True)
    with log.open('w') as f:
        p=subprocess.run([sys.executable,'-m','scar_stage27.run','--id',ident,'--condition',condition],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
    out=RESULTS/'probes'/ident/condition/'result.json'
    return dict(id=ident,condition=condition,returncode=p.returncode,result_exists=out.exists())

def main():
    check_freeze();jobs=[]
    for i,s in enumerate(samples()):
        # Counterbalance fresh A/B request ordering without selection by outcome.
        conditions=['understanding']+(['A','B'] if i%2==0 else ['B','A']) if s['action_test_eligible'] else ['understanding']
        jobs.extend((s['id'],c) for c in conditions)
    records=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        futures=[pool.submit(task,j) for j in jobs]
        for f in concurrent.futures.as_completed(futures):
            records.append(f.result())
            write(RUNTIME/'progress.json',dict(completed=len(records),total=len(jobs),errors=sum(r['returncode']!=0 for r in records),updated=time.time()))
            if records[-1]['returncode']!=0:print(json.dumps(records[-1]),flush=True)
    write(RESULTS/'completion.json',dict(complete=all(r['returncode']==0 and r['result_exists'] for r in records),jobs=records))
    print(json.dumps(dict(jobs=len(records),errors=sum(r['returncode']!=0 for r in records))),flush=True)

if __name__=='__main__':main()
