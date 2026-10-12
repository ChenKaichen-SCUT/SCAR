"""Independent Robot engine effects; no hidden quantities ever enter policy inputs."""
import argparse
import contextlib
import copy
import gzip
import json
import multiprocessing as mp
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from scar.io import atomic_json
from scar.environment import restore, AGENT_ID
from scar.diagnostics.scoring import score_candidate
from scar_sequence.evaluate import physical
from scar_sequence.public import ResourceTable
from scar_unknown17.audit import branch
from scar_v3.hard import owned
from scar_v3.state import parse_action
from scar_stage8.evaluate import audit_episode as resource_audit
from scar_stage9.controller import restore_controller

OUT = Path('results/stage9')


def truth(env, condition, action):
    """Scope-limited native truth of a named public condition; None is unscored."""
    p = parse_action(action); kind = condition['kind']
    world, agent = env.world, env.agents[0]
    area = world.area_instances[env.curr_agents_state['area'][AGENT_ID]]
    names = world.auxiliary['obj_name_to_id']
    oid = names.get(p.target)
    if kind == 'hands': return sum(agent.items_in_hands.values()) <= 1
    if kind == 'ground_presence': return area.objects.get(oid, 0) > 0
    if kind == 'transfer_source': return area.objects.get(oid, 0)+agent.items_in_hands.get(oid, 0) > 0
    if kind == 'materials' and condition.get('item') in names:
        return owned(env, names[condition['item']]) >= condition['amount']
    if kind == 'station':
        stations = condition.get('evidence', {}).get('required') if isinstance(condition.get('evidence'), dict) else None
        if not stations: return None
        return all(area.objects.get(names.get(s), 0) > 0 for s in stations)
    if kind.startswith('container_'):
        name = condition.get('container')
        cid = names.get(name)
        container = world.container_instances.get(cid)
        if not container and p.args and p.args[-1] == 'inventory':
            container = agent.inventory.container
            cid = container.id if container else None
        accessible = bool(container and (cid in area.objects or cid in agent.items_in_hands or cid in agent.equipped_items_in_limb))
        if kind == 'container_access': return accessible
        if not accessible: return False
        if kind == 'container_contents': return container.inventory.get(oid, 0) > 0
        if kind == 'container_capacity' and oid in world.objects:
            size = world.objects[oid].size
            return container.capacity-container.current_load(world.objects) >= size
    return None


def compact_branch(raw, action, case):
    result = branch(raw, [action], case)
    r = result['trace'][0]
    return {'action': action, 'feedback': r['feedback'], 'rejected': r['semantic_rejection'],
            'physical_before': r['physical_before'], 'physical_after': r['physical_after'],
            'public_before': r['before'], 'public_after': r['after'],
            'goal': r['goal'], 'state_hash': r['state_hash'], 'replayed_twice': True}


def audit(job):
    folder, case = job; folder = Path(folder)
    assert case['game'] == 'robot_kingdom'
    effects, comparisons, errors = [], [], []
    with tempfile.TemporaryDirectory() as tmp, open('/dev/null', 'w') as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        paths = sorted((folder/'steps').glob('*/transition.json'))
        for i, path in enumerate(paths):
            row = json.loads(path.read_text())
            raw = (folder/'initial.pkl' if i == 0 else paths[i-1].parent/'environment.pkl').read_bytes()
            env = restore(raw, tmp); after = restore(path.parent/'environment.pkl', tmp, set_rng=False)
            ctrl = restore_controller(row['stage7_state_before'])
            selected = ctrl.choose(row['observation'], row['proposed_action'])
            if selected != row['executed_action']:
                errors.append({'index': i, 'recorded': row['executed_action'], 'reproduced': selected})
            item = {'task_id': folder.name, 'case_id': case['id'], 'index': i, 'method': row.get('stage9_method'),
                    'vetoes': [], 'recovery': None}
            selection = row.get('structured', {}).get('stage9', {})
            explicit = {v['action'] for v in selection.get('rejected', [])}
            # Include internal collection/acquisition filters, not just the two
            # top-level choices. Repeated checks of one action count once/turn.
            veto_list = {v['action']: v for v in selection.get('condition_evaluations', []) if v['status'] == 'REJECT'}
            veto_list.update({v['action']: v for v in selection.get('rejected', [])})
            for veto in veto_list.values():
                scored = score_candidate(env, veto['action'])
                facts = [{**c, 'native_truth': truth(env, c, veto['action'])} for c in veto['conditions']]
                item['vetoes'].append({'action': veto['action'], 'assessment': veto,
                    'veto_source': 'top_level' if veto['action'] in explicit else 'internal_candidate_filter',
                    'native_action_rejected': scored['semantic_rejection'], 'native_feedback': scored['feedback'],
                    'conditions': facts,
                    'evidenced_negative_count': sum(c['status'] == 'REJECT' and bool(c.get('evidence')) for c in facts),
                    'native_false_condition_count': sum(c['status'] == 'REJECT' and c['native_truth'] is False for c in facts),
                    'unknown_only_veto': all(c['status'] != 'REJECT' for c in facts),
                    'executed_alternative_legal': not row['semantic_rejection'],
                    'executed_alternative_progress': row['objective_metrics']['physical_goal_delta'] > 0 or row['objective_metrics']['conditions_released'] > 0})
            pending = selection.get('recovery_selection')
            if pending:
                blocked = pending['node_action']
                before_legality = score_candidate(env, blocked)
                after_legality = score_candidate(after, blocked)
                conds = []
                for c in pending['assessment_before']['conditions']:
                    old, new = truth(env, c, blocked), truth(after, c, blocked)
                    conds.append({**c, 'native_before': old, 'native_after': new,
                                  'native_released': old is False and new is True})
                before, later = row['physical_before'], row['physical_after']
                gain = {n: v-before['accessible'].get(n, 0) for n, v in later['accessible'].items() if v > before['accessible'].get(n, 0)}
                production = {n: v-before['crafted'].get(n, 0) for n, v in later['crafted'].items() if v > before['crafted'].get(n, 0)}
                table = ResourceTable(**row['structured']['resource_table'])
                old_recipes = {n for n, r in table.recipes.items() if r.get('ingredients')}
                table.observe(row['next_observation'], row['executed_action'])
                new_recipes = sorted({n for n, r in table.recipes.items() if r.get('ingredients')}-old_recipes)
                released = any(c['native_released'] for c in conds)
                item['recovery'] = {**pending, 'conditions': conds,
                    'blocked_native_rejected_before': before_legality['semantic_rejection'],
                    'blocked_native_rejected_after': after_legality['semantic_rejection'],
                    'whole_action_released': before_legality['semantic_rejection'] and not after_legality['semantic_rejection'],
                    'selected_legal': not row['semantic_rejection'], 'resource_gain': gain, 'production': production,
                    'relevant_condition_release': released, 'physical_progress': bool(gain or production or released),
                    'information_gain': new_recipes, 'location_preparation': before['location'] != later['location'],
                    'stagnant': not (gain or production or released or new_recipes or before['location'] != later['location']),
                    'node_completed': row['executed_action'] == blocked and not row['semantic_rejection'],
                    'root_resumed': pending['retry_original'] and row['executed_action'] == blocked and not row['semantic_rejection'],
                    'retained_goal': row['structured']['target'] == case['target_action'],
                    'final_task_goal_this_step': row['diagnostic_goal_reached'],
                    'feedback': row['action_rule_feedback'], 'selected_action': row['executed_action']}
            effects.append(item)
            if row['stage7_state_before'].get('stage9'):
                alternate = restore_controller(row['stage7_state_before'])
                alternate.active_recovery = not alternate.active_recovery
                other = alternate.choose(row['observation'], row['proposed_action'])
                if other != selected:
                    actual_effect, alternate_effect = compact_branch(raw, selected, case), compact_branch(raw, other, case)
                else:
                    actual_effect = alternate_effect = None
                comparisons.append({'task_id': folder.name, 'case_id': case['id'], 'index': i,
                    'method': row.get('stage9_method'), 'same_proposal': row['proposed_action'],
                    'original_action': selected, 'toggled_action': other, 'changed': selected != other,
                    'original_effect': actual_effect, 'alternate_effect': alternate_effect,
                    'scope': 'one frozen predecision public state; only active_recovery toggled. Not whole-episode counterfactual.'})
    return {'task_id': folder.name, 'effects': effects, 'counterfactuals': comparisons, 'reproduction_errors': errors}


def main(runtime, workers=8, smoke=False):
    root = Path(runtime)
    if smoke:
        jobs = [(str(f), json.loads((f/'task.json').read_text())['task']) for f in sorted((root/'runs').iterdir())]
    else:
        cases = {c['id']: c for c in json.loads((OUT/'cases.json').read_text())}
        jobs = [(str(root/'runs'/t['task_id']), cases[t['id']]) for t in json.loads((root/'tasks.json').read_text())]
    n = b = d = changes = 0; errors = []; catalogs = {}
    assert all(case['game'] == 'robot_kingdom' for _, case in jobs)
    out = root/'smoke_analysis' if smoke else OUT
    out.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context('spawn')) as pool:
        with gzip.open(out/'resource_audit.jsonl.gz', 'wt') as rf, gzip.open(out/'batch_audit.jsonl.gz', 'wt') as bf:
            for record in pool.map(resource_audit, jobs):
                catalogs[record['case_id']] = record['catalog']
                for r in record['resource']: rf.write(json.dumps(r)+'\n'); n += 1
                for r in record['batches']: bf.write(json.dumps(r)+'\n'); b += 1
        with gzip.open(out/'condition_effects.jsonl.gz', 'wt') as ef, gzip.open(out/'decision_counterfactuals.jsonl.gz', 'wt') as cf:
            for record in pool.map(audit, jobs):
                errors.extend(record['reproduction_errors'])
                for r in record['effects']: ef.write(json.dumps(r, ensure_ascii=False)+'\n')
                for r in record['counterfactuals']: cf.write(json.dumps(r, ensure_ascii=False)+'\n'); d += 1; changes += r['changed']
    result = {'episodes': len(jobs), 'resource_actions': n, 'batch_states': b, 'same_state_toggles': d,
              'changed_choices': changes, 'reproduction_errors': errors, 'api_calls': 0, 'only_game': 'robot_kingdom', 'passed': not errors}
    atomic_json(out/'truth_catalog_evaluation_only.json', catalogs)
    atomic_json(out/'mechanism_audit_completion.json', result)
    if smoke: atomic_json(OUT/'analysis_smoke_checks.json', result)
    print(json.dumps(result)); assert not errors


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--runtime', required=True); p.add_argument('--workers', type=int, default=8); p.add_argument('--smoke', action='store_true')
    a = p.parse_args(); main(a.runtime, a.workers, a.smoke)
