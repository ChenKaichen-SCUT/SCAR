"""Exactly one new repaired seed; no offline sampling or baseline rerun."""
import subprocess,sys
from .common import *

def main():
    assert SEEDS==[42];check_freeze();(RUNTIME/'logs').mkdir(parents=True,exist_ok=True)
    with (RUNTIME/'logs'/'online_42.log').open('w') as f:
        ret=subprocess.run([sys.executable,'-m','scar_stage32.run','--seed','42'],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
    path=RESULTS/'runs'/ident(42)/'summary.json';result=read(path) if path.exists() else None
    okay=ret.returncode==0 and result is not None and result['status'] in ['step_limit','native_done','agent_decision_exhausted']
    write(RESULTS/'online_completion.json',dict(complete=okay,runs=[dict(case='42',returncode=ret.returncode,result=result)]))
    print(json.dumps(dict(complete=okay,runs=1)),flush=True)

if __name__=='__main__':main()
