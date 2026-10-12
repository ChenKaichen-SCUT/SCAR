"""One finite postprocessing pipeline; no model calls and no policy changes."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
from scar.io import atomic_json


def main():
    p=argparse.ArgumentParser();p.add_argument('--runtime',required=True);p.add_argument('--wait-for-completion',action='store_true');a=p.parse_args();root=Path(a.runtime)
    deadline=time.monotonic()+7200
    while True:
        main_done=(root/'progress.json').exists() and json.loads((root/'progress.json').read_text()).get('phase')=='batch_returned'
        control_done=(root/'all_tasks.json').exists()
        if main_done and control_done:break
        if not a.wait_for_completion or time.monotonic()>deadline:raise RuntimeError('Formal batch not finished')
        time.sleep(15)
    tasks=json.loads((root/'all_tasks.json').read_text());bad=[]
    for t in tasks:
        path=root/'runs'/t['task_id']/'status.json'
        status=json.loads(path.read_text()).get('status') if path.exists() else 'missing'
        if status not in {'completed','method_abort'}:bad.append({'task_id':t['task_id'],'status':status})
    if bad:
        atomic_json(root/'finish_status.json',{'phase':'incomplete','tasks':bad});raise RuntimeError('Incomplete tasks require investigation, not silent exclusion')
    for module in ['evaluate','analyze','verify','success_checks']:
        atomic_json(root/'finish_status.json',{'phase':module,'started':time.time()})
        subprocess.run([sys.executable,'-m','scar_unknown17.'+module,'--runtime',str(root)],check=True)
    atomic_json(root/'finish_status.json',{'phase':'verified_awaiting_report_publication','finished':time.time()})

if __name__=='__main__':main()
