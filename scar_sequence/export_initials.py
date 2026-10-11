"""Export experiment-generated initial states; no provider objects or credentials."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
from scar.environment import restore,state_digest
from scar.io import atomic_json


def export(output='results/sequence'):
    root=Path(output);cases=json.loads((root/'dataset/cases.json').read_text());folder=root/'dataset/initial_states';folder.mkdir(exist_ok=True)
    manifest=[]
    for case in cases:
        data=Path(case['initial_snapshot']).read_bytes()
        if re.search(rb'sk-[A-Za-z0-9_-]{16,}',data):raise ValueError('Potential credential in initial state; export blocked')
        env=restore(data,set_rng=False)
        # snapshot() replaced all policy objects with the official physical agent.
        if any(hasattr(a,'llm') or hasattr(a,'cfg') or hasattr(a,'controller') for a in env.agents):
            raise ValueError('Policy/provider object unexpectedly present in initial snapshot')
        if state_digest(env)!=case['state_hash']:raise ValueError('Initial physical hash mismatch')
        path=folder/(case['id']+'.pkl.gz');path.write_bytes(gzip.compress(data,mtime=0))
        manifest.append({'case_id':case['id'],'path':str(path),'state_hash':case['state_hash'],
            'serialized_sha256':hashlib.sha256(data).hexdigest(),'compressed_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'bytes':path.stat().st_size,'contains_only_physical_environment':True})
    atomic_json(root/'dataset/initial_state_manifest.json',manifest)
    return manifest


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',default='results/sequence');a=p.parse_args()
    m=export(a.output);print(json.dumps({'states':len(m),'compressed_bytes':sum(r['bytes'] for r in m)}))
