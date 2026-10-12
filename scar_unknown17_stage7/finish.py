"""Finite completion pipeline. Zero API; no policy changes or polling agent."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
from scar.io import atomic_json


def main():
    p=argparse.ArgumentParser();p.add_argument('--runtime',required=True);p.add_argument('--wait-for-completion',action='store_true');a=p.parse_args();root=Path(a.runtime)
    deadline=time.monotonic()+14400
    while True:
        path=root/'progress.json';done=path.exists() and json.loads(path.read_text()).get('phase')=='batch_returned'
        if done:break
        if not a.wait_for_completion or time.monotonic()>deadline:raise RuntimeError('Formal batch not finished')
        time.sleep(30)
    subprocess.run([sys.executable,'-m','scar_unknown17_stage7.failure_audit','--runtime',str(root)],check=True)
    from scar_unknown17_stage7.failure_audit import adjudicated_status
    tasks=json.loads((root/'tasks.json').read_text());bad=[]
    for task in tasks:
        path=root/'runs'/task['task_id']/'status.json';status=json.loads(path.read_text()).get('status') if path.exists() else 'missing'
        status=adjudicated_status(task['task_id'],status)
        if status not in {'completed','method_abort'}:bad.append({'task_id':task['task_id'],'status':status})
    if bad:
        atomic_json(root/'finish_status.json',{'phase':'incomplete','tasks':bad});raise RuntimeError('No excluded incomplete cases')
    for module in ['evaluate','decision_audit','analyze','verify','report']:
        atomic_json(root/'finish_status.json',{'phase':module,'started':time.time()})
        subprocess.run([sys.executable,'-m','scar_unknown17_stage7.'+module,'--runtime',str(root)],check=True)
    atomic_json(root/'finish_status.json',{'phase':'verified_report_ready','finished':time.time()})

if __name__=='__main__':main()
