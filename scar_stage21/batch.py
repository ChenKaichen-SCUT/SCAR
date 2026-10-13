"""Run the frozen interleaved schedule once; finalized episodes are never rerun."""
import argparse
import concurrent.futures
import json
import os
import subprocess
import sys
from pathlib import Path
from .common import ROOT,RESULTS,load,write
from .run import check_freeze,export_run


def job(entry,runtime,key):
    task,method=entry
    output=RESULTS/'runs'/f'{task}__{method}'/'summary.json'
    if output.exists():return load(output)
    logs=Path(runtime)/'logs';logs.mkdir(parents=True,exist_ok=True)
    cmd=[sys.executable,'-m','scar_stage21.run','--task',task,'--method',method,'--runtime',runtime,'--key-path',key]
    with (logs/f'{task}__{method}.log').open('a') as log:
        result=subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    if not output.exists():
        # An unexpected worker termination is resumed once from its committed
        # checkpoint and paid-response cache. Completed failures are never rerun.
        with (logs/f'{task}__{method}.log').open('a') as log:
            result=subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    if output.exists():return load(output)
    failure=dict(task_id=task,method=method,status='worker_crash',success=False,steps=0,error='Worker failed twice without final archive')
    folder=Path(runtime)/'runs'/f'{task}__{method}';folder.mkdir(parents=True,exist_ok=True)
    (folder/'steps').mkdir(exist_ok=True);output.parent.mkdir(parents=True,exist_ok=True)
    export_run(folder,output.parent,failure)
    return load(output)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--runtime',required=True);parser.add_argument('--workers',type=int,default=12);parser.add_argument('--key-path',default=str(ROOT.parent/'miyao.txt'));args=parser.parse_args()
    freeze=check_freeze();assert 1<=args.workers<=freeze['worker_processes'];schedule=freeze['schedule'];completed=[]
    write(RESULTS/'research_state.json',dict(phase='formal_running',formal_started=True,total_runs=len(schedule),internal_horizon=100))
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures=[pool.submit(job,entry,args.runtime,args.key_path) for entry in schedule]
        for future in concurrent.futures.as_completed(futures):
            row=future.result();completed.append(row)
            write(RESULTS/'batch_progress.json',dict(finished=len(completed),total=len(schedule),runs=completed))
    ok=all((RESULTS/'runs'/f"{r['task_id']}__{r['method']}"/'summary.json').exists() for r in completed)
    import sqlite3
    ledger=Path(args.runtime)/'budget.sqlite'
    with sqlite3.connect(ledger) as db:
        columns=['request_id','reserved_usd','charged_usd','status']
        records=[dict(zip(columns,row)) for row in db.execute('SELECT id,reserved,charged,status FROM requests ORDER BY id')]
    write(RESULTS/'cost_ledger.json',dict(requests=records,committed_usd=sum(r['charged_usd'] if r['charged_usd'] is not None else r['reserved_usd'] for r in records)))
    if ok:
        subprocess.run([sys.executable,'-m','scar_stage21.replay','--site','local','--runtime',str(Path(args.runtime)/'replay')],cwd=ROOT,check=True)
    write(RESULTS/'research_state.json',dict(phase='local_replay_complete' if ok else 'batch_incomplete',formal_started=True,total_runs=len(schedule),archived_runs=len(completed)))
    write(RESULTS/'batch_completion.json',dict(archived_all=ok,finished=len(completed),statuses={s:sum(r['status']==s for r in completed) for s in sorted({r['status'] for r in completed})}))

if __name__=='__main__':main()
