"""Portable restoration; paid reruns require an explicit CLI flag and key path."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
from scar.io import atomic_json,digest
from scar.environment import restore,state_digest
from scar_sequence.run import make_tasks,run_batch


def main():
    p=argparse.ArgumentParser();p.add_argument('--runtime',required=True)
    p.add_argument('--run-closed-loop',action='store_true');p.add_argument('--key');p.add_argument('--workers',type=int,default=12)
    a=p.parse_args();runtime=Path(a.runtime);root=Path('results/sequence')
    freeze=json.loads((root/'freeze.json').read_text());cases=json.loads((root/'dataset/cases.json').read_text())
    config=json.loads(Path('configs/protocol_sequence.json').read_text())
    assert digest(cases)==freeze['dataset_digest']
    for name,sha in freeze['code_hashes'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==sha,name
    paths={};(runtime/'initials').mkdir(parents=True,exist_ok=True)
    for case in cases:
        data=gzip.decompress((root/'dataset/initial_states'/(case['id']+'.pkl.gz')).read_bytes())
        assert hashlib.sha256(data).hexdigest()==case['snapshot_sha256']
        assert state_digest(restore(data,set_rng=False))==case['state_hash']
        path=runtime/'initials'/(case['id']+'.pkl');path.write_bytes(data);paths[case['id']]=str(path.resolve())
    tasks=make_tasks(config,cases)
    for task in tasks:task['initial_snapshot']=paths[task['id']]
    atomic_json(runtime/'tasks.json',tasks)
    atomic_json(runtime/'restoration.json',{'states':len(cases),'dataset_digest':digest(cases),
        'path_mapping_only':True,'original_policy_hashes_verified':True,'paid_run_requested':a.run_closed_loop})
    print(f'Restored {len(cases)} exact physical states; paid execution requested: {a.run_closed_loop}')
    if a.run_closed_loop:
        if not a.key:p.error('--key is required for paid closed-loop reruns')
        run_batch(config,runtime,a.key,tasks,a.workers)


if __name__=='__main__':main()
