import json
from dataclasses import asdict

import pytest

from scar_public.obligations import ExecutionModel
from scar_public.resource_competition import ResourceGap, compile_resources, select_experiment, opportunity_planner
from scar_public.resource_trial import from_public, make_trial, TrialSession
from scar_public.resource_agent import ResourceCompetitionAgent, restore_trial, OPTIONS
from scar_public.test_resource_competition import problem


def observation(holding='1 oak_log',floor='1 workbench',feedback='',equipped='no objects'):
    return (f'Current Location: Old Castle, hall\n{feedback}\nI am holding {holding}.\n'
            f'I have equipped {equipped}.\nI see {floor} near me.\n')


RECIPE = 'I have acquired a new item: oak_log. It can be used to craft: oak_rod (0.5 oak_log)'
STATION = 'Cannot craft oak_rod. Missing necessary workbench in the current area.'
START = observation(feedback=RECIPE+'\n'+STATION)
CRAFTED = observation('no objects','1 workbench, 1 oak_rod','I successfully crafted 1 oak_rod. It is now on the ground.')
HELD = observation('1 oak_rod','1 workbench','I picked up oak_rod.')


def model():
    m=ExecutionModel(); m.observe(observation('2 oak_log')); m.observe(START)
    return m


def test_only_observed_recipe_station_and_current_counts_are_grounded():
    m=model(); p=from_public(m,START,'oak_rod')
    assert p.hand_capacity==2000 and p.recipes[0].needs==(('oak_log',500),)
    assert p.target=='oak_rod' and p.protected_totals==()
    with pytest.raises(ResourceGap): from_public(ExecutionModel(),START,'oak_rod')
    with pytest.raises(ResourceGap): from_public(m,START.replace('1 oak_log','some oak_log'),'oak_rod')
    m.stations.clear()
    with pytest.raises(ResourceGap): from_public(m,START,'oak_rod')


def test_real_feedback_filters_models_and_completion_requires_continuation():
    report,s=make_trial(model(),START,'oak_rod')
    assert report['status']=='CONDITIONAL_EXPERIMENT' and s.action()=='craft 1 oak_rod'
    event=s.observe(CRAFTED)
    assert event['discriminated'] and len(event['surviving_models'])==2
    assert s.status=='ACTIVE' and s.action()=='pick up oak_rod'
    s.observe(HELD)
    assert s.action() is None and s.status=='LOCAL_MILESTONE_CONFIRMED'
    assert not s.summary()['full_task_completion_claimed']


@pytest.mark.parametrize('text,expected',[(CRAFTED.replace('no objects.','0.25 oak_log.',1),'MODEL_MISMATCH'),
    (CRAFTED.replace('I am holding no objects.',''),'OBSERVATION_GAP'),
    (CRAFTED+'\nI was attacked and lost 1 HP.','OBSERVATION_GAP')])
def test_unpredicted_or_missing_feedback_invalidates_continuation(text,expected):
    _,s=make_trial(model(),START,'oak_rod'); s.action(); s.observe(text)
    assert s.status==expected and s.action() is None


def test_stale_or_movable_container_is_not_falsely_assumed_accessible():
    m=model(); m.containers['bag']={'items':{'oak_log':1},'used':1,'capacity':2,'uncertain_after_craft':True}
    with pytest.raises(ResourceGap): from_public(m,observation(equipped='1 bag'),'oak_rod')
    m.containers['bag']['uncertain_after_craft']=False
    with pytest.raises(ResourceGap): from_public(m,observation(holding='1 bag'),'oak_rod')


def test_opportunity_oracle_and_frozen_exemptions_agree_with_search():
    p=problem(needs=3000,held=2000,bag=1000,modes=('exact',),access=('hand','hand_bag'))
    compiled=compile_resources(p,horizon=4)
    planner,proofs=opportunity_planner(compiled,600); frozen=planner.exempt
    oracle=planner.oracle()
    for h in range(1,5):
        solved=planner.solve(compiled.belief,h)
        assert solved.exact and solved.upper==oracle(compiled.belief,h)
    for branch in planner.branches(compiled.belief,'drop ore').values():
        planner.solve(branch,0)
    assert planner.exempt==frozen  # Never grant a new exemption after time/material is lost.
    unknown,proofs=opportunity_planner(compile_resources(problem(),horizon=3),0)
    assert not unknown.exempt and all('unresolved' in r['reason'] for r in proofs.values())


def test_checkpoint_reconstructs_same_policy_from_public_feedback():
    report,s=make_trial(model(),START,'oak_rod'); assert s.action()=='craft 1 oak_rod'
    s.observe(CRAFTED); pending=s.action()
    saved={'problem':asdict(s.compiled.domain.problem),'fingerprint':s.compiled.fingerprint,
           'options':OPTIONS,'feedback':[{'action':'craft 1 oak_rod','text':CRAFTED}],'pending_action':pending}
    resumed=restore_trial(json.loads(json.dumps(saved)))
    assert resumed.action()==pending and resumed.belief==s.belief
    resumed.observe(HELD); assert resumed.action() is None
    saved['pending_action']='drop oak_rod'
    with pytest.raises(ResourceGap): restore_trial(saved)


def test_v6_llm_selects_target_then_certified_continuation_uses_no_new_call():
    class Mock:
        step=0
        calls=0
        def generate(self,*args):
            self.calls+=1
            return {'response':json.dumps({'action':'craft 1 oak_rod','reasoning':'Need a rod.',
                'resource_target':'oak_rod','frame':{}}),'num_input_tokens':5,'num_output_tokens':5}
    llm=Mock(); agent=ResourceCompetitionAgent(llm,'Return JSON.')
    agent.notebook.prompt(observation('2 oak_log'))
    action,*_=agent.act({'text':START})
    assert action=='craft 1 oak_rod' and llm.calls==1
    saved=json.loads(json.dumps(agent.notebook.state()))
    restored=ResourceCompetitionAgent(llm,'Return JSON.'); restored.notebook.load(saved)
    llm.step=1
    action,tin,tout,raw=restored.act({'text':CRAFTED})
    assert action=='pick up oak_rod' and tin==tout==0 and llm.calls==1
    assert json.loads(raw)['decision_source']=='resource_competition'
    restored.observe_terminal({'text':HELD})
    assert restored.notebook.resource_trials[-1]['status']=='LOCAL_MILESTONE_CONFIRMED'


def test_missing_station_evidence_does_not_spend_search_budget():
    from scar_public.resource_agent import ResourceController, ResourceMemory
    memory=ResourceMemory(); memory.model=model()
    stations=dict(memory.model.stations); memory.model.stations.clear()
    controller=ResourceController(memory)
    proposal={'action':'craft 1 oak_rod','resource_target':'oak_rod','frame':{}}
    for step in range(8):
        assert controller.consider(proposal,START,step)==proposal
    assert memory.resource_attempts==[]
    memory.model.stations.update(stations)
    selected=controller.consider(proposal,START,8)
    assert selected['decision_source']=='resource_competition'
    assert len(memory.resource_attempts)==1
