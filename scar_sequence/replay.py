"""Replay a published initial state and witness using the pinned official engine.

These are our own generated trusted pickle snapshots. Do not load untrusted
third-party pickle files. Source and SHA256 manifests accompany each state.
"""
import argparse
import contextlib
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
from scar.environment import restore,state_digest
from scar.diagnostics.build import transition
from scar_sequence.supplement import goal_reached


def main():
    p=argparse.ArgumentParser();p.add_argument('--case',required=True);p.add_argument('--dataset',default='results/sequence/dataset')
    a=p.parse_args();root=Path(a.dataset)
    case=next(c for c in json.loads((root/'cases.json').read_text()) if c['id']==a.case)
    data=gzip.decompress((root/'initial_states'/(a.case+'.pkl.gz')).read_bytes())
    assert hashlib.sha256(data).hexdigest()==case['snapshot_sha256']
    with tempfile.TemporaryDirectory() as tmp,contextlib.redirect_stderr(open('/dev/null','w')):
        env=restore(data,tmp);assert state_digest(env)==case['state_hash']
        for action in case['witness']:transition(env,action)
        assert goal_reached(env,case['goal'])
        print(json.dumps({'case_id':a.case,'steps':len(case['witness']),'goal':True,'final_state_hash':state_digest(env)}))


if __name__=='__main__':main()
