"""Official pregenerated worlds, with optional online expansion disabled.

No material allocation, map, NPC, health or recipe is edited. The common initial
prefix follows only the official public tutorial instructions, before selection
of any target. Hidden task metadata belongs in build/evaluate, never in agents.
"""
import copy
import os
from pathlib import Path
import shutil

from scar.environment import AGENT_ID, create_environment, state_digest
from scar_v3.state import PublicState
from .common import load, write


def create_initial(game, seed, directory):
    directory = Path(directory)
    source = Path(os.environ['AGENTODYSSEY_ROOT'])
    static = directory/'static_world'
    for folder, name in [('env_configs', 'initial.json'), ('world_definitions', 'default.json')]:
        path = static/f'assets/{folder}/generated/{game}/{name}'
        path.parent.mkdir(parents=True, exist_ok=True)
        data = load(source/f'assets/{folder}/generated/{game}/{name}')
        if folder == 'world_definitions':
            data.setdefault('features', {})['online_expansion'] = False
        write(path, data)
    env, obs = create_environment(game, seed, directory/'world', upstream=static)
    history = []
    for _ in range(40):
        public = copy.deepcopy(env.obs[AGENT_ID])
        instruction = PublicState.observe(public).goal
        if not instruction:
            break
        obs, reward, done, info = env.step({AGENT_ID: instruction})
        env.update_scores(reward)
        history.append({'before': public, 'action': instruction, 'after': copy.deepcopy(obs[AGENT_ID])})
        if done:
            raise ValueError('official tutorial ended in game failure')
    else:
        raise ValueError('public tutorial did not finish within 40 prefix actions')
    assert not env.world_definition.get('features', {}).get('online_expansion')
    return env, history
