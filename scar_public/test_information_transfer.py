from math import inf

from scar_public.information_bound import InformationBoundPlanner
from scar_public.information_reference import independent_oracle, reachable_contexts
from scar_public.information_transfer import production, bridge_instance


def bounds(instance, mode):
    return InformationBoundPlanner(instance.models, instance.goal, instance.allowed, mode=mode)


def test_two_resources_are_not_interchangeable():
    for ore, fiber, expected in ((3,2,inf),(2,3,inf),(3,3,3)):
        instance = production(family='test', ore=ore, fiber=fiber, horizon=3)
        assert independent_oracle(instance)(instance.belief,3) == expected
        assert bounds(instance,'capacity_lp').initial(instance.belief,3).lower == expected


def test_upstream_conversion_consumes_fuel_and_requires_real_actions():
    for fuel, expected in ((2,inf),(3,6)):
        instance = production(family='test', ore=3, fiber=3, fuel=fuel, upstream=True, horizon=6)
        p = bounds(instance,'capacity_single')
        solved = p.solve(instance.belief,6)
        assert solved.exact and solved.upper == expected
        assert independent_oracle(instance)(instance.belief,6) == expected
        if expected < inf:
            assert p.verify(instance.belief,6,solved.policy) == expected


def test_real_locations_cannot_be_replaced_by_free_observations():
    instance = production(family='test',ore=2,fiber=2,distance=2,horizon=5)
    p = bounds(instance,'capacity_lp')
    # Explicit limitation: erasing location permits optimistic abstract channels.
    assert p.initial(instance.belief,5).lower == 2
    assert independent_oracle(instance)(instance.belief,5) == inf
    assert len(p.branches(instance.belief,'move_next')) == 1
    assert len(p.branches(instance.belief,'make_0')) == 1  # off-station failure


def test_chain_and_transport_costs_and_inventory_are_joint_constraints():
    for capacity, horizon, expected in ((3,8,inf),(3,9,9),(2,10,inf),(2,11,11)):
        instance = production(family='test',ore=2,fiber=1,upstream=True,distance=2,
                              gather=True,capacity=capacity,assay=True,horizon=horizon)
        oracle = independent_oracle(instance)
        assert oracle(instance.belief,horizon) == expected
        p = bounds(instance,'capacity_single')
        solved = p.solve(instance.belief,horizon)
        assert solved.exact and solved.upper == expected
        if expected < inf:
            assert p.verify(instance.belief,horizon,solved.policy) == expected


def test_unchanged_game_resource_bridge_and_no_guaranteed_gain():
    for kind, horizon, expected in (('recipe_multiresource',2,2),
                                   ('recipe_upstream',4,4),('recipe_cross_location',7,7)):
        instance = bridge_instance(kind,horizon)
        oracle = independent_oracle(instance)
        assert oracle(instance.belief,horizon) == expected
        for mode in ('lp','capacity_lp','single','capacity_single'):
            p = bounds(instance,mode)
            answer = p.solve(instance.belief,horizon)
            assert answer.exact and answer.upper == expected
            assert p.verify(instance.belief,horizon,answer.policy) == expected


def test_admissibility_on_all_reachable_extended_subproblems():
    instance = production(family='test',ore=2,fiber=2,upstream=True,distance=1,horizon=5)
    oracle = independent_oracle(instance)
    planners = [bounds(instance,m) for m in InformationBoundPlanner.MODES]
    contexts = reachable_contexts(instance)
    for belief,horizon in contexts:
        truth = oracle(belief,horizon)
        for p in planners:
            assert p.initial(belief,horizon).lower <= truth
