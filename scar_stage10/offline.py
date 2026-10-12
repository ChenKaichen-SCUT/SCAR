"""Robot original-ten historical parity, bounded decisions and native branches."""
import argparse
import contextlib
import copy
import gzip
import json
from pathlib import Path
import tempfile
import time

from scar.environment import restore, snapshot, state_digest, AGENT_ID
from scar.diagnostics.build import transition
from scar.io import atomic_json
from scar_sequence.evaluate import physical
from scar_sequence.supplement import goal_reached
from scar_unknown17.audit import branch
from scar_stage10.controller import adapted, restore_controller, METHODS

OUT = Path('results/stage10')


def rollout(raw, case, public_state, method, limit):
    endings = []; records = []
    for _ in range(2):
        with tempfile.TemporaryDirectory() as tmp:
            env = restore(raw, tmp); ctrl = adapted(public_state, method); records = []
            for i in range(limit):
                before = copy.deepcopy(env.obs[AGENT_ID]); before_physical = physical(env, case)
                action = ctrl.choose(before, 'wait')
                selected = copy.deepcopy(ctrl.last_choice)
                row = transition(env, action); ctrl.observe(before, action, row['after'])
                records.append(dict(index=i, decision=selected, **row,
                    physical_before=before_physical, physical_after=physical(env, case),
                    goal=goal_reached(env, case['goal'])))
                if records[-1]['goal']: break
            endings.append((state_digest(env), [r['action'] for r in records]))
    assert endings[0] == endings[1]
    return {'trace': records, 'goal': goal_reached(env, case['goal']), 'hash': endings[-1][0],
            'replayed_twice': True, 'base_proposal': 'wait', 'evaluator_suffix': False}


def main(runtime):
    root = Path(runtime); root.mkdir(parents=True, exist_ok=True)
    cases = {c['id']: c for c in json.loads((OUT/'cases.json').read_text())}
    assert len(cases) == 10 and all(c['game'] == 'robot_kingdom' and c['cohort'] == 'development_old10' for c in cases.values())
    parity, decisions, pairs, critical, quantity = [], [], [], [], []
    with (root/'offline.log').open('w') as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        for stage, source in [('stage7', 'C1'), ('stage8', 'P1'), ('stage9', 'F0')]:
            for episode in map(json.loads, gzip.open(f'results/{stage}/trajectories_{source}.jsonl.gz', 'rt')):
                if episode['case_id'] not in cases: continue
                for row in episode['rows']:
                    ctrl = adapted(row['stage7_state_before'], 'S0')
                    action = ctrl.choose(row['observation'], row['proposed_action'])
                    parity.append({'source': stage, 'case_id': episode['case_id'], 'index': row['index'],
                                   'passed': action == row['executed_action']})
        for path in sorted(Path('results/stage9').glob('trajectories_F*.jsonl.gz')):
            for episode in map(json.loads, gzip.open(path, 'rt')):
                if episode['case_id'] not in cases: continue
                case = cases[episode['case_id']]
                raw = gzip.decompress((OUT/'initial_states'/f'{case["id"]}.pkl.gz').read_bytes())
                with tempfile.TemporaryDirectory() as tmp:
                    env = restore(raw, tmp); sampled = 0
                    for row in episode['rows']:
                        actions = {}
                        for method in METHODS:
                            ctrl = adapted(row['stage7_state_before'], method)
                            tick = time.monotonic(); action = ctrl.choose(row['observation'], row['proposed_action'])
                            clone = restore_controller(json.loads(json.dumps(ctrl.to_dict())))
                            actions[method] = action
                            decisions.append({'source': path.name, 'case_id': case['id'], 'index': row['index'],
                                'method': method, 'action': action, 'seconds': time.monotonic()-tick,
                                'roundtrip': ctrl.to_dict() == clone.to_dict(),
                                'candidate_checks': len(getattr(ctrl, 'condition_log', [])),
                                'reason': ctrl.last_choice.get('reason')})
                        if sampled < 4 and (row['semantic_rejection'] or len(set(actions.values())) > 1):
                            before = snapshot(env)
                            variants = {a: branch(before, [a], case) for a in set(actions.values()) | {row['executed_action']}}
                            pairs.append({'case_id': case['id'], 'source': path.name, 'index': row['index'],
                                'observation': row['observation'], 'proposal': row['proposed_action'],
                                'original': row['executed_action'], 'actions': actions, 'variants': variants,
                                'scope': 'first four differing/rejected states per historical episode; all signs retained'})
                            sampled += 1
                        transition(env, row['executed_action'])
        for old in json.loads(Path('results/stage8/negative_counterfactuals.json').read_text())['records']:
            if old['case_id'] not in cases: continue
            raw = gzip.decompress(Path(old['state']['path']).read_bytes()); case = cases[old['case_id']]
            for method in METHODS:
                result = rollout(raw, case, old['controller_state'], method, 40-old['index'])
                critical.append({'case_id': case['id'], 'source_method': old['method'], 'source_index': old['index'],
                    'method': method, 'state': old['state'], 'result': result, 'autonomous_goal': result['goal']})
        # Stage9's first collection failure has two visible units and public
        # capacity. This uses the saved original state, no modified allocations.
        for old in json.loads(Path('results/stage9/negative_counterfactuals.json').read_text())['records']:
            if old['case_id'] not in cases: continue
            raw = gzip.decompress(Path(old['state']['path']).read_bytes()); case = cases[old['case_id']]
            actions = {}
            for method in METHODS:
                ctrl = adapted(old['public_controller'], method)
                action = ctrl.choose(old['public_observation'], old['original_action'])
                actions[method] = action
            effects = {a: branch(raw, [a], case) for a in set(actions.values()) | {old['original_action']}}
            quantity.append({'case_id': case['id'], 'source_method': old['method'], 'index': old['index'],
                'original': old['original_action'], 'actions': actions, 'variants': effects,
                'state': old['state'], 'purpose': 'preserve F0 batch / collect visible supply without deficit cap'})
    atomic_json(OUT/'reference_parity.json', parity)
    atomic_json(OUT/'critical_autonomous.json', critical)
    atomic_json(OUT/'quantity_counterfactuals.json', quantity)
    for name, rows in [('historical_decisions', decisions), ('historical_counterfactuals', pairs)]:
        with gzip.open(OUT/(name+'.jsonl.gz'), 'wt') as f:
            for row in rows: f.write(json.dumps(row, ensure_ascii=False)+'\n')
    result = {'only_game': 'robot_kingdom', 'original_families': 10, 'api_calls': 0,
        'reference_decisions': len(parity), 'parity_passed': all(p['passed'] for p in parity),
        'decision_checks': len(decisions), 'bounded_roundtrip_passed': all(r['roundtrip'] and r['candidate_checks'] <= 32 and r['seconds'] < 1 for r in decisions),
        'physical_paired_states': len(pairs), 'critical_rollouts': len(critical),
        'critical_successes': {m: sum(r['autonomous_goal'] for r in critical if r['method'] == m) for m in METHODS},
        'quantity_states': len(quantity),
        'scope': 'historical development states; constant wait base in critical rollouts; no model or evaluator suffix'}
    result['passed'] = result['parity_passed'] and result['bounded_roundtrip_passed']
    atomic_json(OUT/'offline_checks.json', result); print(json.dumps(result)); assert result['passed']


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--runtime', required=True); a = p.parse_args(); main(a.runtime)
