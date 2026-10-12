"""Independent native effects and public-knowledge opportunities after selection."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import contextlib
import copy
import gzip
import json
import multiprocessing as mp
from pathlib import Path
import tempfile

from scar.environment import restore
from scar.diagnostics.scoring import score_candidate
from scar.io import atomic_json
from scar_sequence.public import ResourceTable
from scar_stage8.evaluate import audit_episode as resource_audit
from scar_stage9.evaluate import compact_branch, truth
from scar_stage11.controller import adapted, restore_controller
from scar_v3.state import parse_action

OUT = Path('results/stage11')


def gains(table, observation, action):
    new = copy.deepcopy(table)
    before = {n for n, r in table.recipes.items() if r.get('ingredients')}
    new.observe(observation, action)
    return sorted({n for n, r in new.recipes.items() if r.get('ingredients')}-before)


def useful_effect(effect, table, keys, public_nodes):
    p = parse_action(effect['action'])
    new = gains(table, effect['public_after'], effect['action'])
    resource = {n: v-effect['physical_before']['accessible'].get(n, 0)
                for n, v in effect['physical_after']['accessible'].items()
                if v > effect['physical_before']['accessible'].get(n, 0)}
    return {'new_public_recipes': new, 'new_key_recipes': sorted(set(new)&keys),
            'rejected': effect['rejected'], 'goal': effect['goal'], 'resource_gain': resource,
            'successful_key_production': p.verb == 'craft' and p.target in keys and not effect['rejected'],
            'public_necessary_action': p.target in public_nodes and p.verb in {'craft', 'pick up', 'store', 'take out'}}


def audit(job):
    folder, case = job; folder = Path(folder)
    assert case['game'] == 'robot_kingdom' and case['cohort'] == 'development_old10'
    effects, comparisons, errors = [], [], []
    keys = {case['object_names'][oid] for oid in case['recipe_graph']}
    relevant = {case['object_names'][oid] for oid in set(case['materials']) | set(case['products']) | set(case['recipe_graph'])}
    goal = case['goal']['name']
    with tempfile.TemporaryDirectory() as tmp, open('/dev/null', 'w') as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        paths = sorted((folder/'steps').glob('*/transition.json'))
        for i, path in enumerate(paths):
            row = json.loads(path.read_text())
            raw = (folder/'initial.pkl' if i == 0 else paths[i-1].parent/'environment.pkl').read_bytes()
            env = restore(raw, tmp); ctrl = restore_controller(row['stage7_state_before'])
            actual = ctrl.choose(row['observation'], row['proposed_action'])
            if actual != row['executed_action']: errors.append({'index': i, 'actual': row['executed_action'], 'reproduced': actual})
            observer = adapted(row['stage7_state_before'], 'E3'); observer.table.observe(row['observation'])
            view = observer.public_goal_view(); t = observer.table
            public_nodes = set(view['known_dependency_nodes']); p = parse_action(actual)
            known = {n for n, r in t.recipes.items() if r.get('ingredients')}
            new = gains(t, row['next_observation'], actual)
            vetoes = []
            conditions = row['structured'].get('stage10', {}).get('conditions', [])
            for action, assessment in {v['action']: v for v in conditions if v['status'] == 'REJECT'}.items():
                native = score_candidate(env, action); scoped = []
                for c in assessment['conditions']:
                    try: value = truth(env, c, action)
                    except TypeError: value = None
                    scoped.append(dict(c, native_truth=value))
                vetoes.append({'assessment': assessment, 'native_rejected': native['semantic_rejection'],
                    'feedback': native['feedback'], 'conditions': scoped,
                    'unknown_only': not any(c['status'] == 'REJECT' for c in scoped), 'selected_legal': not row['semantic_rejection']})
            # Legacy discovery/conversion audit, comparable with Stage10.
            ready = []
            for name in sorted(keys):
                need = observer.amount if name == goal else observer.queue_needs.get(name, 1)
                if not t.recipes.get(name, {}).get('ingredients') or (t.count(name) or 0) >= need: continue
                if not score_candidate(env, 'craft 1 '+name)['semantic_rejection']: ready.append(name)
            # New primary timely-opportunity audit: necessity must already be
            # publicly connected, and actual native ownership must be deficient.
            necessary = []
            native_access = row['physical_before']['accessible']
            for name, node in view['nodes'].items():
                if name not in relevant or native_access.get(name, 0) >= node['required_floor']: continue
                options = []
                if node['known_recipe']:
                    action = observer._batch_action('craft 1 '+name)
                    if not score_candidate(env, action)['semantic_rejection']:
                        options.append({'action': action, 'kind': 'production'})
                acquire = observer._acquire(name, node['required_floor'], public_nodes)
                if acquire and parse_action(acquire).verb in {'pick up', 'store', 'take out'}:
                    trial = compact_branch(raw, acquire, case)
                    if not trial['rejected'] and trial['physical_after']['accessible'].get(name, 0) > native_access.get(name, 0):
                        options.append({'action': acquire, 'kind': 'acquisition'})
                if options:
                    necessary.append({'name': name, 'public_state': node['status'], 'options': options,
                                      'required_floor': node['required_floor'], 'actual_owned': native_access.get(name, 0)})
            resource_gain = {n: v-native_access.get(n, 0) for n, v in row['physical_after']['accessible'].items() if v > native_access.get(n, 0)}
            executed_names = [n['name'] for n in necessary if p.target == n['name'] and not row['semantic_rejection'] and
                ((p.verb == 'craft' and any(o['kind'] == 'production' for o in n['options'])) or
                 (p.verb in {'store', 'take out', 'pick up'} and p.target in resource_gain))]
            selection = row['structured'].get('stage11', {}); selected = selection.get('selected') or {}
            exploration = p.verb == 'inspect' or (p.verb == 'craft' and p.target not in public_nodes) or selected.get('kind') == 'known_forward_bridge'
            current_effect = {'action': actual, 'public_after': row['next_observation'], 'physical_before': row['physical_before'],
                'physical_after': row['physical_after'], 'rejected': row['semantic_rejection'], 'goal': row['diagnostic_goal_reached']}
            original_effect = None
            if row['proposed_action'] != actual:
                original_effect = compact_branch(raw, row['proposed_action'], case)
            base = useful_effect(original_effect or current_effect, t, keys, public_nodes)
            effects.append({'task_id': folder.name, 'case_id': case['id'], 'index': i, 'method': row['stage11_method'],
                'vetoes': vetoes, 'known_ready_nodes': ready, 'ready_executed': p.verb == 'craft' and p.target in ready and not row['semantic_rejection'],
                'public_new_recipe_names': new, 'new_key_recipes': sorted(set(new)&keys), 'known_key_recipes': sorted(known&keys),
                'current_queue': row['structured'].get('queue', []), 'stash_events': [], 'stash_records_after': {}, 'resource_selection': {},
                'resource_action_legal': not row['semantic_rejection'], 'resource_gain': resource_gain,
                'selected_goal_progress': row['objective_metrics']['physical_goal_delta'] > 0,
                'condition_progress': row['objective_metrics']['conditions_released'] > 0,
                'public_goal_view': view, 'public_confirmed_nodes': sorted(public_nodes),
                'necessary_native_opportunities': necessary, 'necessary_executed_now': executed_names,
                'exploration': exploration, 'exploration_public_confirmed': exploration and p.target in public_nodes,
                'exploration_possible_bridge': exploration and p.target not in public_nodes and
                    ((p.verb == 'craft' and p.target in known) or
                     (p.verb == 'inspect' and p.target in observer.quantity_facts.produced)),
                'exploration_native_relevant_subject': exploration and p.target in relevant,
                'known_product_already_inspected': p.target in t.inspected,
                'base_effect': base, 'base_counterfactual': original_effect,
                'base_same_as_selected': row['proposed_action'] == actual,
                'explicit_priority_selected': bool(selected), 'selected_metadata': selected})
            method = row['stage11_method']
            targets = ['E0'] if method in {'E2', 'E3'} else ['E0', 'E2', 'E3'] if method == 'E4' else []
            for other_method in targets:
                other = adapted(row['stage7_state_before'], other_method)
                alternate = other.choose(row['observation'], row['proposed_action']); changed = actual != alternate
                original = compact_branch(raw, actual, case) if changed else None
                alternate_result = compact_branch(raw, alternate, case) if changed else None
                comparisons.append({'task_id': folder.name, 'case_id': case['id'], 'index': i, 'method': method,
                    'toggled_to': other_method, 'proposal': row['proposed_action'], 'original_action': actual,
                    'alternate_action': alternate, 'changed': changed,
                    'original_effect': original, 'alternate_effect': alternate_result,
                    'original_knowledge': useful_effect(original, t, keys, public_nodes) if changed else None,
                    'alternate_knowledge': useful_effect(alternate_result, t, keys, public_nodes) if changed else None,
                    'scope': 'same public state/proposal with named priority switches; changed physical branches twice; local effect only'})
    return {'task_id': folder.name, 'effects': effects, 'comparisons': comparisons, 'errors': errors}


def main(runtime, workers=8, smoke=False):
    root = Path(runtime)
    if smoke:
        jobs = [(str(f), json.loads((f/'task.json').read_text())['task']) for f in sorted((root/'runs').iterdir())]
    else:
        cases = {c['id']: c for c in json.loads((OUT/'cases.json').read_text())}
        jobs = [(str(root/'runs'/t['task_id']), cases[t['id']]) for t in json.loads((root/'tasks.json').read_text())]
    assert all(c['game'] == 'robot_kingdom' and c['cohort'] == 'development_old10' for _, c in jobs)
    out = root/'analysis_smoke' if smoke else OUT; out.mkdir(parents=True, exist_ok=True)
    counts = dict(episodes=len(jobs), actions=0, craft_states=0, paired_decisions=0, changed=0)
    errors, catalogs = [], {}
    with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context('spawn')) as pool:
        with gzip.open(out/'resource_audit.jsonl.gz', 'wt') as rf, gzip.open(out/'batch_audit.jsonl.gz', 'wt') as bf:
            for record in pool.map(resource_audit, jobs):
                catalogs[record['case_id']] = record['catalog']
                for r in record['resource']: rf.write(json.dumps(r)+'\n'); counts['actions'] += 1
                for r in record['batches']: bf.write(json.dumps(r)+'\n'); counts['craft_states'] += 1
        with gzip.open(out/'decision_effects.jsonl.gz', 'wt') as ef, gzip.open(out/'decision_counterfactuals.jsonl.gz', 'wt') as cf:
            for record in pool.map(audit, jobs):
                errors.extend(record['errors'])
                for r in record['effects']: ef.write(json.dumps(r, ensure_ascii=False)+'\n')
                for r in record['comparisons']:
                    cf.write(json.dumps(r, ensure_ascii=False)+'\n'); counts['paired_decisions'] += 1; counts['changed'] += r['changed']
    atomic_json(out/'truth_catalog_evaluation_only.json', catalogs)
    result = dict(counts, errors=errors, api_calls=0, only_game='robot_kingdom', passed=not errors)
    atomic_json(out/'mechanism_audit_completion.json', result)
    if smoke: atomic_json(OUT/'analysis_smoke_checks.json', result)
    print(json.dumps(result)); assert result['passed']


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--runtime', required=True); p.add_argument('--workers', type=int, default=8); p.add_argument('--smoke', action='store_true')
    a = p.parse_args(); main(a.runtime, a.workers, a.smoke)
