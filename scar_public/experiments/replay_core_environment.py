"""Replay recorded formal actions without LLM calls, under the recorded hash seed.

Run once per completed block, in a process with its manifest's PYTHONHASHSEED.
Private snapshots are inputs; only hashes and mismatch counts are exported.
"""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import sys
import time

from scar.environment import AGENT_ID, restore, snapshot, state_digest


def audit(block):
    manifest = json.loads((block / 'manifest.json').read_text())
    assert os.environ.get('PYTHONHASHSEED') == manifest['hash_seed']
    assert (block / 'result.json').exists(), 'Only completed blocks may be audited'
    initial = (block / 'initial.pkl').read_bytes()
    receipt = json.loads((block / 'initial_receipt.json').read_text())
    assert hashlib.sha256(initial).hexdigest() == receipt['sha256']
    output = dict(block=block.name, hash_seed=manifest['hash_seed'], arms={},
                  override_one_step_counterfactuals=[],
                  counterfactual_scope='Offline one-step branches only; no model calls, no full-policy value estimate, excluded from formal episode budgets.')
    started = time.perf_counter()
    for arm in manifest['arms']:
        state = initial
        count = 0
        replay_dir = block / 'replay_private' / arm
        replay_dir.mkdir(parents=True, exist_ok=True)
        for path in sorted((block / arm / 'trace').glob('*.json')):
            row = json.loads(path.read_text())
            with contextlib.redirect_stdout(sys.stderr):
                env = restore(state, replay_dir)
                assert state_digest(env) == row['before_digest'], (arm, row['step'], 'before')
                assert env.obs[AGENT_ID]['text'] == row['observation'], (arm, row['step'], 'input')
                obs, reward, done, info = env.step({AGENT_ID: row['action']})
                env.update_scores(reward)
                assert state_digest(env) == row['after_digest'], (arm, row['step'], 'after')
                assert obs[AGENT_ID]['text'] == row['next_observation'], (arm, row['step'], 'output')
                assert env.scores[AGENT_ID] == row['scores'], (arm, row['step'], 'scores')
                assert bool(done) == row['done'], (arm, row['step'], 'done')
                actual_state = snapshot(env)
                response = json.loads(row['response'])
                decision = response.get('core_gate', {})
                if arm == 'checked' and decision.get('changed'):
                    alternative = restore(state, replay_dir)
                    previous_scores = dict(alternative.scores[AGENT_ID])
                    alt_obs, alt_reward, alt_done, _ = alternative.step({AGENT_ID:decision['proposed']})
                    alternative.update_scores(alt_reward)
                    output['override_one_step_counterfactuals'].append(dict(
                        step=row['step'],executed=row['action'],llm_proposed=decision['proposed'],
                        actual_score_change={k:v-previous_scores.get(k,0) for k,v in row['scores'].items()},
                        proposed_score_change={k:v-previous_scores.get(k,0) for k,v in alternative.scores[AGENT_ID].items()},
                        actual_feedback=row['next_observation'],proposed_feedback=alt_obs[AGENT_ID]['text'],
                        actual_done=row['done'],proposed_done=bool(alt_done)))
                state = actual_state
            count += 1
        output['arms'][arm] = dict(transitions=count, mismatches=0)
    output['elapsed_seconds'] = time.perf_counter() - started
    (block / 'environment_replay_audit.json').write_text(json.dumps(output, indent=2))
    print(json.dumps(dict(block=block.name,arms=output['arms'],elapsed_seconds=output['elapsed_seconds'],
                          one_step_counterfactuals=len(output['override_one_step_counterfactuals']))))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--block', type=Path, required=True)
    audit(p.parse_args().block)
