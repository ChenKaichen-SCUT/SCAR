"""Reconstruct Stage22's exact seed42 initial worlds; never policy inputs."""
import contextlib
import copy
import importlib
import io
import random
import tempfile
import numpy as np
from .common import *


def main():
    offline()
    from scar.environment import create_environment,state_digest,snapshot
    receipts=[]
    for game in GAMES:
        target=RESULTS/'initial'/game
        assert not target.exists(),'Never overwrite prepared experiment initial states'
        directory=source(game);initial=read(directory/'initial_public.json')
        cls=importlib.import_module(f'games.generated.{game}.rules.step_rules.main_quest').MainQuestStepRule
        original=cls._bootstrap;generated=read(directory/'config.json')['world']['auxiliary'].get('main_quest',{}).get('generated',{})
        def recorded(self,env,world):
            original(self,env,world)
            for key in self._generated:
                if key in generated:self._generated[key]=copy.deepcopy(generated[key])
        with tempfile.TemporaryDirectory(prefix='scar24-initial-') as tmp:
            random.seed(SEED);np.random.seed(SEED);cls._bootstrap=recorded
            try:
                with contextlib.redirect_stdout(io.StringIO()):env,obs=create_environment(game,SEED,Path(tmp),upstream=ENGINE)
            finally:cls._bootstrap=original
            native=json.loads(gzip.decompress((directory/'native_prebootstrap_config.json.gz').read_bytes()))
            env.world.auxiliary['ing_to_obj_map']=copy.deepcopy(native['world']['auxiliary']['ing_to_obj_map'])
            assert obs[AGENT_ID]==initial['observation'] and state_digest(env)==initial['initial_state_hash']
            target.mkdir(parents=True)
            (target/'physical.pkl.gz').write_bytes(gzip.compress(snapshot(env)))
            write(target/'initial_public.json',initial)
            receipts.append(dict(game=game,initial_hash=state_digest(env),stage22_initial_exact=True,history=[],model_calls=0,
                physical_sha256=sha(target/'physical.pkl.gz'),note='Restore recorded unordered bootstrap choices and recipe presentation order; no policy access.'))
    write(RESULTS/'initial_receipt.json',dict(passed=True,games=receipts,model_calls=0))
    print(json.dumps(receipts),flush=True)


if __name__=='__main__':main()
