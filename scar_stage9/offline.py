"""Robot-only zero-API autonomy, paired branches and frozen-reference parity."""
import argparse
import contextlib
import copy
import gzip
import hashlib
import json
import tempfile
import time
from pathlib import Path

from scar.io import atomic_json
from scar.environment import restore, snapshot, AGENT_ID, state_digest
from scar.diagnostics.build import transition
from scar_sequence.evaluate import physical
from scar_sequence.supplement import goal_reached
from scar_unknown17.audit import branch
from scar_stage9.controller import adapted, make_controller, restore_controller

OUT = Path('results/stage9')


def rollout(raw, case, state, active, limit, failure_setup=False):
    assert case['game'] == 'robot_kingdom'
    results = []
    for _ in range(2):
        with tempfile.TemporaryDirectory() as tmp:
            env = restore(raw, tmp); ctrl = adapted(state, active); trace = []
            setup = None
            if failure_setup:
                # Public episode target only, never the hidden witness/recovery
                # answer. This creates a real failed-action challenge uniformly.
                before = physical(env, case); obs = copy.deepcopy(env.obs[AGENT_ID])
                tr = transition(env, case['target_action'])
                ctrl.observe(obs, case['target_action'], tr['after'])
                setup = {'action': case['target_action'], 'before': obs, **tr,
                         'physical_before': before, 'physical_after': physical(env, case),
                         'scope': 'one evaluator setup attempt, counted in total budget; NOT policy-selected'}
                assert tr['semantic_rejection']
            for i in range(limit-int(failure_setup)):
                if goal_reached(env, case['goal']): break
                obs = copy.deepcopy(env.obs[AGENT_ID]); before = physical(env, case)
                saved = copy.deepcopy(ctrl.to_dict())
                tick = time.monotonic(); action = ctrl.choose(obs, 'wait'); elapsed = time.monotonic()-tick
                clone = restore_controller(json.loads(json.dumps(saved)))
                assert clone.choose(obs, 'wait') == action and clone.to_dict() == ctrl.to_dict()
                decision = copy.deepcopy(ctrl.last_choice)
                tr = transition(env, action); ctrl.observe(obs, action, tr['after'])
                trace.append({'index': i, 'before': obs, 'after': tr['after'], 'action': action,
                    'decision': decision, 'feedback': tr['feedback'], 'rejected': tr['semantic_rejection'],
                    'physical_before': before, 'physical_after': physical(env, case),
                    'goal': goal_reached(env, case['goal']), 'events': copy.deepcopy(ctrl.events),
                    'seconds': elapsed, 'checkpoint_roundtrip': True, 'state_hash': state_digest(env)})
                ctrl.events.clear()
            results.append({'trace': trace, 'setup': setup, 'goal': goal_reached(env, case['goal']),
                            'state_hash': state_digest(env), 'controller': ctrl.to_dict()})
    assert results[0]['state_hash'] == results[1]['state_hash']
    assert [x['action'] for x in results[0]['trace']] == [x['action'] for x in results[1]['trace']]
    return dict(results[0], repeated_twice=True, base_proposal='wait', extra_API_calls=0,
                scope='autonomous deterministic recovery from public historical controller state; NO evaluator suffix')


def critical(root):
    cases = {c['id']: c for c in json.loads((OUT/'cases.json').read_text())}
    records = []
    with (root/'critical.log').open('w') as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        for old in json.loads(Path('results/stage8/negative_counterfactuals.json').read_text())['records']:
            if old['case_id'] not in cases:
                continue  # Filtering precedes loading any non-Robot snapshot.
            case = cases[old['case_id']]
            raw = gzip.decompress(Path(old['state']['path']).read_bytes())
            for active in [False, True]:
                result = rollout(raw, case, old['controller_state'], active, 40-old['index'])
                records.append({'case_id': case['id'], 'source_method': old['method'], 'source_index': old['index'],
                    'method': 'F2' if active else 'F1', 'state': old['state'], 'result': result,
                    'autonomous_goal': result['goal'], 'first_action': result['trace'][0]['action'] if result['trace'] else None,
                    'source_old_action': old['original_action']})
            if case['goal']['name'] == 'bandage_roll':
                for active in [False, True]:
                    result = rollout(raw, case, old['controller_state'], active, 9, failure_setup=True)
                    records.append({'case_id': case['id'], 'source_method': old['method'], 'source_index': old['index'],
                        'method': 'F2' if active else 'F1', 'state': old['state'], 'result': result,
                        'autonomous_goal': result['goal'], 'first_action': result['trace'][0]['action'],
                        'failure_setup': True, 'source_old_action': old['original_action']})
    atomic_json(OUT/'critical_autonomous.json', records)
    print(json.dumps([{'case': r['case_id'], 'old': r['source_method'], 'index': r['source_index'],
        'method': r['method'], 'goal': r['autonomous_goal'], 'actions': [t['action'] for t in r['result']['trace']]} for r in records]))
    return records


def historical(root):
    cases = {c['id']: c for c in json.loads((OUT/'cases.json').read_text())}
    parity, bounded, counterfactuals = [], [], []
    with (root/'historical.log').open('w') as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        for method, source in [('F0', 'P1'), ('F-Old', 'P3')]:
            for ep in map(json.loads, gzip.open(f'results/stage8/trajectories_{source}.jsonl.gz', 'rt')):
                if ep['case_id'] not in cases: continue
                for row in ep['rows']:
                    ctrl = restore_controller(row['stage7_state_before'])
                    got = ctrl.choose(row['observation'], row['proposed_action'])
                    parity.append({'method': method, 'case_id': ep['case_id'], 'index': row['index'], 'passed': got == row['executed_action']})
        for source in ['P0', 'P1', 'P2', 'P3', 'P4']:
            for ep in map(json.loads, gzip.open(f'results/stage8/trajectories_{source}.jsonl.gz', 'rt')):
                if ep['case_id'] not in cases: continue
                case = cases[ep['case_id']]
                raw = gzip.decompress((OUT/'initial_states'/(case['id']+'.pkl.gz')).read_bytes())
                with tempfile.TemporaryDirectory() as tmp:
                    env = restore(raw, tmp); n = 0
                    for row in ep['rows']:
                        actions = {}
                        for active in [False, True]:
                            ctrl = adapted(row['stage7_state_before'], active)
                            tick = time.monotonic(); action = ctrl.choose(row['observation'], row['proposed_action'])
                            clone = restore_controller(json.loads(json.dumps(ctrl.to_dict())))
                            bounded.append({'source': source, 'case_id': ep['case_id'], 'index': row['index'],
                                'active': active, 'seconds': time.monotonic()-tick, 'roundtrip': clone.to_dict() == ctrl.to_dict(),
                                'candidate_checks': ctrl.candidates, 'depth': len((ctrl.recovery or {}).get('stack', []))})
                            actions['F2' if active else 'F1'] = action
                        # Exhaustive decision checks; predeclared bounded physical
                        # sample: first four failed/wait historical states per episode.
                        if n < 4 and (row['semantic_rejection'] or row['executed_action'] == 'wait'):
                            state = snapshot(env); variants = {a: branch(state, [a], case) for a in set(actions.values()) | {row['executed_action']}}
                            counterfactuals.append({'case_id': case['id'], 'source': source, 'index': row['index'],
                                'public_observation': row['observation'], 'base_proposal': row['proposed_action'],
                                'original_action': row['executed_action'], 'new_actions': actions, 'variants': variants,
                                'scope': 'same state and same saved proposal; instantaneous effects only'})
                            n += 1
                        transition(env, row['executed_action'])
    atomic_json(OUT/'reference_parity.json', parity)
    with gzip.open(OUT/'historical_conditions.jsonl.gz', 'wt') as f:
        for r in bounded: f.write(json.dumps(r)+'\n')
    with gzip.open(OUT/'historical_counterfactuals.jsonl.gz', 'wt') as f:
        for r in counterfactuals: f.write(json.dumps(r, ensure_ascii=False)+'\n')
    return {'reference_decisions': len(parity), 'parity_passed': all(r['passed'] for r in parity),
        'new_condition_decisions': len(bounded), 'physical_paired_states': len(counterfactuals),
        'bounded_and_roundtrip_passed': all(r['roundtrip'] and r['candidate_checks'] <= 48 and r['depth'] <= 4 and r['seconds'] < 1 for r in bounded)}


def main():
    p = argparse.ArgumentParser(); p.add_argument('--runtime', required=True); p.add_argument('--critical-only', action='store_true')
    a = p.parse_args(); root = Path(a.runtime); root.mkdir(parents=True, exist_ok=True)
    records = critical(root)
    if a.critical_only: return
    checks = historical(root)
    # The previously demonstrated bandage and late fiend states must now recover
    # autonomously; early fiend states remain separately reported, never hidden.
    mandatory = [r for r in records if r['case_id'] == 'sequence-48401b39ba565b57' or r['source_index'] in {16, 18}]
    actual_recovery = [r for r in records if r.get('failure_setup') and r['method'] == 'F2']
    checks.update(api_calls=0, only_game='robot_kingdom', critical_count=len(records),
                  real_failure_plan_return_passed=all(any(e['origin'] == 'real_feedback_failure' and
                      e['status'] == 'original_action_succeeded' and len(e['attempts']) <= 8
                      for e in r['result']['controller']['recovery_records']) and r['autonomous_goal'] for r in actual_recovery),
                  mandatory_autonomous_checks=len(mandatory), critical_passed=all(r['autonomous_goal'] for r in mandatory))
    checks['passed'] = all(v for k, v in checks.items() if k.endswith('_passed'))
    atomic_json(OUT/'offline_checks.json', checks); print(json.dumps(checks)); assert checks['passed']


if __name__ == '__main__': main()
