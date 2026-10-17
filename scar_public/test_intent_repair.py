import copy,json
from scar_public.intent_repair import (IntentMemory,IntentController,IntentRepairAgent,
    update_tasks,task_view,proposed_intent,dependency_path)

OBS='Current Location: workshop\nI am holding 1 wood, 1 thread.\nI have equipped no objects.\nI see 1 wood, 1 bench near me.'

def setup():
    m=IntentMemory();m.model.observe(OBS)
    m.model.recipes={'club':{'needs':{'wood':2,'thread':1},'quote':'club (2 wood, 1 thread)'},
                    'splint':{'needs':{'wood':1},'quote':'splint (1 wood)'},
                    'sword':{'needs':{'splint':1,'metal':1},'quote':'sword (1 splint, 1 metal)'}}
    task='Obtain and equip a weapon.'
    text='giver says: '+task
    m.model.observe(text+'\n'+OBS);update_tasks(m.intent_tasks,text,0)
    c=IntentController(m);c.intervention_mode='enforce'
    return m,c,task

def proposal(task,output,**kwargs):
    return dict(action='craft 1 '+output,reasoning='A tentative method.',
        frame=dict(goal_quote=task,method='Craft '+output,assessment='Testing',expected='Observe'),**kwargs)

def test_npc_tasks_are_read_without_mutating_the_shared_actor_prompt():
    m,c,task=setup()
    assert m.model.tasks==[] and task in c.view().tasks
    update_tasks(m.intent_tasks,'giver says: Craft a sword and hold it in your hands.',1)
    assert task not in c.view().tasks
    assert task not in m.model.completed

def test_unrelated_dialogue_is_not_a_task_and_quotes_cannot_invent_one():
    m,c,task=setup();update_tasks(m.intent_tasks,'stranger says: A sword is expensive.',1)
    assert 'stranger' not in m.intent_tasks
    assert c.assess(proposal('invented task','splint'),2,'test')['status']=='UNBOUND_TASK'

def test_first_switch_is_checked_without_a_craft_failure_or_station_grounding():
    m,c,task=setup()
    assert c.assess(proposal(task,'club'),0,'test')['status']=='NEW_PROVISIONAL_METHOD'
    r=c.assess(proposal(task,'splint'),1,'test')
    assert r['status']=='UNSUPPORTED_ENDPOINT_SWITCH' and r['would_intervene']
    assert not m.resource_decision_rejections and not m.model.stations

def test_automatic_upstream_recognition_preserves_final_task_identity():
    m,c,_=setup();task='Craft a sword and hold it in your hands.'
    m.model.source_lines.append('giver says: '+task);update_tasks(m.intent_tasks,'giver says: '+task,1)
    p=proposal(task,'splint')
    assert c.assess(p,1,'test')['intent']['endpoint']=='sword'
    r=c.assess(p,2,'test')
    assert r['status']=='SUPPORTED_UPSTREAM_STEP' and not r['would_intervene']

def test_falsely_naming_old_endpoint_does_not_bypass_dependency_check():
    m,c,task=setup();c.assess(proposal(task,'club'),0,'test')
    r=c.assess(proposal(task,'splint',method_endpoint='club'),1,'test')
    assert r['status']=='UPSTREAM_LINK_UNSUPPORTED' and r['would_intervene']

def test_qualitative_dependency_can_explain_intent_without_claiming_quantities():
    m,c,task=setup();m.model.qualitative_recipes['staff']=['splint','gem']
    p=dependency_path(m.model,'splint','staff')
    assert p and p[0]['numeric'] is False and p[0]['needs'] is None

def test_two_downstream_branches_stay_ambiguous():
    m,c,task=setup();m.model.recipes['wand']={'needs':{'splint':1},'quote':'wand (1 splint)'}
    p=proposal(task,'splint');p['frame']['method']='Craft splint then sword or wand.'
    assert proposed_intent(c.view(),p,{})['endpoint']==''

def test_observe_mode_logs_the_same_gate_without_changing_action_or_calling_llm():
    m,c,task=setup();c.assess(proposal(task,'club'),0,'test');c.intervention_mode='observe'
    p=proposal(task,'splint')
    def forbidden(*args):raise AssertionError('observe mode cannot add LLM calls')
    assert c.select_proposal(p,OBS,1,forbidden,'prompt')==p
    assert m.intent_audits[-1]['would_intervene'] and not m.intent_interventions

def test_enforcement_calls_one_revision_and_records_action_mediation():
    m,c,task=setup();c.assess(proposal(task,'club'),0,'test');calls=[]
    def revise(prompt):calls.append(prompt);return dict(action='inspect wood',reasoning='Inspect',frame={})
    r=c.select_proposal(proposal(task,'splint'),OBS,1,revise,'prompt')
    assert r['action']=='inspect wood' and len(calls)==1
    assert m.intent_interventions[-1]['action_changed']

def test_supported_replacement_does_not_lock_original_materials():
    m,c,task=setup();c.assess(proposal(task,'club'),0,'test')
    m.model.source_lines.append('I inspected splint: A simple weapon.')
    r=c.assess(proposal(task,'splint'),1,'test')
    assert r['status']=='SUPPORTED_SWITCH_WITH_MATERIAL_WITNESS' and not r['would_intervene']
    assert r['details']['material_options']['displaced']

def test_actor_system_prompt_does_not_depend_on_enforcement_mode():
    a=IntentRepairAgent(None,'system');b=IntentRepairAgent(None,'system')
    b.resource_controller.intervention_mode='observe'
    assert a.system_prompt==b.system_prompt
    assert a.notebook.prompt(OBS)==b.notebook.prompt(OBS)
    assert a.resource_controller.intervention_mode=='observe'

def test_memory_restores_audits_and_anchors():
    m,c,task=setup();c.assess(proposal(task,'club'),0,'test')
    restored=IntentMemory();restored.load(json.loads(json.dumps(m.state())))
    assert restored.intent_anchors==m.intent_anchors and restored.intent_audits==m.intent_audits


def test_navigation_and_information_are_not_blocked_by_unknown_role():
    m,c,task=setup();c.assess(proposal(task,'club'),0,'test')
    for action in ('enter hall','inspect splint','pick up wood','drop wood'):
        p=proposal(task,'splint',resource_target='splint');p['action']=action
        r=c.assess(p,1,'test')
        assert r['status']=='PREPARATION_NOT_CONSUMPTION' and not r['would_intervene']


def test_unresolved_review_is_bounded_and_does_not_create_inspection_loops():
    m,c,task=setup();c.assess(proposal(task,'club'),0,'test');calls=[]
    p=proposal(task,'splint')
    def insist(prompt):calls.append(prompt);return copy.deepcopy(p)
    first=c.select_proposal(p,OBS,1,insist,'prompt')
    second=c.select_proposal(p,OBS,2,insist,'prompt')
    assert first['action']==second['action']=='craft 1 splint'
    assert len(calls)==1 and first.get('intent_unresolved') and second.get('intent_review_reuse')


def test_actual_executor_change_is_recorded_even_if_revision_was_overridden():
    m,c,task=setup();c.assess(proposal(task,'club'),0,'test')
    def revise(prompt):return dict(action='inspect wood',reasoning='Inspect',frame={})
    c.select_proposal(proposal(task,'splint'),OBS,1,revise,'prompt')
    p=proposal(task,'splint');c.after_decision(p,OBS,1)
    assert m.intent_interventions[-1]['action_changed']
    assert not m.intent_interventions[-1]['final_action_changed']
