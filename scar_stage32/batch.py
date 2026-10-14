import argparse,concurrent.futures,subprocess,sys
from .common import *

def main(phase):
    check_freeze()
    if phase=='online':
        assert read(RESULTS/'offline_summary.json')['complete'];assert (RESULTS/'online_gate.json').exists()
        cases=[str(s) for s in SEEDS]
    else:cases=[s['id'] for s in read(RESULTS/'samples.json')]
    def task(case):
        (RUNTIME/'logs').mkdir(parents=True,exist_ok=True)
        with (RUNTIME/'logs'/f'{phase}_{case}.log').open('w') as f:
            cmd=[sys.executable,'-m',f'scar_stage32.{"run" if phase=="online" else "offline_run"}',f'--{"seed" if phase=="online" else "id"}',case]
            ret=subprocess.run(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
        path=RESULTS/'runs'/ident(int(case))/'summary.json' if phase=='online' else RESULTS/'offline'/case/'result.json'
        return dict(case=case,returncode=ret.returncode,result=read(path) if path.exists() else None)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3 if phase=='online' else 12) as pool:results=list(pool.map(task,cases))
    okay=all(x['returncode']==0 and x['result'] and x['result']['status'] in ['complete','step_limit','native_done','agent_decision_exhausted'] for x in results)
    write(RESULTS/f'{phase}_completion.json',dict(complete=okay,runs=results));print(json.dumps(dict(phase=phase,complete=okay,cases=len(results))),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--phase',choices=['offline','online'],required=True);main(p.parse_args().phase)
