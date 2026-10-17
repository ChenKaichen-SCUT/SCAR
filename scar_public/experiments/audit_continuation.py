"""Prefix-only trigger replay. Future feedback is read solely by the evaluator."""
import argparse
from collections import Counter
import json
from pathlib import Path
from time import perf_counter

from scar_public.continuation import ContinuationMemory, task_key, feedback_lines
from scar_public.causal_model import digest
from scar_public.task_progress import update_obligations


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--traces', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    episodes = []
    for block in sorted(a.traces.iterdir()):
        for arm in ('checked', 'sentry', 'v16'):
            paths = sorted((block/arm/'trace').glob('*.json'))
            if not paths: continue
            m = ContinuationMemory(); tasks = {}; events = []; triggers = []; counts = Counter(); ms = 0
            for path in paths:
                r = json.loads(path.read_text()); parsed = json.loads(r['response']); step=r['step']-1
                started = perf_counter()
                m.observe(r['observation'], step)
                update_obligations(tasks, r['observation'], step, events)
                task = digest(sorted(v['quote'] for v in tasks.values()))
                trigger = m.assess(r['action'], task)
                m.commit(r['action'], task)
                ms += (perf_counter()-started)*1000
                counts['decisions'] += 1
                if trigger:
                    counts[trigger['kind']] += 1
                    # Outcome labels are diagnostic; they never enter m.assess.
                    future = r['next_observation']
                    triggers.append(dict(step=step, action=r['action'], evidence=trigger,
                        public_goal=parsed.get('frame', {}).get('goal_quote'),
                        actual_failure=feedback_lines(future),
                        actual_stage_completion='Stage completed' in future,
                        actual_craft_success='I successfully crafted' in future,
                        frame=parsed.get('frame')))
            episodes.append(dict(block=block.name, arm=arm, counts=dict(counts),
                                 controller_ms=ms, triggers=triggers))
    result = dict(qualification='Development traces; trigger precision is not policy improvement or generalization.', episodes=episodes)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2), encoding='utf8')
    for arm in ('checked', 'sentry', 'v16'):
        c = Counter()
        for ep in episodes:
            if ep['arm']==arm: c.update(ep['counts'])
        print(arm, dict(c))


if __name__ == '__main__': main()
