"""No-API audit of identical actions under checkpoint and hash-order changes."""
import argparse
import contextlib
import gzip
import json
import os
import sys
from pathlib import Path

from scar.environment import AGENT_ID, restore, snapshot, state_digest


def run(initial, trace, output, steps=100, reload_each=False):
    env = restore(initial)
    rows = []
    for path in sorted(Path(trace).glob('*.json'))[:steps]:
        row = json.loads(path.read_text())
        if reload_each:
            env = restore(snapshot(env))
        with contextlib.redirect_stdout(sys.stderr):
            obs, reward, done, info = env.step({AGENT_ID: row['action']})
            env.update_scores(reward)
        rows.append(dict(step=row['step'], action=row['action'], digest=state_digest(env),
                         text=obs[AGENT_ID]['text'], world=env.world.to_dict(),
                         state=env.curr_agents_state, scores=env.scores, done=done))
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(output, 'wt') as f:
        json.dump(dict(hash_seed=os.environ.get('PYTHONHASHSEED'), reload_each=reload_each, rows=rows), f)
    print(json.dumps(dict(output=str(output), steps=len(rows), final=rows[-1]['digest'])))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--initial', required=True)
    p.add_argument('--trace', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--steps', type=int, default=100)
    p.add_argument('--reload-each', action='store_true')
    a = p.parse_args()
    run(a.initial, a.trace, a.output, a.steps, a.reload_each)
