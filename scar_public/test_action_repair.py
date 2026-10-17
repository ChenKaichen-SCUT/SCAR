import copy,json
from scar_public.action_repair import ActionMemory,ActionController,capacity_candidates
from scar_public.evidence_repair import enabling_conditions
from scar_public.test_resource_evidence import floor_access_evidence


def fixture():
    m=ActionMemory();c=ActionController(m);task='Craft a blade and hold it in your hands.'
    text='[1] '+task+'\nCurrent Location: workshop\nI am holding 2 ore.\nI have equipped no objects.\nI see 1 ore, 1 pack, 1 bench near me.'
    m.prompt(text);m.frame=dict(goal_quote=task,method='Craft blade')
    m.model.capacity_lower=m.model.capacity_upper=2
    m.model.recipes={'blade':{'needs':{'ore':3},'quote':'blade (3 ore)'}}
    m.model.stations={'blade':{'name':'bench','quote':'Missing bench'}}
    m.model.containers={'pack':{'capacity':5,'items':{},'used':0}}
    m.model.source_lines.append('I equipped pack as inventory.')
    p,bank=floor_access_evidence();allowed,_=bank.query(p)
    conditions=enabling_conditions(p,allowed[p.target],'craft 1 blade')
    review=dict(action='craft 1 blade',original_task=task,enabling_conditions=conditions,evidence={'reused':True})
    return m,c,text,review


def test_obstruction_compiles_an_action_without_extra_language_call():
    m,c,text,review=fixture();event=c.compile_repair(review,text,10)
    assert event['chosen']['action']=='drop ore'
    r=c.activate(event,10)
    assert r['decision_source']=='evidence_action_program' and r['action_certificate']['extra_llm_calls']==0
    assert m.action_program['target']=='blade'


def test_no_observed_inventory_capability_no_program():
    m,c,text,review=fixture();m.model.source_lines=[]
    assert c.compile_repair(review,text,10) is None


def test_joint_capacity_must_actually_close_the_gap():
    m,c,text,review=fixture();m.model.containers['pack']['capacity']=0.5
    assert c.compile_repair(review,text,10) is None


def test_upstream_material_gap_is_not_mislabeled_capacity_repair():
    m,c,text,review=fixture()
    review['enabling_conditions']['profiles'][0]['total_material_deficit']['ore']=1
    assert c.compile_repair(review,text,10) is None


def test_failed_primitive_stops_program_instead_of_blindly_running_suffix():
    m,c,text,review=fixture();event=c.compile_repair(review,text,10);r=c.activate(event,10)
    m.last_action=r['action']
    assert c.method_condition_step(text+'\nCannot drop ore.',11) is None
    assert m.action_program is None and m.action_outcomes[-1]['reason']=='EXECUTION_NOT_CONFIRMED'


def test_target_visible_on_floor_skips_unnecessary_bag_observation():
    m,c,text,review=fixture();c.activate(c.compile_repair(review,text,10),10)
    m.action_program.update(pending=None,phase='acquire',refreshed=True)
    m.model.current.update(holding={},equipped={'pack':1},ground={'blade':1})
    m.model.containers['pack']['uncertain_after_craft']=True
    assert c.method_condition_step(text,11)['action']=='pick up blade'


def test_observation_and_execution_modes_compile_identical_candidate():
    m,c,text,review=fixture();other=copy.deepcopy(m);d=ActionController(other);d.action_mode='observe'
    assert c.compile_repair(review,text,10)==d.compile_repair(review,text,10)
    assert m.action_program is None and other.action_program is None


def test_checkpoint_preserves_pending_action_and_evidence():
    m,c,text,review=fixture();c.activate(c.compile_repair(review,text,10),10)
    restored=ActionMemory();restored.load(json.loads(json.dumps(m.state())))
    assert restored.action_program==m.action_program and restored.action_events==m.action_events


def test_late_budget_and_combat_decline_repair():
    m,c,text,review=fixture()
    assert c.compile_repair(review,text,299) is None
    assert c.compile_repair(review,text+'\nI was attacked by enemy.',10) is None


def test_combat_pauses_but_does_not_erase_confirmed_capability_progress():
    m,c,text,review=fixture();r=c.activate(c.compile_repair(review,text,10),10)
    m.last_action=r['action']
    assert c.method_condition_step(text+'\nI dropped ore.\nI was attacked by enemy.',11) is None
    assert m.action_program and m.action_program['pending'] is None
    assert m.action_outcomes[-1]['reason']=='PAUSED_FOR_COMBAT'


def test_broad_actor_goal_keeps_a_unique_public_task_binding_as_intention():
    m,c,text,review=fixture();task='Obtain a weapon.'
    m.model.tasks=[task];m.model.known_tasks=[task];m.model.source_lines.append('[1] '+task)
    m.update(dict(action='craft 1 blade',reasoning='Acquire a weapon for the pending task.',
        frame={'goal_quote':'Explore the world','method':'Craft blade'}),text,1)
    assert m.action_goal_bindings['blade']['task']==task
    assert 'not proof' in m.action_goal_bindings['blade']['qualification']


def test_changed_task_abandons_old_program_and_item_prefix_is_not_success():
    from scar_public.action_repair import acknowledged
    m,c,text,review=fixture();c.activate(c.compile_repair(review,text,10),10)
    m.model.tasks=[];m.intent_tasks={}
    assert c.method_condition_step(text,11) is None
    assert m.action_outcomes[-1]['reason']=='TASK_NO_LONGER_ACTIVE'
    assert not acknowledged('enter hall','I entered hallway.')
    assert not acknowledged('pick up ore','I picked up ore_shard.')
    assert not acknowledged('store 1 ore pack','I stored 1 wood in pack.')
    assert acknowledged('equip pack','I equipped pack as inventory.')


def test_resumed_run_reconstructs_ancestor_public_decisions(tmp_path):
    from scar_public.action_history import prefix_rows
    base=tmp_path/'base';child=tmp_path/'child'
    for run in (base,child):(run/'trace').mkdir(parents=True)
    (base/'manifest.json').write_text('{}')
    for step in (1,2):(base/'trace'/f'{step:04d}.json').write_text(json.dumps({'step':step}))
    parent=base/'checkpoints/0002'
    (child/'manifest.json').write_text(json.dumps({'diagnostic_fork':{'path':str(parent)}}))
    for step in (3,4):(child/'trace'/f'{step:04d}.json').write_text(json.dumps({'step':step}))
    assert [r['step'] for r in prefix_rows(child/'checkpoints/0004')]==[1,2,3,4]
