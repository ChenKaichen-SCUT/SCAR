import json
from dataclasses import replace

from scar_public.evidence_repair import (RepairMemory,RepairController,scoped_problem,
    semantic_context,enabling_conditions,failure_key)
from scar_public.resource_competition import profile_advantage,compile_resources,select_experiment
from scar_public.resource_evidence import EvidenceBank
from scar_public.resource_agent import restore_trial
from scar_public.test_resource_trial import model,START,CRAFTED
from scar_public.test_resource_competition import problem
from scar_public.test_resource_evidence import floor_access_evidence


def test_equal_worst_case_can_conceal_profile_regret():
    ref={'a':1,'b':4};test={'a':3,'b':4}
    assert max(ref.values())==max(test.values())
    assert profile_advantage(ref,test)['minimum_saving']==-2
    assert profile_advantage(ref,{'a':1,'b':3})['status']=='NONDEGRADING'
    assert profile_advantage(None,test)['status']=='UNKNOWN'


def test_selected_probe_carries_pre_execution_profile_certificate():
    c=compile_resources(problem(),horizon=4)
    report,_,_=select_experiment(c,require_profile_nondegradation=True)
    assert report['status']=='CONDITIONAL_EXPERIMENT'
    assert report['prospective_value']['minimum_saving']>=0


def test_joint_conditions_explain_capacity_and_total_missing_material():
    p,bank=floor_access_evidence();allowed,_=bank.query(p)
    conditions=enabling_conditions(p,allowed[p.target],'craft 1 blade')
    assert conditions['all_profiles_obstructed']
    assert all(r['capacity_shortfall']==1000 for r in conditions['profiles'])
    # A demonstrated lower capacity bound is NOT proof of physical infeasibility.
    lower=replace(p,source={'hand_capacity_bounds':[2,None]})
    assert not enabling_conditions(lower,allowed[p.target],'craft 1 blade')['all_profiles_obstructed']


def test_scoped_guard_stops_transfer_at_observed_hour_or_level_change():
    text='Current Time: 0001-01-01 14:20:00\nMy level is 1.\n'+START
    p=scoped_problem(model(),text,'oak_rod');bank=EvidenceBank();_,entry=bank.entry(p)
    entry['allowed']=[('ceil_batch','hand')]
    assert bank.query(scoped_problem(model(),text.replace('14:20','14:50'),'oak_rod'))[1]['reused']
    assert not bank.query(scoped_problem(model(),text.replace('14:20','15:00'),'oak_rod'))[1]['reused']
    assert not bank.query(scoped_problem(model(),text.replace('level is 1','level is 2'),'oak_rod'))[1]['reused']


def test_attribute_scope_is_explicit_and_does_not_import_clock_scoped_facts():
    from scar_public.evidence_repair import context_matches
    text='Current Time: 0001-01-01 14:20:00\nMy level is 1.\n'+START
    p=scoped_problem(model(),text,'oak_rod');bank=EvidenceBank();_,entry=bank.entry(p)
    entry['allowed']=[('ceil_batch','hand')]
    broad=scoped_problem(model(),text,'oak_rod','attributes')
    assert not bank.query(broad)[1]['reused']
    assert context_matches(text.replace('14:20','15:20'),broad.source['semantic_context'])
    assert not context_matches(text.replace('level is 1','level is 2'),broad.source['semantic_context'])


def test_passive_feedback_learns_and_exact_cache_does_not_generalize(monkeypatch):
    p,_=floor_access_evidence()
    p=replace(p,source={'semantic_context':semantic_context(START),'equipment':{}})
    memory=RepairMemory();controller=RepairController(memory)
    memory.model.stations['blade']={'name':'bench'}
    # Use exact public states for the narrow adapter, independent of its planner.
    text='Current Location: workshop\nI am holding 2 ore.\nI have equipped no objects.\nI see 1 ore near me.'
    p=replace(p,source={**p.source,'semantic_context':semantic_context(text)})
    monkeypatch.setattr(controller,'ground',lambda *a:p)
    controller.after_decision({'action':'craft 1 blade'},text,0)
    controller.resume(text+'\nCannot craft blade, Do not have sufficient amount of necessary ingredients.')
    allowed,_=controller.bank().query(p)
    assert allowed and all('ground' not in a for q,a in allowed['blade'])
    controller.mode='cache';assert controller.review_proposal({'action':'craft 1 blade'},text)
    changed=replace(p,holding={'ore':1000},ground={'workshop':{'ore':2000}})
    monkeypatch.setattr(controller,'ground',lambda *a:changed)
    assert controller.review_proposal({'action':'craft 1 blade'},text) is None
    controller.mode='structured';assert controller.review_proposal({'action':'craft 1 blade'},text)


def test_constructive_repair_is_strong_and_checkpointable(monkeypatch):
    p=problem(needs=1000,held=0,floor=1000,modes=('exact',),access=('hand','hand_ground'))
    memory=RepairMemory();controller=RepairController(memory)
    _,entry=controller.bank().entry(p);entry['allowed']=[('exact','hand')]
    memory.model.stations['blade']={'name':'bench'}
    monkeypatch.setattr(controller,'ground',lambda *a:p)
    review=controller.review_proposal({'action':'craft 1 blade'},START)
    action=controller.certified_repair(review,START,10)
    assert action['action']=='pick up ore'
    assert action['repair_certificate']['profile_costs']=={'m0':3}
    restored=restore_trial(json.loads(json.dumps(memory.resource_trial_state)))
    assert restored.action()=='pick up ore'


def test_obstruction_is_not_a_new_success_exemption(monkeypatch):
    p,bank=floor_access_evidence();memory=RepairMemory();memory.resource_evidence=bank.state
    controller=RepairController(memory);memory.model.stations['blade']={'name':'bench'}
    monkeypatch.setattr(controller,'ground',lambda *a:p)
    review=controller.review_proposal({'action':'craft 1 blade'},START)
    assert controller.certified_repair(review,START,10) is None
    assert memory.resource_trial_state is None
    assert memory.evidence_repairs[-1]['status']=='ENABLING_CONDITION_REQUIRED'


def test_carried_container_occupies_capacity_and_cannot_be_dropped_in_policy():
    from scar_public.test_resource_trial import observation
    from scar_public.resource_trial import make_trial
    from scar_public.resource_competition import ResourceDomain
    m=model();m.containers['bag']={'items':{'oak_log':1},'used':1,'capacity':2,'uncertain_after_craft':False}
    text=observation('1 bag')
    p=scoped_problem(m,text,'oak_rod')
    assert p.hand_background==1000 and p.hand_capacity==2000
    assert 'bag' not in p.items and 'drop bag' not in ResourceDomain(p).actions
    report,session=make_trial(m,text,'oak_rod',problem=p,mode='strong',
        allowed_profiles={'oak_rod':[('ceil_batch','hand_bag')]})
    assert session.action()=='craft 1 oak_rod'
    event=session.observe(observation('1 bag','1 workbench, 1 oak_rod',
        'I successfully crafted 1 oak_rod. It is now on the ground.'))
    assert event['status']=='ACTIVE' and session.action()=='pick up oak_rod'
    session.observe(observation('1 bag, 1 oak_rod','1 workbench','I picked up oak_rod.'))
    assert session.summary()['status']=='LOCAL_MILESTONE_CONFIRMED'


def test_carried_container_detachment_invalidates_even_if_other_counts_match():
    from scar_public.test_resource_trial import observation
    from scar_public.resource_trial import make_trial
    m=model();m.containers['bag']={'items':{'oak_log':1},'used':1,'capacity':2,'uncertain_after_craft':False}
    text=observation('1 bag');p=scoped_problem(m,text,'oak_rod')
    _,session=make_trial(m,text,'oak_rod',problem=p,mode='strong',
        allowed_profiles={'oak_rod':[('ceil_batch','hand_bag')]})
    session.action();event=session.observe(observation('no objects','1 workbench, 1 oak_rod',
        'I successfully crafted 1 oak_rod. It is now on the ground.'))
    assert event['status']=='OBSERVATION_GAP' and 'detached' in event['reason']


def test_stale_carried_container_triggers_paid_observation_not_invented_counts():
    from scar_public.test_resource_trial import observation
    m=model();m.containers['bag']={'items':{'oak_log':1},'used':1,'capacity':2,'uncertain_after_craft':True}
    memory=RepairMemory();memory.model=m;controller=RepairController(memory)
    result=controller.consider({'action':'craft 1 oak_rod'},observation('1 bag'),10)
    assert result['action']=='inspect bag' and result['decision_source']=='paid_grounding_observation'
    assert not memory.resource_attempts and not memory.resource_trial_state
