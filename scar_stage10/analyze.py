"""Recompute paired outcomes and evidence for residual unknown-rule failures."""
import argparse
import collections
import csv
import gzip
import json
from pathlib import Path

from scar.io import atomic_json, digest
from scar_sequence.analyze import episode_metrics, aggregate, divide
from scar_unknown17.analyze import mechanism_metrics, grouped_extra
from scar_stage9.analyze import bootstrap
from scar_stage10.controller import METHODS, adapted
from scar_v3.state import parse_action

OUT = Path('results/stage10')


def extra(rows, case, effects, metrics):
    goal = case['goal']['name']; keys = {case['object_names'][x] for x in case['recipe_graph']}
    first, crafted = {}, {}
    streak = maximum = pairs = 0; seen = {}; repeats = []
    all_known_at = None; vetoes = []; collection = []; storage = []; context_repeats = []
    for row, effect in zip(rows, effects, strict=True):
        i = row['index']; p = parse_action(row['executed_action'])
        if row['executed_action'] == 'wait': streak += 1; maximum = max(maximum, streak); pairs += streak > 1
        else: streak = 0
        for name in effect['known_key_recipes']: first.setdefault(name, i)
        for name in effect['new_key_recipes']: first.setdefault(name, i+1)
        if keys <= set(first) and all_known_at is None: all_known_at = i+1
        if p.verb == 'craft' and not row['semantic_rejection']: crafted.setdefault(p.target, i+1)
        state = row['stage7_state_before']; ctrl = adapted(state, 'S1'); ctrl.table.observe(row['observation'])
        # Same public context definition for every method, including frozen S0.
        # Using S0's narrower legacy retry key would inflate its repeat counts.
        context = ctrl.context(row['executed_action'])
        key = digest([row['executed_action'], context])
        if key in seen:
            before, previous_failed = seen[key]
            if row['semantic_rejection'] and previous_failed:
                context_repeats.append({'index': i, 'previous_index': before, 'action': row['executed_action']})
            if not effect['public_new_recipe_names'] and not effect['resource_gain'] and not effect['condition_progress']:
                repeats.append({'index': i, 'previous_index': before, 'action': row['executed_action']})
        seen[key] = (i, row['semantic_rejection'])
        vetoes.extend(dict(v, index=i) for v in effect['vetoes'])
        meta = effect['resource_selection']
        if meta.get('kind') in {'bulk_collection', 'opportunistic_collection', 'opportunity_capacity_check'}:
            collection.append({'index': i, 'action': row['executed_action'], 'selection': meta,
                'legal': effect['resource_action_legal'], 'gain': effect['resource_gain'], 'feedback': row['action_rule_feedback']})
        if meta.get('kind') in {'stash', 'ground_stash', 'prepare_stash', 'stash_capacity_check', 'return_to_stash', 'reconfirm_stash', 'retrieve_stash'}:
            storage.append({'index': i, 'action': row['executed_action'], 'selection': meta,
                'legal': effect['resource_action_legal'], 'gain': effect['resource_gain'], 'events': effect['stash_events'],
                'feedback': row['action_rule_feedback']})
    conversion = [{'recipe': name, 'discovered_after_action': index, 'first_successful_craft': crafted.get(name),
                   'converted_after_discovery': name in crafted and crafted[name] >= index,
                   'already_crafted_before_discovery': name in crafted and crafted[name] < index,
                   'unexecuted': name not in crafted, 'remaining_observed_actions': max(0, len(rows)-index)}
                  for name, index in sorted(first.items())]
    missed = [{'index': e['index'], 'nodes': e['known_ready_nodes'], 'action': rows[e['index']]['executed_action'],
               'queue': e['current_queue'], 'feedback': rows[e['index']]['action_rule_feedback']}
              for e in effects if e['known_ready_nodes'] and not e['ready_executed']]
    update_evidence = []
    for e in effects:
        if not e['new_key_recipes']: continue
        later = effects[e['index']+1:e['index']+5]
        update_evidence.append({'discovery_index': e['index'], 'new_key_recipes': e['new_key_recipes'],
            'next_decisions': [{'index': n['index'], 'queue': n['current_queue'], 'action': rows[n['index']]['executed_action'],
                                'ready': n['known_ready_nodes'], 'recipe_gain': n['public_new_recipe_names']} for n in later],
            'interpretation': 'queue/action trace only; absence from FIFO is not itself proof of an invalid plan'})
    resource_failures = [{'index': r['index'], 'action': r['executed_action'], 'feedback': r['action_rule_feedback']}
                         for r in rows if r['semantic_rejection']]
    labels, evidence = [], {}
    if not metrics['recovery_at_40']:
        if metrics['missing_key_recipes']:
            labels.append('knowledge_discovery')
            evidence['knowledge_discovery'] = {'missing_key_recipes': metrics['missing_key_recipes'],
                'scope': 'undiscovered native recipe names on dependency graph; alternate obtainable-copy routes are not ruled out'}
        if missed or all_known_at is not None:
            labels.append('known_knowledge_not_converted_to_plan')
            evidence['known_knowledge_not_converted_to_plan'] = {
                'all_known_after_action': all_known_at, 'missed_ready_opportunities': missed,
                'unexecuted_known_recipes': [r for r in conversion if r['unexecuted']],
                'scope': 'observable execution gap; a locally ready recipe need not be globally optimal. Also inspect resource evidence.'}
        if resource_failures or metrics['resource_destruction_steps'] or metrics['harmful_target_quantity_overrides']:
            labels.append('material_or_action_execution')
            evidence['material_or_action_execution'] = {'native_rejections': resource_failures,
                'environment_losses': metrics['resource_destruction'],
                'harmful_base_quantity_override_indices': metrics['harmful_quantity_indices']}
        if not labels:
            labels.append('material_or_action_execution')
            evidence['material_or_action_execution'] = {'scope': 'goal incomplete without missing names; exact cause unresolved',
                'terminal_physical': rows[-1]['physical_after'] if rows else None}
    events = [v for e in effects for v in e['stash_events']]
    return {
        'actual_wait_actions': sum(r['executed_action'] == 'wait' for r in rows), 'consecutive_wait_pairs': pairs,
        'max_wait_streak': maximum, 'no_candidate_wait': sum(r['structured'].get('reason') == 'no_public_candidate' for r in rows),
        'same_context_failed_repeats': len(context_repeats), 'failed_repeat_records': context_repeats,
        'same_context_no_gain_repeats': len(repeats), 'no_gain_repeat_records': repeats,
        'condition_vetoes': len(vetoes), 'legal_action_vetoes': sum(not v['native_rejected'] for v in vetoes),
        'unknown_only_vetoes': sum(v['unknown_only'] for v in vetoes),
        'veto_to_legal_alternative': sum(v['selected_legal'] for v in vetoes),
        'overlay_changed_F0': sum(r['structured'].get('stage10', {}).get('overlay_changed_F0', False) for r in rows),
        'base_progress_preserved': sum(r['structured'].get('reason') == 'preserve_supported_base_progress' for r in rows),
        'collection_events': collection, 'collection_selections': len(collection),
        'collection_with_native_gain': sum(bool(e['gain']) for e in collection),
        'collection_rejections': sum(not e['legal'] for e in collection),
        'storage_actions': len(storage), 'storage_records': storage,
        'stash_recorded': sum(e['event'] == 'stash_recorded' for e in events),
        'stash_retrieved': sum(e['event'] == 'stash_retrieved' for e in events),
        'stash_missing': sum(e['event'] == 'stash_missing_on_reconfirmation' for e in events),
        'stash_memory_final': effects[-1]['stash_records_after'] if effects else {},
        'known_ready_opportunities': sum(bool(e['known_ready_nodes']) for e in effects),
        'known_ready_executed': sum(e['ready_executed'] for e in effects), 'known_ready_missed': len(missed),
        'missed_ready_records': missed, 'all_known_after_action': all_known_at,
        'all_known_but_failed': all_known_at is not None and not metrics['recovery_at_40'],
        'recipe_conversion_records': conversion,
        'discovered_recipe_count': len(conversion), 'discovered_then_crafted': sum(r['converted_after_discovery'] for r in conversion),
        'plan_updates_after_knowledge': update_evidence,
        'residual_categories': labels, 'residual_evidence': evidence,
    }


SUMS = ['actual_wait_actions', 'consecutive_wait_pairs', 'no_candidate_wait', 'same_context_failed_repeats',
        'same_context_no_gain_repeats', 'condition_vetoes', 'legal_action_vetoes', 'unknown_only_vetoes',
        'veto_to_legal_alternative', 'overlay_changed_F0', 'base_progress_preserved', 'collection_selections',
        'collection_with_native_gain', 'collection_rejections', 'storage_actions', 'stash_recorded', 'stash_retrieved',
        'stash_missing', 'known_ready_opportunities', 'known_ready_executed', 'known_ready_missed',
        'all_known_but_failed', 'discovered_recipe_count', 'discovered_then_crafted', 'method_abort', 'format_abort']


def main(runtime):
    root = Path(runtime); tasks = json.loads((root/'tasks.json').read_text())
    cases = {c['id']: c for c in json.loads((OUT/'cases.json').read_text())}
    groups = {name: collections.defaultdict(list) for name in ['resource_audit', 'batch_audit', 'decision_effects']}
    for name, group in groups.items():
        for r in map(json.loads, gzip.open(OUT/(name+'.jsonl.gz'), 'rt')): group[r['task_id']].append(r)
    catalogs = json.loads((OUT/'truth_catalog_evaluation_only.json').read_text())
    metrics, summaries, missing = [], [], []
    handles = {m: gzip.open(OUT/f'trajectories_{m}.jsonl.gz', 'wt') for m in METHODS}
    for task in tasks:
        folder = root/'runs'/task['task_id']; case = cases[task['id']]
        if not (folder/'summary.json').exists(): missing.append(task['task_id']); continue
        summary = json.loads((folder/'summary.json').read_text())
        if summary['status'] not in {'completed', 'method_abort'}: missing.append(task['task_id'])
        rows = [json.loads(p.read_text()) for p in sorted((folder/'steps').glob('*/transition.json'))]
        m = episode_metrics(summary, rows, case, groups['resource_audit'][task['task_id']])
        m.update(mechanism_metrics(case, rows, catalogs[case['id']], groups['batch_audit'][task['task_id']]))
        m.update(extra(rows, case, groups['decision_effects'][task['task_id']], m))
        m.update(task_id=task['task_id'], cohort='development_old10', method_abort=summary['status'] == 'method_abort',
                 format_abort='ModelResponseError' in (summary.get('error') or ''))
        metrics.append(m); summaries.append(summary)
        handles[task['algorithm']].write(json.dumps({'task_id': task['task_id'], 'case_id': case['id'], 'summary': m, 'rows': rows}, ensure_ascii=False)+'\n')
    for f in handles.values(): f.close()
    result = {}
    for method in METHODS:
        selected = [m for m in metrics if m['algorithm'] == method]
        totals = aggregate(selected) | grouped_extra(selected) | {k: sum(r[k] for r in selected) for k in SUMS}
        totals['maximum_wait_streak'] = max((r['max_wait_streak'] for r in selected), default=0)
        totals['discovery_to_craft_rate'] = divide(totals['discovered_then_crafted'], totals['discovered_recipe_count'])
        totals['residual_category_counts'] = dict(collections.Counter(k for m in selected for k in m['residual_categories']))
        result[method] = totals
    paired = []
    by = {(m['case_id'], m['algorithm']): m for m in metrics}
    for new, old in [('S1', 'S0'), ('S2', 'S1'), ('S3', 'S2'), ('S3', 'S0')]:
        rows = [{'case_id': cid, 'target': case['goal']['name'], 'old': by[cid, old]['recovery_at_40'],
                 'new': by[cid, new]['recovery_at_40'], 'difference': int(by[cid, new]['recovery_at_40'])-int(by[cid, old]['recovery_at_40'])}
                for cid, case in cases.items() if (cid, old) in by and (cid, new) in by]
        paired.append({'new': new, 'old': old, **bootstrap([r['difference'] for r in rows]),
                       'gained': [r for r in rows if r['difference'] == 1], 'lost': [r for r in rows if r['difference'] == -1], 'families': rows})
    counterfactuals = collections.defaultdict(lambda: collections.Counter()); examples = []
    for r in map(json.loads, gzip.open(OUT/'decision_counterfactuals.jsonl.gz', 'rt')):
        m = counterfactuals[r['method']]; m['decisions'] += 1; m['changed'] += r['changed']
        if r['changed']:
            original, alternate = r['original_effect'], r['alternate_effect']
            m['removing_module_legal_gain'] += original['rejected'] and not alternate['rejected']
            m['removing_module_legal_loss'] += alternate['rejected'] and not original['rejected']
            m['removing_module_goal_gain'] += alternate['goal'] and not original['goal']
            m['removing_module_goal_loss'] += original['goal'] and not alternate['goal']
            examples.append(r)
    atomic_json(OUT/'completion.json', {'expected': len(tasks), 'completed': len(metrics), 'incomplete': missing,
        'fully_complete': len(metrics) == len(tasks) and not missing, 'statuses': dict(collections.Counter(m['status'] for m in metrics))})
    for name, value in [('episode_metrics', metrics), ('all_summaries', summaries), ('method_metrics', result),
                        ('paired_comparisons', paired), ('counterfactual_summary', dict(counterfactuals)),
                        ('counterfactual_changed_decisions', examples)]: atomic_json(OUT/(name+'.json'), value)
    atomic_json(OUT/'family_comparison.json', {case['goal']['name']: {m: by[cid, m] for m in METHODS if (cid, m) in by} for cid, case in cases.items()})
    fields = ['method', 'n', 'successes', 'recovery_at_10', 'recovery_at_20', 'recovery_at_40', 'mean_success_steps', 'steps',
              'cost_usd', 'input_tokens', 'output_tokens', 'cost_per_success_all_attempts', 'tokens_per_success_all_attempts',
              'semantic_rejections', 'actual_wait_actions', 'maximum_wait_streak', 'key_discovery_rate', 'discovery_to_craft_rate',
              'all_known_but_failed', 'harmful_goal_overrides', 'resource_destruction_steps', 'storage_actions', 'method_abort']
    with (OUT/'comparison.csv').open('w') as f:
        writer = csv.DictWriter(f, fields, lineterminator='\n'); writer.writeheader()
        for method, value in result.items(): writer.writerow({k: (value | {'method': method}).get(k) for k in fields})
    print(json.dumps({'completed': len(metrics), 'successes': {m: r['successes'] for m, r in result.items()},
                      'cost_usd': sum(r['cost_usd'] for r in metrics)}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--runtime', required=True); a = p.parse_args(); main(a.runtime)
