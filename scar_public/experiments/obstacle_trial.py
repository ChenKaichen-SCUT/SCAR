"""Development-only complete games; reuse all unchanged historical API calls.

Runs the new arm only. Baseline scores/traces stay frozen. All actual actions
are replayed with paired environment RNG, and every override gets a one-action
counterfactual from the identical private state. Neither scores nor these
counterfactual observations enter the policy.
"""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import sys

from scar.environment import AGENT_ID, restore, snapshot, state_digest
from scar.io import atomic_json
from scar_public.continuation import feedback_lines
from scar_public.experiments.continuation_branch import ReusingProvider
from scar_public.experiments.core_trial import build_system
from scar_public.obstacle_repair import ObstacleRepairAgent
from scar_public.provider import usage_summary


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--block', type=Path, required=True); p.add_argument('--root', type=Path, required=True)
    p.add_argument('--key', required=True); p.add_argument('--steps', type=int, default=300)
    p.add_argument('--agent',choices=['obstacle','hypothesis','objective'],default='obstacle')
    p.add_argument('--reuse-api',type=Path,action='append',default=[])
    a = p.parse_args(); a.root.mkdir(parents=True, exist_ok=True)
    import fcntl
    lock = (a.root/'worker.lock').open('w'); fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    manifest = json.loads((a.block/'manifest.json').read_text())
    assert os.environ['PYTHONHASHSEED'] == manifest['hash_seed']
    atomic_json(a.root/'manifest.json', dict(source_block=str(a.block), max_steps=a.steps,
        source_sha256=hashlib.sha256(Path('source_manifest.json').read_bytes()).hexdigest(),
        hash_seed=manifest['hash_seed'], agent=a.agent, qualification='Existing worlds: development, not independent validation'))
    provider = ReusingProvider(a.root/'api', a.key, historical=a.block/'api',additional_historical=a.reuse_api); provider.arm = a.agent
    state = (a.block/'initial.pkl').read_bytes(); env = restore(state)
    agent_class=ObstacleRepairAgent
    if a.agent=='hypothesis':
        from scar_public.hypothesis_repair import HypothesisRepairAgent
        agent_class=HypothesisRepairAgent
    elif a.agent=='objective':
        from scar_public.objective_repair import ObjectiveRepairAgent
        agent_class=ObjectiveRepairAgent
    agent = agent_class(provider, build_system(env, provider.model))
    prefix = True; prefix_checks = 0; replays = 0; counterfactuals = []; events = []; failures = 0
    for step in range(a.steps):
        provider.step = step
        env = restore(state, a.root/'environment'); text = env.obs[AGENT_ID]['text']; before = state_digest(env)
        with contextlib.redirect_stdout(sys.stderr):
            action, inp, outp, response = agent.act(dict(text=text, step=step))
        parsed = json.loads(response); event = parsed['continuation']
        if event.get('trigger') or event.get('previous_repair'):
            events.append(dict(step=step+1, **{k:v for k,v in event.items() if k != 'step'}))
        with contextlib.redirect_stdout(sys.stderr):
            env = restore(state, a.root/'environment')
            before_scores = env.scores.get(AGENT_ID, {})
            obs, reward, done, _ = env.step({AGENT_ID:action}); env.update_scores(reward)
            after = state_digest(env); following = obs[AGENT_ID]['text']; next_state = snapshot(env)
            replay = restore(state, a.root/'replay')
            ro, rr, rd, _ = replay.step({AGENT_ID:action}); replay.update_scores(rr)
            assert state_digest(replay) == after and ro[AGENT_ID]['text'] == following
            replays += 1
            if event['changed']:
                cf = restore(state, a.root/'counterfactual')
                co, cr, cd, _ = cf.step({AGENT_ID:event['original']}); cf.update_scores(cr)
                counterfactuals.append(dict(step=step+1, original=event['original'], executed=action,
                    original_feedback=co[AGENT_ID]['text'], executed_feedback=following,
                    original_scores=cf.scores[AGENT_ID], executed_scores=env.scores[AGENT_ID], before_scores=before_scores))
        old = json.loads((a.block/'checked/trace'/f'{step+1:04d}.json').read_text())
        if prefix:
            assert before == old['before_digest'] and text == old['observation']
            if action == old['action']:
                assert after == old['after_digest']; prefix_checks += 1
            else:
                assert event['changed'], 'Divergence before a recorded mechanism intervention'
                prefix = False
        failures += bool(feedback_lines(following))
        row = dict(step=step+1, observation=text, action=action, response=parsed, next_observation=following,
                   scores=env.scores[AGENT_ID], done=bool(done), before_digest=before, after_digest=after,
                   input_tokens=inp, output_tokens=outp)
        path = a.root/'trace'/f'{step+1:04d}.json'
        if path.exists():
            previous = json.loads(path.read_text())
            assert all(previous[k] == row[k] for k in ('action','before_digest','after_digest'))
        else:
            atomic_json(path, row)
        state = next_state
        if a.agent=='objective' and (done or step+1==a.steps):
            agent.observe_terminal(dict(text=following,step=step+1))
        result = dict(steps=step+1, scores=env.scores[AGENT_ID], done=bool(done),
            passed='completed the main quest and passed the game' in following,
            failures=failures, overrides=sum(e['changed'] for e in events),
            queries=sum('proposal' in e for e in events),
            proposal_calls=sum(e.get('proposal_calls',int('proposal' in e)) for e in events),
            replays=replays, prefix_checks=prefix_checks)
        atomic_json(a.root/'current.json', result)
        if (step+1)%10 == 0 or done or step+1 == a.steps:
            atomic_json(a.root/'events.json', events)
            atomic_json(a.root/'counterfactuals.json', counterfactuals)
            atomic_json(a.root/'outcomes.json', agent.obstacle_outcomes)
            atomic_json(a.root/'usage.json', usage_summary(a.root/'api'))
            print(json.dumps(result), flush=True)
        if done: break
    atomic_json(a.root/'result.json', dict(**result, usage=usage_summary(a.root/'api')))


if __name__ == '__main__': main()
