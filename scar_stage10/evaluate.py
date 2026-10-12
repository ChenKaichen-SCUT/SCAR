"""Independent native effects after policy selection; no engine data to policy."""
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
from scar_stage10.controller import adapted, restore_controller
from scar_v3.state import parse_action

OUT = Path('results/stage10')


def audit(job):
    folder, case = job; folder = Path(folder)
    assert case['game'] == 'robot_kingdom' and case['cohort'] == 'development_old10'
    effects, comparisons, errors = [], [], []
    keys = {case['object_names'][oid] for oid in case['recipe_graph']}
    goal = case['goal']['name']
    with tempfile.TemporaryDirectory() as tmp, open('/dev/null', 'w') as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        paths = sorted((folder/'steps').glob('*/transition.json'))
        for i, path in enumerate(paths):
            row = json.loads(path.read_text())
            raw = (folder/'initial.pkl' if i == 0 else paths[i-1].parent/'environment.pkl').read_bytes()
            env = restore(raw, tmp)
            ctrl = restore_controller(row['stage7_state_before'])
            actual = ctrl.choose(row['observation'], row['proposed_action'])
            if actual != row['executed_action']: errors.append({'index': i, 'actual': row['executed_action'], 'reproduced': actual})
            selection = row['structured'].get('stage10', {})
            vetoes = []
            distinct = {v['action']: v for v in selection.get('conditions', []) if v['status'] == 'REJECT'}
            for action, assessment in distinct.items():
                native = score_candidate(env, action)
                conditions = []
                for condition in assessment['conditions']:
                    try: value = truth(env, condition, action)
                    except TypeError: value = None  # Immovable-object size is undefined.
                    conditions.append(dict(condition, native_truth=value))
                vetoes.append({'assessment': assessment, 'native_rejected': native['semantic_rejection'],
                    'feedback': native['feedback'], 'conditions': conditions,
                    'unknown_only': not any(c['status'] == 'REJECT' for c in conditions),
                    'selected_legal': not row['semantic_rejection']})
            t = ctrl.table; ready = []
            for name in sorted(keys):
                need = ctrl.amount if name == goal else ctrl.queue_needs.get(name, 1)
                if not t.recipes.get(name, {}).get('ingredients') or (t.count(name) or 0) >= need: continue
                native = score_candidate(env, 'craft 1 '+name)
                if not native['semantic_rejection']: ready.append(name)
            p = parse_action(actual)
            new = copy.deepcopy(t); before_known = {n for n, r in t.recipes.items() if r.get('ingredients')}
            new.observe(row['next_observation'], actual)
            gains = sorted({n for n, r in new.recipes.items() if r.get('ingredients')}-before_known)
            after_memory = json.loads((path.parent/'memory/unknown.json').read_text())['controller']
            prior_stash_events = len(row['stage7_state_before'].get('stash_events', []))
            metadata = selection.get('selected_meta') or {}
            effects.append({'task_id': folder.name, 'case_id': case['id'], 'index': i, 'method': row['stage10_method'],
                'vetoes': vetoes, 'known_ready_nodes': ready,
                'ready_executed': p.verb == 'craft' and p.target in ready and not row['semantic_rejection'],
                'public_new_recipe_names': gains, 'new_key_recipes': sorted(set(gains)&keys),
                'known_key_recipes': sorted(before_known&keys),
                'current_queue': row['structured'].get('queue', []),
                'stash_events': after_memory.get('stash_events', [])[prior_stash_events:],
                'stash_records_after': after_memory.get('stashes', {}),
                'resource_selection': metadata, 'resource_action_legal': not row['semantic_rejection'],
                'resource_gain': {n: v-row['physical_before']['accessible'].get(n, 0)
                    for n, v in row['physical_after']['accessible'].items() if v > row['physical_before']['accessible'].get(n, 0)},
                'selected_goal_progress': row['objective_metrics']['physical_goal_delta'] > 0,
                'condition_progress': row['objective_metrics']['conditions_released'] > 0})
            method = row['stage10_method']
            if method != 'S0':
                previous = {'S1': 'S0', 'S2': 'S1', 'S3': 'S2'}[method]
                if method == 'S1': other = adapted(row['stage7_state_before'], 'S0')
                else:
                    other = restore_controller(row['stage7_state_before'])
                    if method == 'S2': other.opportunistic = False
                    else: other.storage = False
                alternate = other.choose(row['observation'], row['proposed_action'])
                changed = actual != alternate
                comparisons.append({'task_id': folder.name, 'case_id': case['id'], 'index': i,
                    'method': method, 'toggled_to': previous, 'proposal': row['proposed_action'],
                    'original_action': actual, 'alternate_action': alternate, 'changed': changed,
                    'original_effect': compact_branch(raw, actual, case) if changed else None,
                    'alternate_effect': compact_branch(raw, alternate, case) if changed else None,
                    'scope': 'same recorded public controller state and proposal; disable adjacent module only; changed native branches replayed twice'})
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
