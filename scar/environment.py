"""Real upstream environments; exact snapshots include RNG and live step-rule state."""
import contextlib
import copy
import hashlib
import os
from pathlib import Path
import random
import shutil
import tempfile

import cloudpickle
import numpy as np


AGENT_ID = "agent_adam_davis"


def create_environment(game, seed, run_dir, agent=None, upstream=None):
    from utils import dynamic_load_game_class
    upstream = Path(upstream or os.environ["AGENTODYSSEY_ROOT"])
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    config_path = run_dir / "config.json"
    if config_path.exists():
        raise FileExistsError(f"Refusing to overwrite {config_path}")
    shutil.copyfile(upstream / f"assets/env_configs/generated/{game}/initial.json", config_path)
    if agent is None:
        agent = dynamic_load_game_class(game, "agent", "Agent")(AGENT_ID, "adam_davis")
    env = dynamic_load_game_class(game, "env", "AgentOdysseyEnv")(
        seed=seed, agents=[agent], run_dir=str(run_dir), config_path=str(config_path),
        world_definition_path=str(upstream / f"assets/world_definitions/generated/{game}/default.json"),
        enable_obs_valid_actions=False, save_dep_graph_steps=None,
    )
    if env.world_definition.get("features", {}).get("online_expansion"):
        raise ValueError("Online world generation would introduce unbudgeted/uncontrolled model calls")
    obs = env.reset()
    return env, obs


def snapshot(env):
    """Only trusted local snapshots. Never includes LLM objects or credentials."""
    from utils import dynamic_load_game_class
    game = type(env).__module__.split(".")[-2]
    clean = copy.copy(env)
    clean.agents = []
    for agent in env.agents:
        physical = dynamic_load_game_class(game, "agent", "Agent")(agent.id, agent.name)
        physical.from_dict(agent.to_dict(), env.world.container_instances)
        physical._action_rules_module = agent._action_rules_module
        physical._base_action_rule_class = agent._base_action_rule_class
        clean.agents.append(physical)
    return cloudpickle.dumps({"env": clean, "python_rng": random.getstate(),
                              "numpy_rng": np.random.get_state()}, protocol=5)


def save_snapshot(path, env):
    data = snapshot(env)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    temp = Path(str(path) + ".tmp")
    temp.write_bytes(data)
    temp.replace(path)
    return hashlib.sha256(data).hexdigest()


def restore(data, run_dir=None, agent=None, set_rng=True):
    data = Path(data).read_bytes() if isinstance(data, (str, Path)) else data
    saved = cloudpickle.loads(data)
    env = saved["env"]
    if run_dir:
        env.run_dir = str(run_dir)
        env.config_path = str(Path(run_dir) / "config.json")
    if agent:
        old = env.agents[0]
        agent.from_dict(old.to_dict(), env.world.container_instances)
        agent._action_rules_module = old._action_rules_module
        agent._base_action_rule_class = old._base_action_rule_class
        env.agents = [agent]
    if set_rng:
        random.setstate(saved["python_rng"])
        np.random.set_state(saved["numpy_rng"])
    return env


@contextlib.contextmanager
def isolated_copy(env):
    python_rng, numpy_rng = random.getstate(), np.random.get_state()
    with tempfile.TemporaryDirectory(prefix="scar-score-") as directory:
        clone = restore(snapshot(env), directory)
        try:
            yield clone
        finally:
            random.setstate(python_rng)
            np.random.set_state(numpy_rng)


def state_digest(env):
    from scar.io import digest
    return digest({"world": env.world.to_dict(), "agents": [a.to_dict() for a in env.agents],
                   "state": env.curr_agents_state, "rng": env.rng.getstate(),
                   "step": env.steps, "scores": env.scores, "obs": env.obs})
