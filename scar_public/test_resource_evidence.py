import json
from dataclasses import replace

import pytest

from scar_public.resource_competition import compile_resources, ResourceGap
from scar_public.resource_agent import (PersistentResourceAgent, PersistentResourceController,
                                      PersistentResourceMemory)
from scar_public.resource_evidence import EvidenceBank, evidence_context
from scar_public.resource_trial import make_trial, from_public
from scar_public.test_resource_trial import model, START, CRAFTED, HELD, observation
from scar_public.test_resource_competition import problem


def learned():
    bank=EvidenceBank()
    _,session=make_trial(model(),START,'oak_rod')
    p=session.compiled.domain.problem
    _,meta=bank.query(p)
    session.action(); event=session.observe(CRAFTED)
    bank.observe(session.compiled,event,meta['epoch'])
    return bank,p,session


def test_elimination_survives_new_quantities_without_splitting_joint_parameters():
    p=problem(bag=1000,access=('hand','hand_bag'),modes=('exact','ceil_batch'))
    pairs={'blade':[('exact','hand'),('ceil_batch','hand_bag')]}
    c=compile_resources(p,horizon=2,allowed_profiles=pairs)
    assert len(c.models)==2
    assert {x for a in c.aliases.values() for x in a['blade']}==set(pairs['blade'])
    with pytest.raises(ResourceGap): compile_resources(p,allowed_profiles={'blade':[]})
    with pytest.raises(ResourceGap): compile_resources(p,allowed_profiles={'other':[('exact','hand')]})


def test_aliases_are_lifted_before_batch_size_changes():
    bank,p,_=learned()
    allowed,meta=bank.query(p)
    assert meta['reused'] and meta['raw_profiles_before']==12 and meta['raw_profiles_after']==8
    assert {q for q,a in allowed['oak_rod']}=={'ceil_batch','ceil_per_output'}
    # A one-item test cannot distinguish these two rounding semantics.
    new=replace(p,recipes=(replace(p.recipes[0],quantities=(1,2)),))
    assert evidence_context(new)[0]==evidence_context(p)[0]
    c=compile_resources(new,horizon=2,allowed_profiles=bank.query(new)[0])
    assert {h['oak_rod'][0] for h in c.hypotheses.values()}=={'ceil_batch','ceil_per_output'}


def test_transient_counts_transfer_but_guard_changes_do_not():
    bank,p,_=learned()
    assert bank.query(replace(p,holding={'oak_log':2000}))[1]['reused']
    variants=[replace(p,hand_capacity=3000),replace(p,bag_name='new_bag'),
        replace(p,start_location='other'),replace(p,source={**p.source,'equipment':{'gloves':1}}),
        replace(p,source={**p.source,'station':'new station evidence'}),
        replace(p,recipes=(replace(p.recipes[0],needs=(('oak_log',1000),)),))]
    for new in variants: assert not bank.query(new)[1]['reused']


def test_search_failure_is_not_evidence_and_mismatch_revokes_epoch():
    bank,p,session=learned()
    with pytest.raises(ResourceGap):
        bank.observe(session.compiled,dict(status='NO_INITIALLY_VIABLE_CANDIDATE'),0)
    assert bank.query(p)[1]['reused']
    bank.observe(session.compiled,dict(status='MODEL_MISMATCH'),0)
    assert not bank.query(p)[1]['reused'] and bank.query(p)[1]['epoch']==1
    with pytest.raises(ResourceGap): bank.observe(session.compiled,session.events[0],0)


def test_guarded_ledger_and_filtered_policy_survive_notebook_reload():
    class Mock:
        step=0; calls=0
        def generate(self,*args):
            self.calls+=1
            return dict(response=json.dumps(dict(action='craft 1 oak_rod',resource_target='oak_rod',frame={})),
                        num_input_tokens=5,num_output_tokens=5)
    llm=Mock(); agent=PersistentResourceAgent(llm,'Return JSON.')
    agent.notebook.prompt(observation('2 oak_log'))
    assert agent.act({'text':START})[0]=='craft 1 oak_rod'
    assert agent.act({'text':CRAFTED})[0]=='pick up oak_rod'
    restored=PersistentResourceAgent(llm,'Return JSON.')
    restored.notebook.load(json.loads(json.dumps(agent.notebook.state())))
    restored.observe_terminal({'text':HELD})
    p=from_public(model(),START,'oak_rod')
    assert EvidenceBank(restored.notebook.resource_evidence).query(p)[1]['reused']
    restored.notebook.model=model()
    selected=restored.resource_controller.consider(dict(action='craft 1 oak_rod'),START,3)
    assert selected['decision_source']=='resource_competition'
    assert restored.notebook.resource_trial_state['allowed_profiles']
    from scar_public.resource_agent import restore_trial
    s=restore_trial(json.loads(json.dumps(restored.notebook.resource_trial_state)))
    assert s.action()==selected['action']
    assert len(s.compiled.models)==2
    assert llm.calls==1  # Persistence does not add LLM calls or a prompt treatment.


def test_matched_state_planning_uses_evidence_without_feedback_prompt_change():
    from scar_public.resource_agent import ResourceController, ResourceMemory
    bank,p,_=learned()
    proposal=dict(action='craft 1 oak_rod')
    ordinary=ResourceMemory(); ordinary.model=model()
    persistent=PersistentResourceMemory(); persistent.model=model(); persistent.resource_evidence=bank.state
    assert ordinary.resource_feedback()==persistent.resource_feedback()
    fresh=ResourceController(ordinary); reuse=PersistentResourceController(persistent)
    fresh.consider(proposal,START,3); reuse.consider(proposal,START,3)
    assert len(fresh.session.compiled.models)==4
    assert len(reuse.session.compiled.models)==2
    assert persistent.resource_trials[-1]['selection']['persistent_evidence']['reused']


@pytest.mark.parametrize('feedback',[CRAFTED.replace('1 oak_rod','2 oak_rod'),
                                    CRAFTED+'\nI was attacked and lost 1 HP.'])
def test_controller_revokes_persistent_rules_after_invalid_feedback(feedback):
    bank,p,_=learned()
    memory=PersistentResourceMemory(); memory.model=model(); memory.resource_evidence=bank.state
    controller=PersistentResourceController(memory)
    selected=controller.consider(dict(action='craft 1 oak_rod'),START,1)
    memory.last_action=selected['action']
    assert controller.resume(feedback) is None
    assert memory.resource_trial_state is None
    allowed,meta=EvidenceBank(memory.resource_evidence).query(p)
    assert allowed is None and meta['epoch']==1


def test_information_has_action_value_only_in_a_relevant_state():
    from scar_public.resource_competition import select_experiment
    allowed={'blade':[('exact','hand_bag')]}
    for held,expected in ((0,('3','2')),(1000,('2','2'))):
        p=problem(needs=1000,held=held,bag=1000,modes=('exact',),access=('hand','hand_bag'))
        costs=[]
        for filtering in (None,allowed):
            compiled=compile_resources(p,horizon=4,allowed_profiles=filtering)
            result,_,_=select_experiment(compiled,mode='strong',max_extra_actions=0)
            costs.append(result['worst_total_actions'])
        assert tuple(costs)==expected
