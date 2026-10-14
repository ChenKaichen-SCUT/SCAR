import concurrent.futures
import subprocess
import sys
from .common import *


def task(game):
    (RUNTIME/'logs').mkdir(parents=True,exist_ok=True)
    with (RUNTIME/'logs'/f'{game}.log').open('w') as f:
        result=subprocess.run([sys.executable,'-m','scar_stage24.run','--game',game],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
    p=RESULTS/'runs'/f'{game}__AGC'/'summary.json'
    return dict(game=game,returncode=result.returncode,summary=read(p) if p.exists() else None)

def main():
    check_freeze()
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(task,GAMES))
    complete=all(r['returncode']==0 and r['summary'] and r['summary']['status'] in ('step_limit','native_done','agent_decision_exhausted') for r in results)
    write(RESULTS/'batch_completion.json',dict(complete=complete,runs=results))
    print(json.dumps(dict(complete=complete,runs=[dict(game=r['game'],status=(r['summary'] or {}).get('status')) for r in results])))

if __name__=='__main__':main()
