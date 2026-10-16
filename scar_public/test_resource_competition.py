from dataclasses import replace
from math import inf, isfinite

import pytest

from scar_public.resource_competition import (
    Recipe, ResourceProblem, ResourceDomain, ResourceGap, consumption, compile_resources, select_experiment)


def problem(*, needs=500, held=1000, bag=0, floor=0, capacity=2000,
            modes=('exact','ceil_batch'), access=('hand',), quantities=(1,), protected=()):
    return ResourceProblem(locations=('workshop',), routes={}, items=('ore','blade'),
        recipes=(Recipe('blade',(('ore',needs),),('workshop',),modes,access,quantities),),
        start_location='workshop',holding={'ore':held},ground={'workshop':{'ore':floor}},
        bag={'ore':bag} if bag else {},bag_name='satchel' if bag else None,
        hand_capacity=capacity,bag_capacity=5000 if bag else 0,hand_background=0,bag_background=0,
        target='blade',protected_totals=protected)


def test_quantity_hypotheses_are_computable_and_distinct_for_batches():
    recipe = problem().recipes[0]
    assert consumption(recipe,1,'exact') == {'ore':500}
    assert consumption(recipe,1,'ceil_batch') == {'ore':1000}
    assert consumption(recipe,2,'ceil_batch') == {'ore':1000}
    assert consumption(recipe,2,'ceil_per_output') == {'ore':2000}


def test_safe_on_task_probe_has_common_verified_continuation_in_every_branch():
    compiled = compile_resources(problem(),horizon=4)
    result,witness,planner = select_experiment(compiled,prefix_depth=2)
    assert result['status'] == 'CONDITIONAL_EXPERIMENT'
    assert result['prefix'] == ['craft 1 blade'] and result['worst_total_actions'] == '2'
    assert all(x['common_continuation_verified'] for x in result['selected_leaves'])
    for model in compiled.models:
        state,observation = model.step(compiled.domain.start,'craft 1 blade')
        worlds = planner.branches(compiled.belief,'craft 1 blade')[observation]
        assert planner.verify(worlds,3,witness['suffixes'][observation]) == 1


def test_discriminating_but_resource_destroying_batch_is_rejected():
    p = problem(held=2000,modes=('exact','ceil_per_output'),quantities=(1,2),protected=(('ore',1000),))
    compiled = compile_resources(p,horizon=4)
    result,_,_ = select_experiment(compiled,prefix_depth=1)
    unsafe = next(c for c in result['candidates'] if c['prefix'] == ['craft 2 blade'])
    assert unsafe['decision'] == 'REJECT_UNVERIFIED_CONTINUATION'
    assert any(not l['common_continuation_verified'] for l in unsafe['leaves'])
    assert result['prefix'] == ['craft 1 blade']


def test_bag_is_hidden_until_a_paid_inspection_and_extra_cost_is_explicit():
    p = problem(held=0,bag=1000,access=('hand_bag',))
    compiled = compile_resources(p,horizon=4)
    planner = compiled.planner()
    branches = planner.branches(compiled.belief,'craft 1 blade')
    assert len(branches) == 1  # Different latent bag amounts are not public evidence.
    after = next(iter(branches.values()))
    assert len(planner.branches(after,'inspect satchel')) == 2
    direct,_,_ = select_experiment(compiled,prefix_depth=2,max_extra_actions=0)
    assert direct['status'] == 'DIRECT_POLICY'
    allowed,_,_ = select_experiment(compiled,prefix_depth=2,max_extra_actions=1)
    assert allowed['status'] == 'CONDITIONAL_EXPERIMENT'
    assert allowed['prefix'] == ['craft 1 blade','inspect satchel']
    assert allowed['worst_total_actions'] == '3'


def test_access_probe_is_skipped_if_direct_completion_is_cheaper():
    p = problem(needs=1000,held=0,bag=1000,modes=('exact',),access=('hand','hand_bag'))
    compiled = compile_resources(p,horizon=5)
    result,_,_ = select_experiment(compiled,prefix_depth=1)
    assert result['status'] == 'DIRECT_POLICY'
    probe = next(c for c in result['candidates'] if c['prefix'] == ['craft 1 blade'])
    assert probe['all_leaves_verified'] and probe['decision'] == 'REJECT_EXTRA_COST'
    allowed,_,_ = select_experiment(compiled,prefix_depth=1,max_extra_actions=1)
    assert allowed['status'] == 'CONDITIONAL_EXPERIMENT'
    assert allowed['prefix'] == ['craft 1 blade']
    assert allowed['worst_total_actions'] == '4'


def test_unviable_candidate_world_is_not_discarded_to_approve_test():
    p = problem(needs=3000,held=2000,bag=1000,modes=('exact',),access=('hand','hand_bag'))
    compiled = compile_resources(p,horizon=5)
    result,witness,_ = select_experiment(compiled,prefix_depth=1)
    assert result['status'] == 'NO_VERIFIED_SHARED_CONTINUATION' and witness is None
    assert result['baseline_lower'] == 'inf'
    assert all(not c['all_leaves_verified'] for c in result['candidates'])


def test_opportunity_mode_retains_impossible_world_and_reports_conditional_success():
    p = problem(needs=3000,held=2000,bag=1000,modes=('exact',),access=('hand','hand_bag'))
    compiled = compile_resources(p,horizon=5)
    result,witness,planner = select_experiment(compiled,prefix_depth=1,mode='preserve_opportunity')
    assert result['status'] == 'CONDITIONAL_EXPERIMENT' and result['prefix'] == ['craft 1 blade']
    assert len(result['success_exempt_models']) == 1
    assert len(planner.models) == 2 and len(compiled.belief) == 2
    exempt = result['success_exempt_models'][0]
    assert result['initial_individual_feasibility'][exempt]['lower'] == 'inf'
    branches = planner.branches(compiled.belief,'craft 1 blade')
    for observation,worlds in branches.items():
        planner.verify(worlds,4,witness['suffixes'][observation])
        if {name for name,_ in worlds} == {exempt}:
            assert witness['suffixes'][observation] == {'stop':True}
            assert not all(planner.goal.holds(s) for _,s in worlds)  # NOT a completion claim.


def test_opportunity_exemptions_never_relax_protected_resources():
    p = problem(held=2000,modes=('exact','ceil_per_output'),quantities=(1,2),protected=(('ore',1000),))
    result,_,_ = select_experiment(compile_resources(p,horizon=4),prefix_depth=1,mode='preserve_opportunity')
    assert not result['success_exempt_models']
    unsafe = next(c for c in result['candidates'] if c['prefix'] == ['craft 2 blade'])
    assert unsafe['decision'] == 'REJECT_UNVERIFIED_CONTINUATION'


def test_upstream_recipe_and_cross_location_travel_are_real_actions():
    p = ResourceProblem(locations=('forge','mine'),routes={'forge':{'mine':'mine'},'mine':{'forge':'forge'}},
        items=('ore','bar','blade'),recipes=(
            Recipe('bar',(('ore',1000),),('forge',),('exact',),('hand',)),
            Recipe('blade',(('bar',500),),('forge',),('exact','ceil_batch'),('hand',))),
        start_location='forge',holding={},ground={'mine':{'ore':1000}},bag={},bag_name=None,
        hand_capacity=2000,bag_capacity=0,hand_background=0,bag_background=0,target='blade')
    compiled = compile_resources(p,horizon=8,max_states=12000)
    planner = compiled.planner(); solved = planner.solve(compiled.belief,8,2000)
    assert isfinite(solved.upper) and solved.upper >= 7
    assert planner.verify(compiled.belief,8,solved.policy) == solved.upper
    assert not isfinite(planner.solve(compiled.belief,5,2000).upper)


def test_no_certificate_from_truncated_grounding_or_search_budget():
    with pytest.raises(ResourceGap): compile_resources(problem(),max_states=1)
    compiled = compile_resources(problem(),horizon=3)
    planner = compiled.planner()
    result = planner.solve(compiled.belief,3,expansion_budget=0)
    assert result.status == 'UNKNOWN' and result.policy is None


def test_equivalent_parameters_do_not_manufacture_distinguishing_branches():
    p = problem(needs=1000,modes=('exact','ceil_batch','ceil_per_output'),
                access=('hand','hand_bag'),quantities=(1,))
    compiled = compile_resources(p,horizon=3)
    assert len(compiled.models) == 1 and len(compiled.aliases['m0']['blade']) == 6
    result,_,_ = select_experiment(compiled,prefix_depth=2)
    assert result['status'] == 'DIRECT_POLICY' and not result['candidates']


def test_reachable_graph_lp_search_matches_independent_unpruned_oracle():
    for p in (problem(),problem(needs=1000,held=0,bag=1000,modes=('exact',),access=('hand','hand_bag'))):
        compiled = compile_resources(p,horizon=4)
        planner = compiled.planner(); oracle = planner.oracle()
        for horizon in (1,2,3,4):
            result = planner.solve(compiled.belief,horizon)
            assert result.exact and result.lower == oracle(compiled.belief,horizon)
            if result.upper < inf:
                assert planner.verify(compiled.belief,horizon,result.policy) == result.upper
