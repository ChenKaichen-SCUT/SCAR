"""Original-ten historical decisions and autonomous native continuations, zero API."""
import argparse
import contextlib
import copy
import gzip
import hashlib
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
from scar_stage11.controller import METHODS, adapted, restore_controller
from scar_v3.state import parse_action

OUT = Path('results/stage11')
ACTIVE = ['E0', 'E2', 'E3', 'E4']


def rollout(raw, case, public_state, method, limit):
    endings = []; records = []
    for _ in range(2):
        with tempfile.TemporaryDirectory() as tmp:
            env = restore(raw, tmp); ctrl = adapted(public_state, method); records = []
            for index in range(limit):
                before = copy.deepcopy(env.obs[AGENT_ID]); state = copy.deepcopy(ctrl.to_dict())
                action = ctrl.choose(before, 'wait'); decision = copy.deepcopy(ctrl.last_choice)
                row = transition(env, action); ctrl.observe(before, action, row['after'])
                records.append(dict(index=index, public_controller=state, decision=decision, **row,
                    physical_after=physical(env, case), goal=goal_reached(env, case['goal'])))
                if records[-1]['goal'] or row['done']: break
            endings.append((state_digest(env), [r['action'] for r in records]))
    assert endings[0] == endings[1]
    return {'trace': records, 'goal': goal_reached(env, case['goal']), 'final_hash': endings[-1][0],
            'replayed_twice': True, 'base_proposal': 'wait', 'evaluator_suffix': False,
            'waits': sum(r['action'] == 'wait' for r in records),
            'rejections': sum(r['semantic_rejection'] for r in records)}


def main(runtime):
    root = Path(runtime); root.mkdir(parents=True, exist_ok=True)
    cases = {c['id']: c for c in json.loads((OUT/'cases.json').read_text())}
    assert len(cases) == 10 and all(c['game'] == 'robot_kingdom' and c['cohort'] == 'development_old10' for c in cases.values())
    episodes = [ep for m in ['S0', 'S1', 'S2', 'S3'] for ep in map(json.loads, gzip.open(f'results/stage10/trajectories_{m}.jsonl.gz', 'rt'))]
    by_task = {e['task_id']: e for e in episodes}
    source_states = []
    # Previously published two-step diagnostics, deduplicated by physical state.
    seen = set()
    for rec in json.loads(Path('results/stage10/knowledge_counterfactuals.json').read_text())['records']:
        key = (rec['case_id'], rec['state']['serialized_sha256'])
        if key in seen: continue
        seen.add(key); ep = by_task[rec['task_id']]
        source_states.append({'case_id': rec['case_id'], 'index': rec['index'], 'source': 'Stage10 published knowledge-gap state',
            'raw': gzip.decompress(Path(rec['state']['path']).read_bytes()),
            'public_state': ep['rows'][rec['index']]['stage7_state_before']})
    targets = {'brimite_blade_blank', 'forged_blade_blank', 'fiend_helm', 'hellfire_bomb', 'hunter_gauntlets'}
    chosen = {}
    for ep in episodes:
        if ep['summary']['algorithm'] != 'S1' or cases[ep['case_id']]['goal']['name'] not in targets: continue
        metric = ep['summary']
        chosen[ep['task_id']] = min(metric['all_known_after_action'] if metric['all_known_after_action'] is not None
                                   else metric['missed_ready_records'][0]['index'], len(ep['rows'])-1)
    decisions = []; parity = []; pairs = []
    with (root/'offline.log').open('w') as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        for ep in episodes:
            case = cases[ep['case_id']]; raw = gzip.decompress((OUT/'initial_states'/f'{case["id"]}.pkl.gz').read_bytes())
            with tempfile.TemporaryDirectory() as tmp:
                env = restore(raw, tmp); sampled = 0
                for row in ep['rows']:
                    actions = {}
                    for method in METHODS:
                        ctrl = adapted(row['stage7_state_before'], method); tick = time.monotonic()
                        action = ctrl.choose(row['observation'], row['proposed_action'])
                        clone = restore_controller(json.loads(json.dumps(ctrl.to_dict())))
                        actions[method] = action
                        d = getattr(ctrl, 'decision11', {})
                        record = {'source': ep['task_id'], 'case_id': case['id'], 'index': row['index'], 'method': method,
                            'action': action, 'seconds': time.monotonic()-tick, 'roundtrip': clone.to_dict() == ctrl.to_dict(),
                            'condition_checks': len(ctrl.condition_log), 'exploration_candidates': len(d.get('exploration_candidates', [])),
                            'execution_candidates': len(d.get('execution_candidates', [])),
                            'public_nodes': len(d.get('public_goal_view', {}).get('nodes', {})),
                            'reason': ctrl.last_choice.get('reason')}
                        decisions.append(record)
                        if ep['summary']['algorithm'] == 'S1' and method in {'E0', 'E1'}:
                            parity.append({'task_id': ep['task_id'], 'index': row['index'], 'method': method,
                                           'passed': action == row['executed_action']})
                    if ep['task_id'] in chosen and row['index'] == chosen[ep['task_id']]:
                        source_states.append({'case_id': case['id'], 'index': row['index'],
                            'source': 'S1 failed task: all-known point, otherwise first missed native-ready state',
                            'raw': snapshot(env), 'public_state': row['stage7_state_before']})
                    if sampled < 4 and (row['semantic_rejection'] or len(set(actions.values())) > 1):
                        current = snapshot(env)
                        variants = {a: branch(current, [a], case) for a in sorted(set(actions.values()) | {row['executed_action']})}
                        pairs.append({'case_id': case['id'], 'source': ep['task_id'], 'index': row['index'],
                            'observation': row['observation'], 'proposal': row['proposed_action'],
                            'original': row['executed_action'], 'actions': actions, 'variants': variants,
                            'scope': 'first four differing/rejected states per historical episode, all signs retained'})
                        sampled += 1
                    transition(env, row['executed_action'])
        for old in json.loads(Path('results/stage8/negative_counterfactuals.json').read_text())['records']:
            if old['case_id'] not in cases: continue
            source_states.append({'case_id': old['case_id'], 'index': old['index'],
                'source': 'Stage8 critical original-family regression',
                'raw': gzip.decompress(Path(old['state']['path']).read_bytes()), 'public_state': old['controller_state']})
        critical = []
        for n, state in enumerate(source_states):
            case = cases[state['case_id']]; path = OUT/'historical_states'/f'{n:02}-{case["id"]}.pkl.gz'; path.parent.mkdir(exist_ok=True)
            with gzip.GzipFile(filename=str(path), mode='wb', mtime=0) as f: f.write(state['raw'])
            for method in ACTIVE:
                result = rollout(state['raw'], case, state['public_state'], method, 40-state['index'])
                critical.append({'case_id': case['id'], 'target': case['goal']['name'], 'source': state['source'],
                    'source_index': state['index'], 'method': method,
                    'state': {'path': str(path), 'serialized_sha256': hashlib.sha256(state['raw']).hexdigest()},
                    'public_controller': state['public_state'], 'result': result,
                    'autonomous_goal': result['goal'], 'E1_alias': 'E0 only for fixed wait proposals; no prompt comparison without model'})
    for name, rows in [('historical_decisions', decisions), ('historical_counterfactuals', pairs), ('critical_autonomous', critical)]:
        with gzip.open(OUT/(name+'.jsonl.gz'), 'wt') as f:
            for row in rows: f.write(json.dumps(row, ensure_ascii=False)+'\n')
    atomic_json(OUT/'reference_parity.json', parity)
    counts = {m: {'decisions': sum(r['method'] == m for r in decisions),
                  'waits': sum(r['method'] == m and r['action'] == 'wait' for r in decisions),
                  'rollout_successes': sum(r['method'] == m and r['autonomous_goal'] for r in critical),
                  'rollout_waits': sum(r['result']['waits'] for r in critical if r['method'] == m),
                  'critical_stage8_successes': sum(r['method'] == m and 'Stage8' in r['source'] and r['autonomous_goal'] for r in critical)} for m in ACTIVE}
    bounded = all(r['roundtrip'] and r['seconds'] < 2 and max(r['condition_checks'], r['exploration_candidates'], r['execution_candidates']) <= 32 and r['public_nodes'] <= 64 for r in decisions)
    result = {'api_calls': 0, 'only_game': 'robot_kingdom', 'original_families': 10,
        'reference_decisions': len(parity), 'parity_passed': all(r['passed'] for r in parity),
        'decision_checks': len(decisions), 'bounded_roundtrip_passed': bounded,
        'historical_paired_states': len(pairs), 'autonomous_states': len(source_states), 'autonomous_rollouts': len(critical),
        'counts': counts, 'scope': 'development checkpoints; no new family or edited allocation; constant wait base; no evaluator suffix',
        'passed': all(r['passed'] for r in parity) and bounded}
    atomic_json(OUT/'offline_checks.json', result); print(json.dumps(result)); assert result['passed']


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--runtime', required=True); a = p.parse_args(); main(a.runtime)
