"""All family outcomes, all recovery chains and matched effects, including losses."""
import argparse
import collections
import csv
import gzip
import json
import statistics
from pathlib import Path

import numpy as np
from scar.io import atomic_json, digest
from scar_sequence.analyze import episode_metrics, aggregate, divide
from scar_stage9.controller import METHODS, restore_controller
from scar_v3.state import parse_action

OUT = Path('results/stage9')


def bootstrap(values):
    if not values: return {'difference': None, 'ci95': None, 'n': 0}
    a = np.asarray(values, dtype=float); rng = np.random.default_rng(314159)
    means = a[rng.integers(len(a), size=(10000, len(a)))].mean(axis=1)
    return {'difference': float(a.mean()), 'ci95': [float(x) for x in np.quantile(means, [.025, .975])],
            'n': len(a), 'warning': 'small developed sample; empirical interval is not generalization evidence'}


def extra(rows, case, effects, plans):
    waits = longest = pairs = 0; seen = {}; repeats = []; conditions = {}; false_unknown = 0
    vetoes = []; recovery = []; subgoals = {}; goals_lost = []; lower_veto = []
    state_bytes = []
    for r in rows:
        if r['executed_action'] == 'wait':
            waits += 1; longest = max(longest, waits); pairs += waits > 1
        else: waits = 0
        s = r['stage7_state_before']; ctrl = restore_controller(s); ctrl.table.observe(r['observation'])
        context = ctrl.action_context(r['executed_action']) if hasattr(ctrl, 'action_context') else ctrl.public_context(parse_action(r['executed_action']).target)
        key = digest([r['executed_action'], context])
        if r['semantic_rejection']:
            if key in seen: repeats.append({'index': r['index'], 'previous': seen[key], 'action': r['executed_action']})
            seen[key] = r['index']
        state_bytes.append(len(json.dumps(s, ensure_ascii=False).encode()))
        if r.get('structured', {}).get('target') != case['target_action']:
            goals_lost.append(r['index'])
        safety = r.get('structured', {}).get('safety', {})
        for block in safety.get('production_blocked', []):
            if parse_action(block['action']).target != case['goal']['name']:
                lower_veto.append({'index': r['index'], **block})
    for effect in effects:
        for v in effect['vetoes']:
            vetoes.append(v); false_unknown += v['unknown_only_veto']
        r = effect.get('recovery')
        if not r: continue
        r = dict(r, index=effect['index']); recovery.append(r)
        for c in r['conditions']:
            if c['status'] == 'SUPPORTED': continue
            key = digest([r['event_id'], r['node_action'], c['kind'], c.get('item'), c.get('container')])
            subgoals.setdefault(key, {'event_id': r['event_id'], 'node': r['node_action'], 'kind': c['kind'],
                'item': c.get('item'), 'container': c.get('container'), 'native_unsatisfied_seen': False,
                'physically_released': False, 'first_index': effect['index'], 'release_indices': []})
            node = subgoals[key]
            node['native_unsatisfied_seen'] |= c['native_before'] is False
            if c['native_released']:
                node['physically_released'] = True; node['release_indices'].append(effect['index'])
    by_kind = {}
    for kind in ['hands', 'materials', 'station', 'container_access', 'container_capacity', 'container_contents']:
        nodes = [r for r in subgoals.values() if r['kind'] == kind and r['native_unsatisfied_seen']]
        by_kind[kind] = {'blocked': len(nodes), 'released': sum(n['physically_released'] for n in nodes),
                        'rate': divide(sum(n['physically_released'] for n in nodes), len(nodes))}
    finish_chains = []
    for plan in plans:
        attempts = [r for r in recovery if r['event_id'] == plan['id']]
        root = [r for r in attempts if r['root_resumed']]
        end = root[-1]['index'] if root else None
        finish_chains.append({'event_id': plan['id'], 'origin': plan['origin'], 'blocked_action': plan['blocked_action'],
            'obstacle_types': plan['obstacle_types'], 'status': plan['status'], 'attempts': attempts,
            'root_resumed_index': end,
            'task_success_after_resume': end is not None and any(r['diagnostic_goal_reached'] for r in rows if r['index'] >= end),
            'native_condition_release': any(r['relevant_condition_release'] or r['whole_action_released'] for r in attempts),
            'public_record': plan, 'censored_at_episode_end': plan['status'] == 'active'})
    return {'actual_wait_actions': sum(r['executed_action'] == 'wait' for r in rows), 'consecutive_wait_pairs': pairs,
        'max_wait_streak': longest,
        'no_candidate_wait': sum(bool(r.get('structured', {}).get('stage9', {}).get('no_candidate') or
                                     r.get('structured', {}).get('safety', {}).get('no_candidate')) for r in rows),
        'same_context_failed_repeats': len(repeats), 'failed_repeat_records': repeats,
        'condition_vetoes': len(vetoes), 'vetoes_with_negative_evidence': sum(v['evidenced_negative_count'] > 0 for v in vetoes),
        'vetoes_with_native_false_condition': sum(v['native_false_condition_count'] > 0 for v in vetoes),
        'legal_action_vetoes': sum(not v['native_action_rejected'] for v in vetoes),
        'unknown_to_reject_without_negative_evidence': false_unknown,
        'veto_to_legal_alternative': sum(v['executed_alternative_legal'] for v in vetoes),
        'veto_to_immediate_goal_condition_progress': sum(v['executed_alternative_progress'] for v in vetoes),
        'recovery_events': len(plans), 'recovery_subgoals': len(subgoals),
        'native_unsatisfied_recovery_subgoals': sum(s['native_unsatisfied_seen'] for s in subgoals.values()),
        'native_completed_recovery_subgoals': sum(s['physically_released'] for s in subgoals.values()),
        'nested_recovery_nodes': sum(e.get('event') == 'gpar_subgoal_created' for r in rows for e in r.get('events', [])),
        'recovery_actions': len(recovery), 'legal_recovery_actions': sum(r['selected_legal'] for r in recovery),
        'physical_progress_recovery_actions': sum(r['physical_progress'] for r in recovery),
        'information_gain_recovery_actions': sum(bool(r['information_gain']) for r in recovery),
        'location_preparation_recovery_actions': sum(r['location_preparation'] for r in recovery),
        'stagnant_recovery_actions': sum(r['stagnant'] for r in recovery),
        'whole_action_releases': sum(r['whole_action_released'] for r in recovery),
        'successful_root_resumes': sum(r['root_resumed'] for r in recovery),
        'completed_stack_nodes': sum(r['node_completed'] for r in recovery),
        'goal_lost_steps': len(goals_lost), 'goal_lost_indices': goals_lost,
        'intermediate_demand_floor_vetoes': len(lower_veto), 'demand_floor_records': lower_veto,
        'obstacle_resolution': by_kind, 'recovery_subgoal_records': list(subgoals.values()),
        'recovery_chains': finish_chains,
        'completed_failure_to_goal_chains': sum(p['origin'] == 'real_feedback_failure' and p['task_success_after_resume'] and p['native_condition_release'] for p in finish_chains),
        'completed_veto_to_goal_chains': sum(p['origin'] == 'public_condition_veto' and p['task_success_after_resume'] and p['native_condition_release'] for p in finish_chains),
        'mean_controller_bytes': statistics.mean(state_bytes) if state_bytes else 0}


SUM_FIELDS = ['actual_wait_actions', 'consecutive_wait_pairs', 'no_candidate_wait', 'same_context_failed_repeats',
    'condition_vetoes', 'vetoes_with_negative_evidence', 'vetoes_with_native_false_condition', 'legal_action_vetoes',
    'unknown_to_reject_without_negative_evidence', 'veto_to_legal_alternative', 'veto_to_immediate_goal_condition_progress',
    'recovery_events', 'recovery_subgoals', 'native_unsatisfied_recovery_subgoals', 'native_completed_recovery_subgoals',
    'nested_recovery_nodes', 'recovery_actions', 'legal_recovery_actions', 'physical_progress_recovery_actions',
    'information_gain_recovery_actions', 'location_preparation_recovery_actions', 'stagnant_recovery_actions',
    'whole_action_releases', 'successful_root_resumes', 'completed_stack_nodes', 'goal_lost_steps',
    'intermediate_demand_floor_vetoes', 'completed_failure_to_goal_chains', 'completed_veto_to_goal_chains',
    'method_abort', 'format_abort', 'recursion_abort']


def group_extra(rows):
    result = {k: sum(r[k] for r in rows) for k in SUM_FIELDS}
    result['maximum_wait_streak'] = max((r['max_wait_streak'] for r in rows), default=0)
    result['alternative_legal_rate'] = divide(result['veto_to_legal_alternative'], result['condition_vetoes'])
    result['recovery_subgoal_release_rate'] = divide(result['native_completed_recovery_subgoals'], result['native_unsatisfied_recovery_subgoals'])
    result['obstacle_resolution'] = {}
    for k in ['hands', 'materials', 'station', 'container_access', 'container_capacity', 'container_contents']:
        blocked = sum(r['obstacle_resolution'][k]['blocked'] for r in rows)
        released = sum(r['obstacle_resolution'][k]['released'] for r in rows)
        result['obstacle_resolution'][k] = {'blocked': blocked, 'released': released, 'rate': divide(released, blocked)}
    return result


def main(runtime):
    root = Path(runtime); tasks = json.loads((root/'tasks.json').read_text())
    cases = {c['id']: c for c in json.loads((OUT/'cases.json').read_text())}
    resources, effects = collections.defaultdict(list), collections.defaultdict(list)
    for name, dest in [('resource_audit', resources), ('condition_effects', effects)]:
        for r in map(json.loads, gzip.open(OUT/(name+'.jsonl.gz'), 'rt')): dest[r['task_id']].append(r)
    metrics, summaries, missing = [], [], []
    handles = {m: gzip.open(OUT/f'trajectories_{m}.jsonl.gz', 'wt') for m in METHODS}
    for task in tasks:
        folder = root/'runs'/task['task_id']; path = folder/'summary.json'
        if not path.exists(): missing.append({'task_id': task['task_id'], 'status': 'missing'}); continue
        summary = json.loads(path.read_text())
        if summary['status'] not in {'completed', 'method_abort'}:
            missing.append({'task_id': task['task_id'], 'status': summary['status']}); continue
        case = cases[task['id']]
        paths = sorted((folder/'steps').glob('*/transition.json')); rows = [json.loads(p.read_text()) for p in paths]
        state = json.loads((paths[-1].parent/'memory/unknown.json').read_text())['controller'] if paths else {}
        m = episode_metrics(summary, rows, case, resources[task['task_id']])
        m.update(extra(rows, case, effects[task['task_id']], state.get('recovery_records', [])), cohort=case['cohort'],
                 task_id=task['task_id'], method_abort=summary['status'] == 'method_abort',
                 format_abort='ModelResponseError' in (summary.get('error') or ''),
                 recursion_abort='RecursionError' in (summary.get('error') or ''))
        handles[task['algorithm']].write(json.dumps({'task_id': task['task_id'], 'case_id': case['id'], 'summary': m, 'rows': rows}, ensure_ascii=False)+'\n')
        metrics.append(m); summaries.append(summary)
    for f in handles.values(): f.close()
    atomic_json(OUT/'completion.json', {'expected': len(tasks), 'completed': len(metrics), 'incomplete': missing,
        'fully_complete': len(metrics) == len(tasks) and not missing, 'statuses': dict(collections.Counter(m['status'] for m in metrics))})
    atomic_json(OUT/'episode_metrics.json', metrics); atomic_json(OUT/'all_summaries.json', summaries)
    scopes = {'all16_development': set(cases), **{s: {cid for cid, c in cases.items() if c['cohort'] == s} for s in ['development_old10', 'development_stage8_6']}}
    groups = {scope: {method: aggregate(rs) | group_extra(rs) for method in METHODS
        for rs in [[r for r in metrics if r['algorithm'] == method and r['case_id'] in ids]]} for scope, ids in scopes.items()}
    atomic_json(OUT/'method_metrics.json', groups)
    by = {m: {r['case_id']: r for r in metrics if r['algorithm'] == m} for m in METHODS}; paired = []
    for scope, ids0 in scopes.items():
        for a, b in [('F1', 'F-Old'), ('F2', 'F1'), ('F2', 'F0')]:
            ids = sorted(ids0 & by[a].keys() & by[b].keys())
            differences = [int(by[a][i]['recovery_at_40'])-int(by[b][i]['recovery_at_40']) for i in ids]
            paired.append({'scope': scope, 'a': a, 'b': b, 'success_difference': bootstrap(differences),
                'a_only': [i for i, d in zip(ids, differences) if d == 1], 'b_only': [i for i, d in zip(ids, differences) if d == -1],
                'cost_difference': bootstrap([by[a][i]['cost_usd']-by[b][i]['cost_usd'] for i in ids]),
                'wait_difference': bootstrap([by[a][i]['actual_wait_actions']-by[b][i]['actual_wait_actions'] for i in ids])})
    atomic_json(OUT/'paired_comparisons.json', paired)
    atomic_json(OUT/'family_comparison.json', [{'case_id': cid, 'target': c['goal']['name'], 'cohort': c['cohort'],
        'methods': {m: by[m].get(cid) for m in METHODS}} for cid, c in cases.items()])
    cfstats = collections.defaultdict(collections.Counter); examples = []
    for r in map(json.loads, gzip.open(OUT/'decision_counterfactuals.jsonl.gz', 'rt')):
        s = cfstats[r['method']]; s['states'] += 1; s['changed'] += r['changed']
        if not r['changed']: continue
        old, new = r['original_effect'], r['alternate_effect']
        s['alternate_legal_gain'] += old['rejected'] and not new['rejected']
        s['alternate_legal_loss'] += new['rejected'] and not old['rejected']
        s['alternate_goal_gain'] += new['goal'] and not old['goal']
        s['alternate_goal_loss'] += old['goal'] and not new['goal']
        examples.append(r)
    atomic_json(OUT/'counterfactual_summary.json', dict(cfstats))
    atomic_json(OUT/'counterfactual_changed_decisions.json', examples)
    fields = ['scope', 'method', 'n', 'successes', 'recovery_at_10', 'recovery_at_20', 'recovery_at_40', 'mean_success_steps',
              'steps', 'cost_usd', 'cost_per_success_all_attempts', 'tokens_per_success_all_attempts', 'semantic_rejections',
              'actual_wait_actions', 'maximum_wait_streak', 'recovery_events', 'recovery_actions',
              'native_completed_recovery_subgoals', 'successful_root_resumes', 'method_abort']
    with (OUT/'comparison.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fields, lineterminator='\n'); w.writeheader()
        for scope, methods in groups.items():
            for method, m in methods.items(): w.writerow({k: (m | {'scope': scope, 'method': method}).get(k) for k in fields})
    print(json.dumps({'episodes': len(metrics), 'complete': not missing, 'cost_usd': sum(r['cost_usd'] for r in metrics),
        'successes': {s: {m: v['successes'] for m, v in methods.items()} for s, methods in groups.items()}}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--runtime', required=True); a = p.parse_args(); main(a.runtime)
