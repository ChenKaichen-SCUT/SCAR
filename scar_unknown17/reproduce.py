"""Portable frozen-state restoration; default performs zero model calls."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from scar.environment import restore,state_digest
from scar.io import atomic_json,digest
from scar_unknown17.audit import initial


def main():
    p=argparse.ArgumentParser();p.add_argument('--runtime',required=True);p.add_argument('--run-closed-loop',action='store_true')
    p.add_argument('--key');a=p.parse_args();root=Path(a.runtime);out=Path('results/unknown17')
    cs=json.loads((out/'cases.json').read_text());freeze=json.loads((out/'freeze.json').read_text())
    assert digest(cs)==freeze['dataset_digest']
    for name,h in freeze['code_hashes'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==h,name
    control=json.loads((out/'format_control_freeze.json').read_text())
    assert hashlib.sha256(Path('scar_unknown17/format_control.py').read_bytes()).hexdigest()==control['code_hash']
    (root/'initials').mkdir(parents=True,exist_ok=True)
    for c in cs:
        raw=initial(c);assert state_digest(restore(raw,set_rng=False))==c['state_hash']
        (root/'initials'/f'{c["id"]}.pkl').write_bytes(raw)
    atomic_json(root/'restoration.json',{'states':17,'all_physical_hashes_match':True,'paid_execution_requested':a.run_closed_loop})
    print(json.dumps({'restored':17,'paid_execution_requested':a.run_closed_loop}))
    if a.run_closed_loop:
        if not a.key:p.error('--key is required for explicit paid rerun')
        for module in ['run','format_control']:
            subprocess.run([sys.executable,'-m','scar_unknown17.'+module,'--runtime',str(root),'--key',a.key],check=True)
        subprocess.run([sys.executable,'-m','scar_unknown17.finish','--runtime',str(root)],check=True)

if __name__=='__main__':main()
