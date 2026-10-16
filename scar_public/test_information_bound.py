from math import inf

from scar_public.information_bound import InformationBoundPlanner
from scar_public.information_instances import workshop
from scar_public.information_reference import independent_oracle, reachable_contexts


def planner(instance, mode, **kwargs):
    return InformationBoundPlanner(instance.models, instance.goal, instance.allowed,
                                   mode=mode, **kwargs)


def test_information_cost_is_strictly_above_perfect_information():
    case = workshop(scan_steps=3, horizon=4)
    values = {mode: planner(case, mode).initial(case.belief, 4).lower
              for mode in InformationBoundPlanner.MODES}
    assert values == dict(lp=1, single=1, pair_lp=4, pair_exact=4,
                          capacity_lp=2, capacity_single=2)
    assert independent_oracle(case)(case.belief, 4) == 4


def test_material_consumed_by_a_probe_can_destroy_every_continuation():
    scarce = workshop(scan_steps=3, horizon=4, assay=True, stock=1)
    spare = workshop(scan_steps=3, horizon=4, assay=True, stock=2)
    for case, expected in ((scarce, 4), (spare, 2)):
        p = planner(case, 'pair_exact')
        assert p.initial(case.belief, case.horizon).lower == expected
        assert independent_oracle(case)(case.belief, case.horizon) == expected
    p = planner(scarce, 'pair_lp')
    assert all(p.initial(b, 3).lower == inf for b in p.branches(scarce.belief, 'assay').values())


def test_horizon_infeasibility_is_detected_despite_each_world_being_solvable():
    case = workshop(count=4, scan_steps=3, horizon=3)
    assert planner(case, 'single').initial(case.belief, 3).lower == 1
    assert planner(case, 'pair_lp').initial(case.belief, 3).lower == inf
    assert independent_oracle(case)(case.belief, 3) == inf


def test_productive_information_is_not_charged_twice_or_required_unnecessarily():
    case = workshop(count=4, stock=1, horizon=4, common=True, assay=True)
    for mode in InformationBoundPlanner.MODES:
        p = planner(case, mode)
        assert p.initial(case.belief, 4).lower == 1
        solved = p.solve(case.belief, 4)
        assert solved.lower == solved.upper == 1
        assert p.verify(case.belief, 4, solved.policy) == 1


def test_pair_feasibility_does_not_imply_joint_feasibility():
    case = workshop(count=3, stock=2, horizon=3, wrong_breaks=False)
    p = planner(case, 'pair_exact')
    assert p.initial(case.belief, 3).lower == 2
    assert independent_oracle(case)(case.belief, 3) == inf
    assert p.solve(case.belief, 3).lower == inf


def test_action_cost_is_not_confused_with_action_count_horizon():
    case = workshop(scan_steps=2, horizon=3, costs={'scan': 3, 'make_0': 2, 'make_1': 2})
    for mode in InformationBoundPlanner.MODES:
        p = planner(case, mode)
        optimum = independent_oracle(case)(case.belief, 3)
        assert optimum == 8
        assert p.initial(case.belief, 3).lower <= optimum
        solved = p.solve(case.belief, 3)
        assert solved.exact and solved.upper == 8
        assert p.verify(case.belief, 3, solved.policy) == 8


def test_interrupted_bound_computation_returns_a_valid_lower_not_false_infeasibility():
    case = workshop(count=3, scan_steps=3, horizon=4)
    for limit in (0, 1, 5, 20):
        for mode in ('single', 'pair_lp', 'pair_exact'):
            p = planner(case, mode, node_limit=limit)
            lower = p.initial(case.belief, 4).lower
            assert 1 <= lower <= 4
            result = p.solve(case.belief, 4, expansion_budget=0)
            assert result.lower <= 4 and result.upper == inf and result.status == 'UNKNOWN'


def test_every_reachable_subproblem_bound_and_search_against_unpruned_oracle():
    cases = (workshop(count=3, scan_steps=2, horizon=3, assay=True),
             workshop(count=3, stock=2, horizon=3, wrong_breaks=False),
             workshop(count=4, stock=3, horizon=3, bits=True))
    for case in cases:
        oracle = independent_oracle(case)
        contexts = reachable_contexts(case)
        variants = {mode: planner(case, mode) for mode in InformationBoundPlanner.MODES}
        for belief, horizon in sorted(contexts, key=lambda k: (k[1], repr(k[0]))):
            truth = oracle(belief, horizon)
            bounds = {mode: p.initial(belief, horizon).lower for mode, p in variants.items()}
            assert bounds['lp'] <= bounds['pair_lp'] <= truth
            assert bounds['lp'] <= bounds['single'] <= bounds['pair_exact'] <= truth
            assert bounds['lp'] <= bounds['capacity_lp'] <= truth
            assert bounds['single'] <= bounds['capacity_single'] <= truth
        for p in variants.values():
            solved = p.solve(case.belief, case.horizon)
            assert solved.exact and solved.upper == oracle(case.belief, case.horizon)
            if solved.upper < inf:
                assert p.verify(case.belief, case.horizon, solved.policy) == solved.upper


def test_capacity_finds_higher_order_resource_conflict_missed_by_every_pair():
    case = workshop(count=6, stock=5, horizon=6, wrong_breaks=False)
    assert planner(case, 'pair_exact').initial(case.belief, 6).lower == 2
    for mode in ('capacity_lp', 'capacity_single'):
        assert planner(case, mode).initial(case.belief, 6).lower == inf
    assert independent_oracle(case)(case.belief, 6) == inf


def test_capacity_counts_binary_information_and_productive_leaf_separately():
    case = workshop(count=8, stock=4, horizon=4, bits=True)
    assert planner(case, 'single').initial(case.belief, 4).lower == 1
    assert planner(case, 'pair_exact').initial(case.belief, 4).lower == 2
    for mode in ('capacity_lp', 'capacity_single'):
        assert planner(case, mode).initial(case.belief, 4).lower == 4
    assert independent_oracle(case)(case.belief, 4) == 4


def test_capacity_abstains_when_hidden_resources_share_an_observation():
    from dataclasses import replace
    case = workshop(count=2, stock=2, horizon=3, wrong_breaks=False, assay=True)
    for model in case.models:
        model.lookup = {key: replace(value, observation=(value.observation[2] == 'done',),
                                     delta=(0,) if model.name == 'm0' and key[1] == 'assay' else value.delta)
                        for key, value in model.lookup.items()}
    p = planner(case, 'capacity_lp')
    assert p.coverage.stats['disabled_reason'] == 'same observation permits different successor resources'
    assert p.coverage.lower(case.belief, 3) == 0


def test_capacity_does_not_certify_when_completion_is_unobservable():
    from dataclasses import replace
    case = workshop(count=2, stock=2, horizon=3, wrong_breaks=False)
    for model in case.models:
        model.lookup = {key: replace(value, observation=('opaque',))
                        for key, value in model.lookup.items()}
    p = planner(case, 'capacity_lp')
    assert p.coverage.stats['disabled_reason'] == 'completion is not observable'
    assert p.coverage.lower(case.belief, 3) == 0
