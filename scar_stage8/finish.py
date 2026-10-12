"""Finite one-shot completion pipeline; no extra model calls or reruns."""
import argparse,subprocess,sys,time,json
from pathlib import Path
from scar.io import atomic_json

def main():
    p=argparse.ArgumentParser();p.add_argument('--runtime',required=True);p.add_argument('--workers',type=int,default=8);p.add_argument('--wait-for-batch',action='store_true');a=p.parse_args()
    if a.wait_for_batch:
        atomic_json(Path(a.runtime)/'finish_status.json',{'phase':'waiting_for_finite_batch'})
        deadline=time.monotonic()+10800
        while time.monotonic()<deadline:
            state=json.loads((Path(a.runtime)/'progress.json').read_text())
            if state['phase']=='batch_returned':break
            time.sleep(30)
        else:raise TimeoutError('Batch did not complete within3hours')
    for module in ['failure_audit','evaluate','decision_audit','analyze','verify','report']:
        atomic_json(Path(a.runtime)/'finish_status.json',{'phase':module})
        cmd=[sys.executable,'-m','scar_stage8.'+module,'--runtime',a.runtime]
        if module in ['evaluate','decision_audit','verify']:cmd+=['--workers',str(a.workers)]
        subprocess.run(cmd,check=True)
    atomic_json(Path(a.runtime)/'finish_status.json',{'phase':'verified_report_ready','api_calls_in_postprocess':0})
if __name__=='__main__':main()
