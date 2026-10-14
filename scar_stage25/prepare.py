"""Three seeds/game; seed42 restores the exact prior paired initial world."""
import contextlib
import gzip
import io
import random
import shutil
import tempfile
import numpy as np
from .common import *

def main():
    offline()
    from scar.environment import create_environment,snapshot,state_digest
    receipts=[]
    for game,seed in CASES:
        target=RESULTS/'initial'/case_id(game,seed);assert not target.exists()
        if seed==42:
            shutil.copytree(ROOT/'results/stage24/initial'/game,target);initial=read(target/'initial_public.json')
        else:
            with tempfile.TemporaryDirectory(prefix='scar25-initial-') as tmp:
                random.seed(seed);np.random.seed(seed)
                with contextlib.redirect_stdout(io.StringIO()):env,obs=create_environment(game,seed,tmp,upstream=ENGINE)
                target.mkdir(parents=True)
                (target/'physical.pkl.gz').write_bytes(gzip.compress(snapshot(env),mtime=0))
                initial=dict(game=game,seed=seed,observation=obs[AGENT_ID],initial_state_hash=state_digest(env))
                write(target/'initial_public.json',initial)
        receipts.append(dict(game=game,seed=seed,case=case_id(game,seed),initial_hash=initial['initial_state_hash'],paired_prior_world=seed==42,model_calls=0))
    write(RESULTS/'initial_receipt.json',dict(passed=True,runs=receipts,new_model_calls=0))
    print('Prepared nine independent initial-state snapshots; no model calls.')

if __name__=='__main__':main()
