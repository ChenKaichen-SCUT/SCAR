"""Frozen-protocol task, discovery, execution and prompt-comparator statistics."""
import argparse
import collections
import csv
import gzip
import json
from pathlib import Path

from scar.io import atomic_json
from scar_sequence.analyze import episode_metrics, aggregate, divide
from scar_unknown17.analyze import mechanism_metrics, grouped_extra
from scar_stage9.analyze import bootstrap
from scar_stage10.analyze import extra as reliability_extra, SUMS as RELIABILITY_SUMS
from scar_stage11.controller import METHODS
from scar_v3.state import parse_action

OUT = Path('results/stage11')
COMPARISONS = [('E1','E0'), ('E2','E0'), ('E3','E0'), ('E4','E0'), ('E4','E2'), ('E4','E3'), ('E2','E1'), ('E4','E1')]


def workflow_metrics(rows, effects, case):
    timely = []; products = []; first_produced = set(); discovered = {}; crafted = {}
    for i, (row, effect) in enumerate(zip(rows, effects, strict=True)):
        p = parse_action(row['executed_action'])
        for n in effect['known_key_recipes']: discovered.setdefault(n, i-1)
        for n in effect['new_key_recipes']: discovered.setdefault(n, i)
        if p.verb == 'craft' and not row['semantic_rejection']:
            crafted.setdefault(p.target, i)
        necessary = {o['name'] for o in effect['necessary_native_opportunities']}
        if necessary:
            hits = []
            for j in range(i, min(len(rows), i+3)):
                selected = parse_action(rows[j]['executed_action'])
                if selected.target in necessary and not rows[j]['semantic_rejection'] and (
                    selected.verb == 'craft' or (selected.verb in {'store','take out','pick up'} and selected.target in effects[j]['resource_gain'])):
                    hits.append(j)
            timely.append({'index': i, 'opportunities': effect['necessary_native_opportunities'],
                'actual': row['executed_action'], 'executed_now': bool(effect['necessary_executed_now']),
                'executed_within3': bool(hits), 'first_execution_index': min(hits) if hits else None,
                'right_censored': not hits and i+3 > len(rows),
                'scope': 'locally feasible public necessity; later state changes may remove demand, not globally optimality proof'})
        if p.verb == 'craft' and 'successfully crafted' in row['action_rule_feedback'] and p.target != case['goal']['name'] and p.target not in first_produced:
            first_produced.add(p.target)
            inspections = [j for j in range(i+1, len(rows)) if parse_action(rows[j]['executed_action']).verb == 'inspect'
                           and parse_action(rows[j]['executed_action']).target == p.target and not rows[j]['semantic_rejection']]
            first = min(inspections) if inspections else None
            products.append({'product': p.target, 'production_index': i, 'first_inspection_index': first,
                'previously_inspected': effect['known_product_already_inspected'],
                'inspected_within3': first is not None and first-i <= 3,
                'right_censored': first is None and i+3 >= len(rows),
                'lag': first-i if first is not None else None,
                'new_recipes_at_inspection': effects[first]['public_new_recipe_names'] if first is not None else [],
                'new_key_recipes_at_inspection': effects[first]['new_key_recipes'] if first is not None else []})
    fresh = [r for r in products if not r['previously_inspected']]
    inspect_evaluable = [r for r in fresh if not r['right_censored']]
    timely_evaluable = [r for r in timely if not r['right_censored']]
    delays = [{'recipe': name, 'discovery_index': i, 'first_craft_index': crafted.get(name),
               'lag': crafted[name]-i if name in crafted and crafted[name] >= i else None,
               'unconverted': name not in crafted} for name, i in sorted(discovered.items())]
    lag_values = [r['lag'] for r in delays if r['lag'] is not None]
    related = [e for e in effects if e['exploration'] and (e['exploration_public_confirmed'] or e['exploration_possible_bridge'])]
    good_base = [e for e in effects if not e['base_effect']['rejected'] and
                 (e['base_effect']['goal'] or e['base_effect']['new_key_recipes'] or e['base_effect']['successful_key_production'] or
                  (e['base_effect']['public_necessary_action'] and e['base_effect']['resource_gain']))]
    return {'timely_records': timely, 'new_product_inspections': products, 'discovery_execution_delays': delays,
        'necessary_feasible_states': len(timely), 'necessary_executed_now': sum(r['executed_now'] for r in timely),
        'necessary_executed_within3': sum(r['executed_within3'] for r in timely_evaluable),
        'necessary_within3_evaluable': len(timely_evaluable), 'necessary_within3_censored': len(timely)-len(timely_evaluable),
        'new_intermediate_types': len(products), 'new_uninspected_intermediate_types': len(fresh),
        'new_intermediate_inspected_within3': sum(r['inspected_within3'] for r in inspect_evaluable),
        'new_intermediate_inspection_evaluable': len(inspect_evaluable), 'new_intermediate_inspection_censored': len(fresh)-len(inspect_evaluable),
        'discovery_execution_lag_sum': sum(lag_values), 'discovery_execution_lag_n': len(lag_values),
        'exploration_actions': sum(e['exploration'] for e in effects),
        'exploration_without_public_goal_connection': sum(e['exploration'] and not e['exploration_public_confirmed'] for e in effects),
        'exploration_native_nonrelevant_subject': sum(e['exploration'] and not e['exploration_native_relevant_subject'] for e in effects),
        'public_related_exploration_actions': len(related),
        'public_related_exploration_new_rules': sum(len(e['public_new_recipe_names']) for e in related),
        'public_related_exploration_new_key_rules': sum(len(e['new_key_recipes']) for e in related),
        'base_native_useful_proposals': len(good_base), 'base_useful_proposals_preserved': sum(e['base_same_as_selected'] for e in good_base),
        'base_useful_proposals_overridden': sum(not e['base_same_as_selected'] for e in good_base),
        'base_public_necessary_proposals': sum(e['base_effect']['public_necessary_action'] for e in effects),
        'explicit_priority_selections': sum(e['explicit_priority_selected'] for e in effects),
        'public_deaths': sum('I have died.' in r['next_observation']['text'] for r in rows),
        'public_curse_warning_steps': sum('invites corruption' in r['next_observation']['text'] for r in rows)}


def main(runtime, smoke=False):
    global OUT
    original_out = OUT
    root = Path(runtime)
    cases = {c['id']: c for c in json.loads((OUT/'cases.json').read_text())}
    if smoke:
        tasks = [json.loads((f/'task.json').read_text())['task'] for f in sorted((root/'runs').iterdir())]
        OUT = root/'analysis_smoke'
    else:
        tasks = json.loads((root/'tasks.json').read_text())
    groups = {name: collections.defaultdict(list) for name in ['resource_audit', 'batch_audit', 'decision_effects']}
    for name, group in groups.items():
        for r in map(json.loads, gzip.open(OUT/(name+'.jsonl.gz'), 'rt')): group[r['task_id']].append(r)
    catalogs = json.loads((OUT/'truth_catalog_evaluation_only.json').read_text())
    metrics, summaries, missing = [], [], []
    handles = {m: gzip.open(OUT/f'trajectories_{m}.jsonl.gz', 'wt') for m in METHODS}
    workflow_keys = []
    for task in tasks:
        folder = root/'runs'/task['task_id']; case = cases[task['id']]
        if not (folder/'summary.json').exists(): missing.append(task['task_id']); continue
        summary = json.loads((folder/'summary.json').read_text())
        if summary['status'] not in {'completed', 'method_abort', 'completed_budget', 'failed', 'worker_failed'}: missing.append(task['task_id'])
        rows = [json.loads(p.read_text()) for p in sorted((folder/'steps').glob('*/transition.json'))]
        effect = groups['decision_effects'][task['task_id']]
        m = episode_metrics(summary, rows, case, groups['resource_audit'][task['task_id']])
        m.update(mechanism_metrics(case, rows, catalogs[case['id']], groups['batch_audit'][task['task_id']]))
        m.update(reliability_extra(rows, case, effect, m)); workflow = workflow_metrics(rows, effect, case); m.update(workflow)
        workflow_keys = [k for k, v in workflow.items() if isinstance(v, (int, float))]
        m.update(task_id=task['task_id'], cohort='development_old10', method_abort=summary['status'] == 'method_abort',
                 format_abort='ModelResponseError' in (summary.get('error') or ''))
        metrics.append(m); summaries.append(summary)
        handles[task['algorithm']].write(json.dumps({'task_id': task['task_id'], 'case_id': case['id'], 'summary': m, 'rows': rows}, ensure_ascii=False)+'\n')
    for f in handles.values(): f.close()
    result = {}
    for method in METHODS:
        selected = [m for m in metrics if m['algorithm'] == method]
        totals = aggregate(selected) | grouped_extra(selected) | {k: sum(r[k] for r in selected) for k in RELIABILITY_SUMS+workflow_keys}
        totals['maximum_wait_streak'] = max((r['max_wait_streak'] for r in selected), default=0)
        totals['discovery_to_craft_rate'] = divide(totals['discovered_then_crafted'], totals['discovered_recipe_count'])
        for name, num, den in [('timely_execution_rate', 'necessary_executed_now', 'necessary_feasible_states'),
                               ('timely_within3_rate', 'necessary_executed_within3', 'necessary_within3_evaluable'),
                               ('fresh_product_inspection_within3_rate', 'new_intermediate_inspected_within3', 'new_intermediate_inspection_evaluable'),
                               ('mean_discovery_execution_lag', 'discovery_execution_lag_sum', 'discovery_execution_lag_n')]:
            totals[name] = divide(totals[num], totals[den])
        totals['residual_category_counts'] = dict(collections.Counter(k for m in selected for k in m['residual_categories']))
        result[method] = totals
    paired = []; by = {(m['case_id'], m['algorithm']): m for m in metrics}
    for new, old in COMPARISONS:
        rows = [{'case_id': cid, 'target': case['goal']['name'], 'old': by[cid, old]['recovery_at_40'],
                 'new': by[cid, new]['recovery_at_40'], 'difference': int(by[cid, new]['recovery_at_40'])-int(by[cid, old]['recovery_at_40'])}
                for cid, case in cases.items() if (cid, old) in by and (cid, new) in by]
        paired.append({'new': new, 'old': old, **bootstrap([r['difference'] for r in rows]),
                       'gained': [r for r in rows if r['difference'] == 1], 'lost': [r for r in rows if r['difference'] == -1], 'families': rows})
    counterfactuals = collections.defaultdict(collections.Counter); examples = []
    for r in map(json.loads, gzip.open(OUT/'decision_counterfactuals.jsonl.gz', 'rt')):
        m = counterfactuals[r['method']+'->'+r['toggled_to']]; m['decisions'] += 1; m['changed'] += r['changed']
        if r['changed']:
            original, alternate = r['original_effect'], r['alternate_effect']
            m['removing_module_legal_gain'] += original['rejected'] and not alternate['rejected']
            m['removing_module_legal_loss'] += alternate['rejected'] and not original['rejected']
            m['removing_module_goal_gain'] += alternate['goal'] and not original['goal']
            m['removing_module_goal_loss'] += original['goal'] and not alternate['goal']
            m['module_on_more_new_key_rules'] += len(r['original_knowledge']['new_key_recipes']) > len(r['alternate_knowledge']['new_key_recipes'])
            m['module_on_fewer_new_key_rules'] += len(r['original_knowledge']['new_key_recipes']) < len(r['alternate_knowledge']['new_key_recipes'])
            examples.append(r)
    atomic_json(OUT/'completion.json', {'expected': len(tasks), 'completed': len(metrics), 'incomplete': missing,
        'fully_complete': len(metrics) == len(tasks) and not missing, 'statuses': dict(collections.Counter(m['status'] for m in metrics))})
    for name, value in [('episode_metrics', metrics), ('all_summaries', summaries), ('method_metrics', result),
                        ('paired_comparisons', paired), ('counterfactual_summary', dict(counterfactuals))]: atomic_json(OUT/(name+'.json'), value)
    with gzip.open(OUT/'counterfactual_changed_decisions.jsonl.gz', 'wt') as f:
        for r in examples: f.write(json.dumps(r, ensure_ascii=False)+'\n')
    atomic_json(OUT/'family_comparison.json', {case['goal']['name']: {m: by[cid, m] for m in METHODS if (cid, m) in by} for cid, case in cases.items()})
    fields = ['method', 'n', 'successes', 'recovery_at_10', 'recovery_at_20', 'recovery_at_40', 'mean_success_steps', 'steps',
              'cost_usd', 'input_tokens', 'output_tokens', 'semantic_rejections', 'actual_wait_actions', 'maximum_wait_streak',
              'key_discovery_rate', 'discovery_to_craft_rate', 'timely_execution_rate', 'timely_within3_rate',
              'fresh_product_inspection_within3_rate', 'mean_discovery_execution_lag', 'all_known_but_failed',
              'harmful_goal_overrides', 'resource_destruction_steps', 'public_deaths', 'method_abort']
    with (OUT/'comparison.csv').open('w') as f:
        writer = csv.DictWriter(f, fields, lineterminator='\n'); writer.writeheader()
        for method, value in result.items(): writer.writerow({k: (value | {'method': method}).get(k) for k in fields})
    print(json.dumps({'completed': len(metrics), 'successes': {m: r['successes'] for m, r in result.items()},
                      'cost_usd': sum(r['cost_usd'] for r in metrics)}))
    if smoke:
        gate = json.loads((original_out/'analysis_smoke_checks.json').read_text())
        gate['statistics_smoke_passed'] = len(metrics) == 5 and not missing and sum(m['api_calls'] for m in metrics) == 0
        gate['passed'] = gate['passed'] and gate['statistics_smoke_passed']
        atomic_json(original_out/'analysis_smoke_checks.json', gate)
        assert gate['passed']


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--runtime', required=True); p.add_argument('--smoke', action='store_true'); a = p.parse_args(); main(a.runtime, a.smoke)
