import json
from types import SimpleNamespace

from scar_public.continuation import ContinuationMemory, task_key
from scar_public.obstacle_repair import (ObstacleRepairAgent, missing_requirements,
    repair_programs, test_value as evaluate)
from scar_public.core_planner import CorePlannerAgent
from scar_public.public_model import PublicModel
from scar_public.test_continuation import obs


def case(held='1 rod', ground='1 metal, 1 club', place='hall'):
    text=obs(held=held,ground=ground,place=place)
    model=PublicModel();model.observe(text)
    model.recipes={'blade':dict(needs={'rod':1,'metal':1},quote='blade (1 rod, 1 metal)')}
    memory=SimpleNamespace(model=model,progress_tasks={})
    evidence=ContinuationMemory();evidence.observe(text,0)
    original=dict(action='enter vault',reasoning='Find supplies',frame=dict(goal_quote='Craft a blade and hold it.'),
                  core_packet=dict(focus=dict(target='blade')))
    return memory,evidence,original,['Craft a blade and hold it.']


def test_missing_material_generates_acquisition_not_unrelated_inspection():
    m,e,o,g=case();programs=repair_programs(m,o,g,e,'task',[],[])
    assert any(p['action']=='pick up metal' for p in programs)
    assert not any(p['action']=='inspect club' for p in programs)
    assert not any(p['target']=='rod' for p in programs)


def test_finished_output_does_not_require_reacquiring_consumed_ingredients():
    m,e,o,g=case(held='1 blade')
    assert missing_requirements(m,o,g)=={}
    assert repair_programs(m,o,g,e,'task',[],[])==[]


def test_material_location_is_real_public_observation_and_old_claim_can_fail():
    m,e,o,g=case(ground='1 club')
    m.model.locations['Estate, yard']=dict(objects={'metal':1},neighbors=['hall'])
    m.model.edges['Estate, hall']={'yard':'Estate, yard'}
    programs=repair_programs(m,o,g,e,'task',[],[])
    p=next(p for p in programs if p['action']=='enter yard' and p['target']=='metal')
    assert p['test']==dict(kind='visible',target='metal') and p['on_pass']=='pick up metal'
    assert evaluate(p['test'],obs(place='yard',ground='no objects')) is False
    assert evaluate(p['test'],'Current Location: Estate, yard') is None


def test_quantity_shortfall_is_not_hidden_by_one_held_unit():
    m,e,o,g=case(held='1 rod, 1 metal',ground='1 club')
    m.model.recipes['blade']['needs']['metal']=2
    assert 'metal' in missing_requirements(m,o,g)
    assert evaluate(dict(kind='visible',target='metal'),e.observation) is False


def test_known_capacity_prevents_impossible_pickup_and_no_forced_discard():
    m,e,o,g=case(held='1 rod, 1 token');m.model.capacity_lower=m.model.capacity_upper=2
    programs=repair_programs(m,o,g,e,'task',[],[])
    assert not any(p['action']=='pick up metal' or p['action'].startswith('drop ') for p in programs)


def test_attempt_scope_prevents_immediate_repeated_experiment_and_expires():
    m,e,o,g=case();programs=repair_programs(m,o,g,e,'task',[],[])
    p=next(p for p in programs if p['action']=='pick up metal')
    assert not any(x['scope']==p['scope'] for x in repair_programs(m,o,g,e,'task',[p],[]))
    e.step+=25
    assert any(x['scope']==p['scope'] for x in repair_programs(m,o,g,e,'task',[p],[]))


def test_inspection_does_not_match_unrelated_neighbor_list():
    t=dict(kind='content',target='key',contains='vault')
    assert evaluate(t,obs(feedback='I inspected key: A shiny item.')) is None
    assert evaluate(t,obs(feedback='I inspected key: Opens the vault.')) is True
    assert evaluate(t,obs(feedback='Nothing learned.')) is None


def test_renaming_preserves_the_dependency_program():
    for label in ('metal','resource_x','token_z'):
        m,e,o,g=case(ground='1 '+label+', 1 club')
        m.model.recipes['blade']['needs']={'rod':1,label:1}
        assert any(p['action']=='pick up '+label for p in repair_programs(m,o,g,e,'task',[],[]))


def test_nontriggered_actor_is_unchanged():
    class LLM:
        step=0
        def __init__(self):self.prompts=[]
        def generate(self,user,system):
            self.prompts.append((user,system))
            return dict(response=json.dumps(dict(action='talk to guide',reasoning='Get task',
                frame=dict(goal_quote='Visit the vault.',method='Talk',expected='Task instruction'))),
                num_input_tokens=1,num_output_tokens=1)
    a,b=CorePlannerAgent(LLM(),'JSON'),ObstacleRepairAgent(LLM(),'JSON')
    for step in range(2):
        for agent in (a,b):agent.llm.step=step
        x,y=a.act(dict(text=obs())),b.act(dict(text=obs()))
        assert x[:3]==y[:3] and a.llm.prompts==b.llm.prompts
        assert a.notebook.state()==b.notebook.state()


def pending_case():
    a=ObstacleRepairAgent(SimpleNamespace(step=2),'JSON');text=obs(held='1 key')
    a.continuation.observe(text,2);a.notebook.model.observe(text)
    a.obstacle_pending=dict(task=task_key(a.notebook),goal='Visit the vault.',condition='Acquire key',
        test=dict(kind='held',target='key'),on_pass='enter vault',on_fail='reconsider')
    a.repair_trigger=lambda action,task:None
    return a,text


def test_actual_condition_can_execute_continuation():
    a,text=pending_case()
    out=a.finalize_decision(dict(action='inspect note',frame={}),dict(text=text),2,'',lambda p:None)
    assert out['action']=='enter vault' and out['continuation']['reason']=='OBSERVED_TEST_SELECTS_CONTINUATION'


def test_task_change_threat_or_urgent_action_cancels_continuation():
    for mode in ('task','threat','urgent'):
        a,text=pending_case();original='inspect note'
        if mode=='task':a.notebook.progress_tasks['new']=dict(quote='Another task')
        if mode=='threat':text+='\nI was attacked by opponent.'
        if mode=='urgent':original='eat bread'
        out=a.finalize_decision(dict(action=original,frame={}),dict(text=text),2,'',lambda p:None)
        assert out['action']==original


def test_failed_execution_cannot_select_success_branch():
    a,text=pending_case();text+='\nCannot pick up key, not enough space in hand.'
    out=a.finalize_decision(dict(action='inspect note',frame={}),dict(text=text),2,'',lambda p:None)
    assert out['action']=='inspect note' and a.obstacle_outcomes[-1]['outcome'] is None
