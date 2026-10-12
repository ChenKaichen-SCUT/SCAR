"""Post-hoc interpretation, model accounting and bounded-plan checks, zero API."""
import collections
import gzip
import json
from pathlib import Path

from scar.io import atomic_json
from scar_stage9.controller import METHODS
from scar_unknown17.analyze import mechanism_metrics

OUT = Path('results/stage9')


def main():
    cases = {c['id']: c for c in json.loads((OUT/'cases.json').read_text())}
    catalogs = json.loads((OUT/'truth_catalog_evaluation_only.json').read_text())
    batch = collections.defaultdict(list); resources = collections.defaultdict(list)
    for r in map(json.loads, gzip.open(OUT/'batch_audit.jsonl.gz', 'rt')): batch[r['task_id']].append(r)
    for r in map(json.loads, gzip.open(OUT/'resource_audit.jsonl.gz', 'rt')): resources[r['task_id']].append(r)
    knowledge, bounds, models = [], [], {}
    for method in METHODS:
        requests = [r['request'] for r in map(json.loads, gzip.open(OUT/f'requests_{method}.jsonl.gz', 'rt'))]
        served = collections.Counter(); finishes = collections.Counter()
        for r in requests:
            raw = r.get('raw_response') or {}
            if isinstance(raw, str):
                try: raw = json.loads(raw)
                except ValueError: raw = {}
            served[raw.get('model') or 'UNKNOWN'] += 1
            for c in raw.get('choices', []): finishes[c.get('finish_reason')] += 1
        models[method] = {'requests': len(requests), 'requested_models': dict(collections.Counter(r['model'] for r in requests)),
            'served_models': dict(served), 'request_statuses': dict(collections.Counter(r['status'] for r in requests)),
            'finish_reasons': dict(finishes),
            **{k: sum((r.get('usage') or {}).get(k, 0) for r in requests) for k in
               ['prompt_tokens', 'completion_tokens', 'prompt_cache_hit_tokens', 'prompt_cache_miss_tokens']},
            'cost_usd': sum(r.get('cost_usd', 0) for r in requests), 'extra_planner_model_calls': 0}
        for ep in map(json.loads, gzip.open(OUT/f'trajectories_{method}.jsonl.gz', 'rt')):
            case = cases[ep['case_id']]; rows = ep['rows']
            k = mechanism_metrics(case, rows, catalogs[case['id']], batch[ep['task_id']])
            k.update(task_id=ep['task_id'], case_id=case['id'], method=method, target=case['goal']['name'],
                     terminal_public_recipe=rows[-1]['structured']['resource_table']['recipes'].get(case['goal']['name']),
                     terminal_physical=rows[-1]['physical_after'])
            knowledge.append(k)
            if method == 'F2':
                plans = [p['public_record'] for p in ep['summary']['recovery_chains']]
                bounds.append({'case_id': case['id'], 'events': len(plans),
                    'max_actual_recovery_actions': max((len(p['attempts']) for p in plans), default=0),
                    'max_recorded_stack_depth': max((len((r['structured']['stage9'].get('recovery') or {}).get('stack', [])) for r in rows), default=0),
                    'max_candidates': max(r['structured']['stage9']['candidate_checks'] for r in rows),
                    'max_same_context_rebuilds': max((max(r['stage7_state_before'].get('rebuilds', {}).values(), default=0) for r in rows), default=0),
                    'statuses': dict(collections.Counter(p['status'] for p in plans))})
    atomic_json(OUT/'knowledge_diagnostics.json', knowledge)
    atomic_json(OUT/'request_model_audit.json', models)
    passed = all(r['max_actual_recovery_actions'] <= 8 and r['max_recorded_stack_depth'] <= 4 and
                 r['max_candidates'] <= 48 and r['max_same_context_rebuilds'] <= 2 for r in bounds)
    atomic_json(OUT/'recovery_bound_audit.json', {'records': bounds, 'passed': passed, 'scope':
        'actual executed recovery actions, recorded nesting, candidate checks and unchanged-context plan rebuild counts; public recipe scans are linear, not counted as candidates'})
    assert passed
    grouped = {}
    for method in METHODS:
        ks = [r for r in knowledge if r['method'] == method]
        bs = [b for task, rr in batch.items() if '-'+method+'-' in task for b in rr]
        rr = [r for task, rs in resources.items() if '-'+method+'-' in task for r in rs]
        grouped[method] = {'key_recipes': sum(r['key_recipe_discovered'] for r in ks),
            'key_recipe_total': sum(r['key_recipe_total'] for r in ks),
            'episodes_missing_key_recipe_names': sum(bool(r['missing_key_recipes']) for r in ks),
            'locally_dominated_productive_batches': sum(bool(b['dominated_by']) and b['actual']['actual_output'] > 0 for b in bs),
            'productive_batches': sum(b['actual']['actual_output'] > 0 for b in bs),
            'environment_resource_loss_steps': sum(bool(r['environment_quantity_destruction']) for r in rr),
            'exact_environment_losses': dict(sum((collections.Counter(r['environment_quantity_destruction']) for r in rr), collections.Counter()))}
    atomic_json(OUT/'mechanistic_summary.json', grouped)
    atomic_json(OUT/'analysis_decisions.json', {
        'policy_changed_after_freeze': False, 'paid_reruns': 0,
        'veto_scope': 'all logged distinct rejected actions per decision, including internal filters; repeat checks deduplicated; frozen references have no tri-state log and zeros there mean uninstrumented',
        'unknown_reject_scope': 'structural test: a veto with no explicit REJECT evidence; zero does not prove complete knowledge or universally correct conservatism',
        'physical_subgoals': 'unique(event,node action,condition kind,item/container); count native False→True separately from selected-action legality and final success',
        'native_truth_limits': 'only directly mappable public hand/material/station/container conditions; loop/speculation guards have no physical truth label; native legality independently probed',
        'recovery_stagnation': 'no material/production/condition/information gain and no location change; location preparation is separate from actual physical advancement',
        'negative_counterfactuals': 'four post-hoc one-action substitutions with identical evaluator suffix; positive and negative branches retained, never added to autonomous successes',
        'offline_to_online_gap': 'midtrajectory critical states already retain materials/recipe disclosures; successful repair there is not initial-state closed-loop success',
        'bootstrap': '10000 paired family samples, seed314159; [0,0] from identical per-family binary outcomes does not prove population equivalence',
        'source_scope': 'all64 episodes and all new engine replays only Robot Kingdom;16 previously analyzed tasks, no independent generalization set'})
    atomic_json(OUT/'research_judgment.json', {'verdict': 'NO-GO', 'keep_reference': 'F0',
        'H1': 'mechanical defect repairs and fewer waits/rejections are supported locally; task-completion gain is not supported',
        'H2': 'GPAR has genuine condition-release/root-resume events but no extra successful families over F1',
        'Q1': 'partially: tri-state and production-veto defects fixed in tested states; future-demand handling remains incomplete in collection and minimum batch sizing',
        'Q2': 'waiting greatly reduced, not eliminated; F2 still has an8-action wait streak',
        'Q3': 'public material/station subgoals work on some states; hands/container mechanism proven only in targeted Robot gates, formal events do not establish those general effects',
        'Q4': '31 successful original-action resumes;3 real-failure chains precede task successes, all on families also solved by F1',
        'Q5': 'no extra F2 task completion:2/16 vs2/16 with identical success families',
        'Q6': 'no recursion or goal-field loss; F2 adds rejected actions and long waiting on some families, repeated exploration and resources losses remain',
        'Q7': 'most wait/rejection reduction occurs in F1; there is no demonstrated task-level improvement attributable to active planning',
        'remaining_defects': ['default-one collection exposes later-needed ground supplies to step-rule loss',
            'separate one-output fractional batches can exhaust a final-goal ingredient',
            'craft retry context includes location even for material failure, enabling unhelpful retries',
            'goal field retention and legal subgoals do not establish globally useful goal pursuit'],
        'decision': 'do not promote F1 orF2 overF0; retain diagnostic implementation and negative evidence, defer GPAR expansion and optional paid confirmation tasks'})
    print(json.dumps({'requests': sum(x['requests'] for x in models.values()), 'bound_audit': passed,
                      'verdict': 'NO-GO', 'knowledge': grouped}))


if __name__ == '__main__': main()
