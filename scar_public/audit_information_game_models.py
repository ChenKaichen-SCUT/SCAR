"""Read-only applicability audit of previously public-grounded game models.

No game checkpoint is loaded and no real environment action is executed. Strong
all-model goal obligations here differ from V8's preserve_opportunity mode.
"""
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
from time import perf_counter

from scar_public.finite_planner import printable
from scar_public.information_bound import InformationBoundPlanner
from scar_public.information_reference import independent_oracle
from scar_public.information_transfer import TransferInstance, bridge_grid
from scar_public.resource_competition import Recipe, ResourceProblem, compile_resources


def restore_problem(payload):
    data = dict(payload)
    data['recipes'] = tuple(Recipe(r['output'], tuple(tuple(x) for x in r['needs']),
        tuple(r['stations']), tuple(r['quantity_modes']), tuple(r['access_modes']),
        tuple(r['quantities'])) for r in data['recipes'])
    for field in ('locations','items','assumptions'):
        data[field] = tuple(data[field])
    data['protected_totals'] = tuple(tuple(x) for x in data['protected_totals'])
    return ResourceProblem(**data)


def policy_witness(instance, planner=None):
    planner = planner or InformationBoundPlanner(instance.models, instance.goal, instance.allowed,
                                                mode='single')
    answer = planner.solve(instance.belief, instance.horizon)
    oracle = independent_oracle(instance)
    truth = oracle(instance.belief, instance.horizon)
    assert answer.exact and answer.upper == truth
    traces = {}
    if isfinite(truth):
        assert planner.verify(instance.belief, instance.horizon, answer.policy) == truth
        for name, initial in sorted(instance.belief):
            state, node, actions = initial, answer.policy, []
            while not node.get('stop'):
                action = node['action']
                actions.append(action)
                state, observation = planner.models[name].step(state, action)
                node = node['branches'][observation]
            traces[name] = actions
    return dict(optimum=printable(truth), independent_enumeration_agrees=True,
                oracle_subproblems=oracle.cache_info().currsize,
                action_traces=traces,
                common_open_loop_witness=bool(traces) and len({tuple(t) for t in traces.values()}) == 1)


def audit(problem, horizon):
    start = perf_counter()
    compiled = compile_resources(problem, horizon=horizon, max_states=12000)
    compiled_at = perf_counter()
    planner = InformationBoundPlanner(compiled.models, compiled.domain.goal(),
                                     compiled.domain.allowed, mode='capacity_lp')
    lp = max(planner.relax[name].lower(state,horizon) for name,state in compiled.belief)
    capacity = planner.coverage.lower(compiled.belief,horizon)
    bound_seconds = perf_counter()-compiled_at
    instance = TransferInstance('public_local', 'public_local', compiled.models, compiled.domain.goal(),
                                compiled.belief, horizon, compiled.domain.allowed)
    witness = policy_witness(instance, planner)
    return dict(fingerprint=compiled.fingerprint, candidate_models=len(compiled.models),
                graph_states=compiled.states, horizon=horizon,
                root_lp=printable(lp), root_capacity=printable(capacity),
                combined=printable(max(lp,capacity)), root_improves=capacity>lp,
                capacity_statistics=planner.coverage.stats,
                compilation_seconds=compiled_at-start, bound_seconds=bound_seconds,
                exact_local_solution=witness,
                guarantee_mode='strong; no originally-infeasible-model exemption',
                game_performance_claim=False)


def main():
    source = Path(__file__).parent / 'results/2026-10-16-resource-competition/analysis.json'
    payload = json.loads(source.read_text(encoding='utf-8'))
    rows = []
    for case in payload['cases']:
        problem = restore_problem(case['selection']['grounding'])
        row = audit(problem,case['horizon'])
        assert row['fingerprint'] == case['selection']['fingerprint']
        rows.append(dict(game=case['game'], public_prefix_length=case['next_step'],
                         grounding_fingerprint_verified=True, **row))
    hidden = ResourceProblem(locations=('forge',), routes={}, items=('ore','blade'),
        recipes=(Recipe('blade',(('ore',500),),('forge',),('exact','ceil_batch'),('hand_bag',)),),
        start_location='forge', holding={}, ground={}, bag={'ore':1000}, bag_name='bag',
        hand_capacity=2000, bag_capacity=2000, hand_background=0,bag_background=0,target='blade')
    hidden_audit = audit(hidden,4)
    assert hidden_audit['capacity_statistics']['disabled_reason'] == \
        'same observation permits different successor resources'
    result = dict(api_calls=0, game_actions=0, new_baseline_runs=0,
        source_sha256=sha256(source.read_bytes()).hexdigest(), cases=rows,
        hidden_quantity_negative_control=hidden_audit,
        bridge_policy_witnesses=[dict(name=case.name, **policy_witness(case)) for case in bridge_grid()],
        interpretation='Finite models reconstructed from prior public prefixes. No hidden engine state, '
                       'new game rollout or task score used. Strong infeasibility is not a contradiction '
                       'of a prior preserve_opportunity trial; success obligations differ.')
    destination = Path(__file__).parent / 'results/2026-10-16-information-transfer/game_applicability.json'
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False),flush=True)


if __name__ == '__main__':
    main()
