from dataclasses import replace
from math import inf

from scar_public.control_capacity import ControlCapacity, ControlInformationPlanner
from scar_public.finite_planner import State, Goal, compile_model
from scar_public.information_bound import InformationBoundPlanner
from scar_public.information_instances import workshop
from scar_public.information_reference import independent_oracle, reachable_contexts
from scar_public.information_transfer import production, bridge_instance, TransferInstance
from scar_public.observation_capacity import ObservationCapacity


def control(instance, indices=(0,), base='single'):
    return ControlInformationPlanner(instance.models,instance.goal,instance.allowed,
                                     base=base,symbol_indices=indices)


def test_location_refinement_rejects_frozen_false_information_channel():
    case=production(family='cross',ore=2,fiber=2,distance=2,horizon=5)
    old=InformationBoundPlanner(case.models,case.goal,case.allowed,mode='capacity_lp')
    assert old.initial(case.belief,5).lower == 2
    for base in ('lp','single'):
        p=control(case,base=base)
        assert p.initial(case.belief,5).lower == inf
        answer=p.solve(case.belief,5)
        assert answer.exact and answer.upper == independent_oracle(case)(case.belief,5) == inf
        assert p.expanded == 0


def test_chain_refinement_accounts_for_transport_and_inventory():
    for capacity,horizon,expected in ((3,8,inf),(3,9,9),(2,10,inf),(2,11,11)):
        case=production(family='chain',ore=2,fiber=1,upstream=True,distance=2,gather=True,
                        capacity=capacity,assay=True,horizon=horizon)
        p=control(case)
        assert p.initial(case.belief,horizon).lower == expected
        answer=p.solve(case.belief,horizon)
        assert answer.exact and answer.upper == independent_oracle(case)(case.belief,horizon) == expected
        if expected < inf:
            assert p.verify(case.belief,horizon,answer.policy) == expected


def test_known_preparation_stage_prevents_premature_observations():
    for horizon,expected in ((5,inf),(6,6)):
        case=workshop(count=4,scan_steps=5,horizon=horizon)
        old=ObservationCapacity(case.models,case.goal,case.allowed)
        p=control(case)
        assert old.lower(case.belief,horizon) == 2
        assert p.initial(case.belief,horizon).lower == expected
        assert independent_oracle(case)(case.belief,horizon) == expected


def test_empty_projection_is_original_bound_and_refinement_dominates_reachable_queries():
    cases=(workshop(count=3,scan_steps=2,horizon=3,assay=True),
           production(family='cross',ore=2,fiber=2,upstream=True,distance=1,horizon=5),
           bridge_instance('recipe_upstream',4))
    for case in cases:
        old=ObservationCapacity(case.models,case.goal,case.allowed)
        empty=ControlCapacity(case.models,case.goal,case.allowed,())
        indices=(0,2,3) if case.family.startswith('recipe_') else (0,)
        refined=ControlCapacity(case.models,case.goal,case.allowed,indices)
        oracle=independent_oracle(case)
        for belief,horizon in reachable_contexts(case):
            assert old.lower(belief,horizon) == empty.lower(belief,horizon)
            assert old.lower(belief,horizon) <= refined.lower(belief,horizon) <= oracle(belief,horizon)


def test_hidden_successor_stage_is_not_treated_as_a_free_observation():
    def transition(name,state,action):
        phase,done=state.symbols
        if action == 'hidden':
            phase=int(name[1:])
        if action == 'finish':
            done=True
        return State((phase,done),state.resources),(done,state.resources)
    models=[compile_model(f'm{i}',((0,1),(False,True)),(1,),
                          {'hidden':1,'finish':1},transition) for i in range(2)]
    initial=State((0,False),(1,))
    goal=Goal(symbols=((1,True),))
    belief=frozenset((m.name,initial) for m in models)
    refined=ControlCapacity(models,goal,lambda s:True,(0,))
    assert refined.stats['disabled_reason'] == 'same observation permits different successor projections'
    assert refined.lower(belief,2) == 1
    assert refined.stats['fallback'] is not None


def test_uncertain_current_stage_falls_back_instead_of_choosing_a_favorable_stage():
    case=workshop(count=2,scan_steps=3,horizon=4)
    belief=frozenset((name,State((int(name[1:]),'live'),state.resources)) for name,state in case.belief)
    refined=ControlCapacity(case.models,case.goal,case.allowed,(0,))
    coarse=ObservationCapacity(case.models,case.goal,case.allowed)
    assert refined.lower(belief,4) == coarse.lower(belief,4) == 2
    assert refined.stats['inapplicable_queries'] == 1


def test_weighted_costs_and_unobservable_completion_fall_back():
    case=workshop(scan_steps=2,horizon=3,costs={'scan':3,'make_0':2,'make_1':2})
    p=control(case)
    assert p.coverage.stats['disabled_reason'] == 'requires unit action costs'
    result=p.solve(case.belief,3)
    assert result.exact and result.upper == 8
    case=workshop(count=2,stock=2,horizon=3,wrong_breaks=False)
    for model in case.models:
        model.lookup={key:replace(value,observation=('opaque',)) for key,value in model.lookup.items()}
    refined=ControlCapacity(case.models,case.goal,case.allowed,(0,))
    assert refined.stats['disabled_reason'] == 'completion is not observable'
    assert refined.lower(case.belief,3) == 0


def test_common_productive_action_does_not_require_identification():
    case=workshop(count=4,stock=1,horizon=4,common=True,assay=True,scan_steps=3)
    p=control(case)
    assert p.initial(case.belief,4).lower == 1
    answer=p.solve(case.belief,4)
    assert answer.upper == p.verify(case.belief,4,answer.policy) == 1
