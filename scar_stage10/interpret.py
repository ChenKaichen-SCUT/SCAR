"""Original-run accounting and scope audit; does not change frozen policies."""
import argparse
import collections
import contextlib
import gzip
import json
from pathlib import Path
import tempfile

from scar.io import atomic_json
from scar_stage10.controller import METHODS

OUT = Path('results/stage10')


def capacity_audit(runtime):
    from scar.environment import restore, AGENT_ID
    root = Path(runtime); records = []
    for task in json.loads((root/'tasks.json').read_text()):
        assert task['game'] == 'robot_kingdom' and task['cohort'] == 'development_old10'
        folder = root/'runs'/task['task_id']; paths = sorted((folder/'steps').glob('*/transition.json'))
        with tempfile.TemporaryDirectory() as tmp, open('/dev/null', 'w') as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            for i, path in enumerate(paths):
                env = restore(folder/'initial.pkl' if i == 0 else paths[i-1].parent/'environment.pkl', tmp)
                agent, world = env.agents[0], env.world
                inv = agent.inventory.container
                load = inv.current_load(world.objects) if inv else None
                area = world.area_instances[env.curr_agents_state['area'][AGENT_ID]]
                carried_containers = set(agent.items_in_hands) | set(agent.equipped_items_in_limb)
                if inv:
                    carried_containers.add(inv.id)
                external = [world.container_instances[oid].name for oid, amount in area.objects.items()
                            if amount > 0 and oid in world.container_instances and oid not in carried_containers]
                records.append({'task_id': task['task_id'], 'method': task['algorithm'], 'index': i,
                    'inventory_load': load, 'inventory_capacity': agent.inventory.capacity if inv else None,
                    'inventory_full': bool(inv and load >= agent.inventory.capacity),
                    'hands_full': sum(agent.items_in_hands.values()) >= 2,
                    'external_accessible_containers': external})
    with gzip.open(OUT/'capacity_states.jsonl.gz', 'wt') as f:
        for record in records: f.write(json.dumps(record)+'\n')
    result = {}
    for method in METHODS:
        rr = [r for r in records if r['method'] == method]
        result[method] = {'states': len(rr), 'full_inventory_states': sum(r['inventory_full'] for r in rr),
            'full_hands_states': sum(r['hands_full'] for r in rr),
            'with_external_container_states': sum(bool(r['external_accessible_containers']) for r in rr),
            'maximum_inventory_load': max((r['inventory_load'] for r in rr if r['inventory_load'] is not None), default=None),
            'capacities': sorted({r['inventory_capacity'] for r in rr if r['inventory_capacity'] is not None})}
    atomic_json(OUT/'capacity_coverage.json', result)


def main(runtime=None):
    if runtime: capacity_audit(runtime)
    models = {}; bounds = []; risks = []
    for method in METHODS:
        requests = [x['request'] for x in map(json.loads, gzip.open(OUT/f'requests_{method}.jsonl.gz', 'rt'))]
        served, finish = collections.Counter(), collections.Counter()
        for request in requests:
            raw = request.get('raw_response') or {}
            if isinstance(raw, str):
                try: raw = json.loads(raw)
                except ValueError: raw = {}
            served[raw.get('model', 'UNKNOWN')] += 1
            for c in raw.get('choices', []): finish[c.get('finish_reason')] += 1
        models[method] = {'requests': len(requests), 'requested_models': dict(collections.Counter(r['model'] for r in requests)),
            'served_models': dict(served), 'request_statuses': dict(collections.Counter(r['status'] for r in requests)),
            'finish_reasons': dict(finish), 'cost_usd': sum(r.get('cost_usd', 0) for r in requests),
            **{k: sum((r.get('usage') or {}).get(k, 0) for r in requests)
               for k in ['prompt_tokens', 'completion_tokens', 'prompt_cache_hit_tokens', 'prompt_cache_miss_tokens']},
            'extra_planner_calls': 0}
        for ep in map(json.loads, gzip.open(OUT/f'trajectories_{method}.jsonl.gz', 'rt')):
            risks.append({'task_id': ep['task_id'], 'case_id': ep['case_id'], 'method': method,
                'death_events': [{'index': r['index'], 'action': r['executed_action'],
                                  'public_feedback': r['next_observation']['text']}
                                 for r in ep['rows'] if 'I have died.' in r['next_observation']['text']],
                'public_curse_warning_steps': sum('invites corruption' in r['next_observation']['text'] for r in ep['rows'])})
            states = [r['stage7_state_before'] for r in ep['rows']]
            maximum_checks = max((len(r['structured'].get('stage10', {}).get('conditions', [])) for r in ep['rows']), default=0)
            extra_collection = sum((r['structured'].get('stage10', {}).get('selected_meta') or {}).get('kind')
                                   in {'opportunistic_collection', 'opportunity_capacity_check'} for r in ep['rows'])
            stash_actions = sum((r['structured'].get('stage10', {}).get('selected_meta') or {}).get('kind')
                                in {'stash', 'ground_stash', 'prepare_stash'} for r in ep['rows'])
            bounds.append({'task_id': ep['task_id'], 'max_candidate_checks': maximum_checks,
                'extra_opportunity_actions': extra_collection, 'stash_transfer_actions': stash_actions,
                'GPAR_stack_present': any('recovery' in s for s in states),
                'passed': maximum_checks <= 32 and extra_collection <= 6 and stash_actions <= 4
                          and all('recovery' not in s for s in states)})
    comparisons = collections.defaultdict(collections.Counter)
    for r in map(json.loads, gzip.open(OUT/'decision_counterfactuals.jsonl.gz', 'rt')):
        if not r['changed']: continue
        actual, alternate = r['original_effect']['physical_after']['accessible'], r['alternate_effect']['physical_after']['accessible']
        names = set(actual) | set(alternate)
        comparisons[r['method']]['module_on_more_relevant_units'] += any(actual.get(n, 0) > alternate.get(n, 0) for n in names)
        comparisons[r['method']]['module_on_fewer_relevant_units'] += any(actual.get(n, 0) < alternate.get(n, 0) for n in names)
    atomic_json(OUT/'request_model_audit.json', models)
    atomic_json(OUT/'bounds_audit.json', {'records': bounds, 'passed': all(r['passed'] for r in bounds)})
    atomic_json(OUT/'counterfactual_resource_summary.json', dict(comparisons))
    atomic_json(OUT/'public_risk_audit.json', {'records': risks,
        'summary': {m: {'death_events': sum(len(r['death_events']) for r in risks if r['method'] == m),
                        'episodes_with_death': sum(bool(r['death_events']) for r in risks if r['method'] == m),
                        'curse_warning_steps': sum(r['public_curse_warning_steps'] for r in risks if r['method'] == m)} for m in METHODS},
        'scope': 'actual public events; resource preservation is not equivalent to health safety or task progress; no isolated causal attribution'})
    atomic_json(OUT/'analysis_decisions.json', {
        'policy_changed_after_freeze': False, 'paid_reruns': 0,
        'scope': 'original10 Robot families only; no Stage8six, new task family, independent test set or other engine',
        'repeat_context': 'same ResourceController public action-context calculation applied to ALL methods for evaluator counts',
        'known_recipe': 'public ingredient names, not complete quantitative rules',
        'ready_nodes': 'independently native-ready craft1 for publicly named key nodes below the same public planning floor; local readiness, not proof of optimal scheduling',
        'residual_categories': 'overlapping observable evidence classes, not exclusive causal explanations; all-known failure or missed ready nodes indicates an execution gap requiring case review',
        'capacity_fixture': 'modified allocations in one original task for component correctness; extra native container and optional hidden depletion while away; excluded from closed-loop scores',
        'critical_rollouts': '18/18 new-controller autonomous continuations from six historical midtrajectory states, constant wait base; not initial-task success rate',
        'knowledge_counterfactuals': 'post-hoc evaluator-selected craft1 + inspect bridges, two real actions within original remaining40, both branches twice; no agent or whole-task success claim',
        'storage_evidence': 'formal storage/return/retrieval action count is zero; unit and stress correctness do not establish task-level value',
        'raw_reference_logs': 'S0 has no tri-state or Stage10 selection logs; zeros mean not instrumented',
        'bootstrap': '10000 paired family samples seed314159; zero-width interval for identical outcomes is not equivalence evidence',
    })
    assert all(r['passed'] for r in bounds)
    assert all(m['served_models'] == {'deepseek-flash': m['requests']} for m in models.values())
    print(json.dumps({'requests': sum(m['requests'] for m in models.values()), 'cost_usd': sum(m['cost_usd'] for m in models.values()),
                      'bounded': True, 'served_models': 'deepseek-flash'}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--runtime'); a = p.parse_args(); main(a.runtime)
