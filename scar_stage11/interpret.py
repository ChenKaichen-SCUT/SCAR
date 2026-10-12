"""Request/prompt fidelity, bounds and original-run accounting; no model calls."""
import collections
import gzip
import hashlib
import json
from pathlib import Path

from scar.io import atomic_json
from scar_stage11.controller import METHODS, PROMPT_REMINDER
from scar_unknown17_stage7.controller import CONFIGS

OUT = Path('results/stage11')


def main():
    models = {}; first = {}; bounds = []; risks = []; bookkeeping = []
    for method in METHODS:
        wrapped = list(map(json.loads, gzip.open(OUT/f'requests_{method}.jsonl.gz', 'rt')))
        requests = [w['request'] for w in wrapped]; served = collections.Counter(); finish = collections.Counter()
        for w in wrapped:
            request = w['request']; first.setdefault(w['task_id'], request['messages'])
            raw = request.get('raw_response') or {}
            if isinstance(raw, str):
                try: raw = json.loads(raw)
                except ValueError: raw = {}
            served[raw.get('model', 'UNKNOWN')] += 1
            for c in raw.get('choices', []): finish[c.get('finish_reason')] += 1
        models[method] = {'requests': len(requests), 'requested_models': dict(collections.Counter(r['model'] for r in requests)),
            'served_models': dict(served), 'request_statuses': dict(collections.Counter(r['status'] for r in requests)),
            'finish_reasons': dict(finish), 'thinking': dict(collections.Counter(r.get('thinking', 'UNKNOWN') for r in requests)),
            'cost_usd': sum(r.get('cost_usd', 0) for r in requests),
            **{k: sum((r.get('usage') or {}).get(k, 0) for r in requests)
               for k in ['prompt_tokens','completion_tokens','prompt_cache_hit_tokens','prompt_cache_miss_tokens']},
            'extra_planner_calls': 0}
        for ep in map(json.loads, gzip.open(OUT/f'trajectories_{method}.jsonl.gz', 'rt')):
            states = [r['stage7_state_before'] for r in ep['rows']]
            choices = [r['structured'].get('stage11', {}) for r in ep['rows']]
            mc = max((len(r['structured'].get('stage10', {}).get('conditions', [])) for r in ep['rows']), default=0)
            me = max((len(c.get('exploration_candidates', [])) for c in choices), default=0)
            mx = max((len(c.get('execution_candidates', [])) for c in choices), default=0)
            mn = max((len(c.get('public_goal_view', {}).get('nodes', {})) for c in choices), default=0)
            correct = all(s.get('flags') == CONFIGS['C1'] and not s.get('opportunistic') and not s.get('storage')
                          and 'recovery' not in s for s in states)
            bounds.append({'task_id': ep['task_id'], 'steps': len(ep['rows']), 'condition_checks_max': mc,
                'exploration_candidates_max': me, 'execution_candidates_max': mx, 'public_nodes_max': mn,
                'only_S1_backbone': correct,
                'passed': correct and len(ep['rows']) <= 40 and max(mc,me,mx) <= 32 and mn <= 64})
            risks.append({'task_id': ep['task_id'], 'case_id': ep['case_id'], 'method': method,
                'death_events': [{'index': r['index'], 'action': r['executed_action'], 'public_feedback': r['next_observation']['text']}
                                 for r in ep['rows'] if 'I have died.' in r['next_observation']['text']],
                'curse_warning_steps': sum('invites corruption' in r['next_observation']['text'] for r in ep['rows'])})
            for i in range(len(states)-1):
                delta = states[i+1]['exploration_spent']-states[i]['exploration_spent']
                if delta > 1:
                    bookkeeping.append({'task_id': ep['task_id'], 'method': method, 'index': i,
                                        'action': ep['rows'][i]['executed_action'], 'exploration_counter_delta': delta})
    prompt_records = []
    for c in json.loads((OUT/'cases.json').read_text()):
        group = {m: next((messages for task, messages in first.items() if task.startswith(c['id']+'-'+m+'-')), None) for m in METHODS}
        e0 = json.dumps(group['E0'], ensure_ascii=False, sort_keys=True)
        e1 = json.dumps(group['E1'], ensure_ascii=False, sort_keys=True)
        prompt_records.append({'case_id': c['id'],
            'shared_prompt_and_history_match': group['E0'] is not None and all(group[m] == group['E0'] for m in ['E2','E3','E4']),
            'E1_exactly_fixed_reminder': e1 != e0 and e1.replace('\\n'+PROMPT_REMINDER, '') == e0,
            'first_request_sha256': {m: hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True).encode()).hexdigest() for m,v in group.items()}})
    atomic_json(OUT/'request_model_audit.json', models)
    atomic_json(OUT/'prompt_fidelity.json', {'records': prompt_records,
        'passed': all(r['shared_prompt_and_history_match'] and r['E1_exactly_fixed_reminder'] for r in prompt_records),
        'scope': 'first full messages per family; later prompts differ through actual observations/actions, not extra instructions'})
    atomic_json(OUT/'bounds_audit.json', {'records': bounds, 'passed': all(r['passed'] for r in bounds)})
    atomic_json(OUT/'public_risk_audit.json', {'records': risks, 'summary': {m: {
        'death_events': sum(len(r['death_events']) for r in risks if r['method']==m),
        'curse_warning_steps': sum(r['curse_warning_steps'] for r in risks if r['method']==m)} for m in METHODS}})
    atomic_json(OUT/'exploration_bookkeeping_audit.json', {'multiple_increments': bookkeeping,
        'interpretation': 'inherited/candidate probe counters are internal budgets, not actual environment actions; actual exploration is counted from trajectories'})
    atomic_json(OUT/'analysis_decisions.json', {
        'policy_changed_after_freeze': False, 'paid_episode_reruns': 0, 'extra_models_or_agents': 0,
        'scope': 'original10 Robot developmental families, same initial states/physical seeds,50 episodes,40 actions',
        'reference': 'E0/E1 exact ResourceController S1; E1 differs only by the frozen prompt reminder',
        'public_vs_native': 'only evaluator sees true key graph, native readiness, proposal effects and physical losses',
        'exploration_labels': 'no publicly confirmed link and native non-key subject are separate proxies, not proof of uselessness',
        'forward_bridges': 'unknown downstream connection remains explicit; candidate names are generic and no hidden edges are inferred',
        'timely': 'public confirmed necessity and native local readiness; not global optimality; 3-action window right censoring reported',
        'production_inspection': 'first actual production per intermediate, separately already inspected vs fresh, next3-action window with right censoring',
        'conversion': 'known ingredient names, not full quantities; unconverted recipes retained alongside conditional delay means',
        'local_counterfactual': 'same recorded public state/proposal, disable named priorities, both native branches twice; no full trajectory causality',
        'model_ability': 'useful original proposals and harmful overrides recorded in all methods; no extra calls to synthesize prompt counterfactual',
        'bootstrap': '10000 paired developed-family samples; zero width for identical binary outcomes does not prove equivalence',
        'no_generalization': True})
    assert all(r['passed'] for r in bounds)
    assert all(r['shared_prompt_and_history_match'] and r['E1_exactly_fixed_reminder'] for r in prompt_records)
    assert all(m['served_models'] == {'deepseek-flash': m['requests']} for m in models.values())
    print(json.dumps({'requests': sum(m['requests'] for m in models.values()), 'cost_usd': sum(m['cost_usd'] for m in models.values()),
                      'bounds_passed': True, 'prompt_fidelity_passed': True}))


if __name__ == '__main__':
    main()
