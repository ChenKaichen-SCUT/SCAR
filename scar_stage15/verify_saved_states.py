"""Server audit against the original formal checkpoint bytes; zero API."""
import argparse
import contextlib
from pathlib import Path
from scar.io import atomic_json,digest
from scar_stage14.common import records


def main():
    p=argparse.ArgumentParser();p.add_argument('--runtime',required=True);a=p.parse_args()
    from scar.environment import restore,state_digest
    checks=[]
    with open('/dev/null','w') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        for ep in records('results/stage15/native_audit.jsonl.gz'):
            for row in ep['rows']:
                path=Path(a.runtime)/'runs'/ep['task_id']/'steps'/f"{row['index']+1:04}"/'environment.pkl'
                actual=state_digest(restore(path,set_rng=False))
                assert actual==row['state_hash'],(ep['task_id'],row['index'])
                checks.append({'task_id':ep['task_id'],'index':row['index'],'state_hash':actual})
    result={'passed':True,'original_formal_checkpoint_hashes_matched':len(checks),'digest':digest(checks),'api_calls':0,
            'scope':'saved original post-action world, physical agents, RNG, live rules, scores and observations, not just a second replay'}
    atomic_json('results/stage15/original_checkpoint_verification.json',result);print(result)

if __name__=='__main__':main()
