import json
from scar_public.method_repair import (MethodMemory,MethodController,output_support,
    portfolio_check,joint_material_completion,task_binding,recipe_chain)


def fixture():
    m=MethodMemory();model=m.model
    task='Obtain and equip a weapon before engaging enemies.'
    model.observe('[1] '+task+'\nCurrent Location: workshop\nI am holding 1 wood, 1 thread.\n'
                  'I have equipped no objects.\nI see 1 wood, 1 bench near me.')
    model.recipes={'club':{'needs':{'wood':2,'thread':1},'quote':'club (2 wood, 1 thread)'},
                   'splint':{'needs':{'wood':1},'quote':'splint (1 wood)'}}
    m.method_commitment=dict(target='club',task=task,created=0,recipe=model.recipes['club'])
    return m,MethodController(m),task


def test_recipe_and_object_name_do_not_prove_task_role():
    m,c,task=fixture()
    report=c.assess_switch({'action':'craft 1 splint','task_quote':task})
    assert report['block'] and report['task_support']['status']=='UNKNOWN'
    assert report['resource']['displaced']
    assert all(r['increased_deficits']['club']['wood']==1 for r in report['resource']['profiles'])


def test_capacity_improvement_does_not_override_missing_goal_link():
    m,c,task=fixture();m.model.current['ground']['wood']=10
    report=c.assess_switch({'action':'craft 1 splint','task_quote':task})
    assert report['resource']['status']=='MATERIAL_OPTION_PRESERVED'
    assert report['block']  # plentiful materials do not prove a task role


def test_supported_alternative_releases_old_recipe_without_method_lock_in():
    m,c,task=fixture()
    m.model.source_lines.append('I inspected splint: A compact weapon for travel.')
    report=c.assess_switch({'action':'craft 1 splint','task_quote':task})
    assert not report['block']
    assert report['status']=='TASK_LINKED_METHOD_SWITCH'
    assert report['resource']['displaced']  # allowed because the same task has a supported alternative
    assert all(r['status']=='JOINT_MATERIAL_WITNESS' for r in report['joint_material_witnesses'])


def test_negated_category_description_is_not_positive_evidence():
    m,c,task=fixture();m.model.source_lines.append('I inspected splint: This is not a weapon.')
    assert output_support(m.model,'splint',task)['status']=='UNKNOWN'


def test_upstream_recipe_requires_supported_endpoint_and_remaining_inputs():
    m,c,task=fixture();m.model.recipes['mace']={'needs':{'splint':1,'stone':1},'quote':'mace (1 splint, 1 stone)'}
    m.model.source_lines.append('I inspected mace: A heavy weapon.')
    parsed={'action':'craft 1 splint','task_quote':task,'method_endpoint':'mace'}
    report=c.assess_switch(parsed)
    assert report['task_support']['status']!='UNKNOWN' and report['recipe_chain']
    assert report['status']=='ALTERNATIVE_RESOURCE_GAP'
    m.model.current['ground']['stone']=1
    assert not c.assess_switch(parsed)['block']


def test_shared_resource_is_not_counted_twice_across_remaining_tasks():
    m,c,task=fixture()
    m.model.recipes['axe']={'needs':{'wood':1},'quote':'axe (1 wood)'}
    m.model.recipes['box']={'needs':{'wood':2},'quote':'box (2 wood)'}
    m.model.source_lines.append('I inspected axe: A heavy weapon.')
    other='Craft a box and hold it in your hands.'
    m.model.known_tasks.append(other);m.model.tasks.append(other);m.model.source_lines.append(other)
    report=c.assess_switch({'action':'craft 1 axe','task_quote':task})
    assert report['status']=='ALTERNATIVE_RESOURCE_GAP'
    m.model.current['ground']['wood']=2
    assert not c.assess_switch({'action':'craft 1 axe','task_quote':task})['block']


def test_portfolio_preserves_disjunction_not_all_method_ingredients():
    routes=[{'target':'wooden','needs':{'wood':2}},{'target':'stone','needs':{'stone':1}}]
    effect=[{'mode':'exact','consume':{'wood':1},'produce':{'test':1}}]
    report=portfolio_check({'wood':2,'stone':1},routes,effect)
    assert report['status']=='MATERIAL_OPTION_PRESERVED'
    assert report['profiles'][0]['retained_routes']==['stone']


def test_task_word_equip_is_not_equated_with_command_equippability():
    m,c,task=fixture()
    # A real public completion report resolves the task even if command fails.
    m.model.observe('Stage completed: '+task+'\nCannot equip club, it is not equippable.')
    c.prepare_decision('',2)
    assert m.method_commitment is None
    assert m.method_outcomes[-1]['outcome']=='PUBLIC_COMPLETION'


def test_material_witness_is_joint_and_cycle_bounded():
    m,c,task=fixture()
    assert joint_material_completion(m.model,{'wood':2,'thread':1},[('club',1)])['status']=='JOINT_MATERIAL_WITNESS'
    assert joint_material_completion(m.model,{'wood':2,'thread':1},[('club',1),('splint',1)])['missing']
    m.model.recipes['wood']={'needs':{'splint':1},'quote':'wood (1 splint)'}
    assert joint_material_completion(m.model,{},[('splint',1)])['missing']


def test_evidenced_container_enabler_uses_no_item_name_heuristic():
    m,c,task=fixture();model=m.model
    model.capacity_lower=2;model.capacity_upper=2
    model.containers['xyz']={'capacity':20,'items':{}}
    model.current['ground']['xyz']=1
    assert c.enabling_action('',2) is None
    model.source_lines.append('I equipped xyz as inventory.')
    p=c.enabling_action('',2)
    assert p['action'].startswith('drop ')
    assert not p['action'].startswith('craft ')


def test_unknown_task_binding_cannot_create_supported_alternative():
    m,c,task=fixture()
    assert task_binding(m.model,dict(frame={'goal_quote':'invented goal'}),'club')==''
    assert output_support(m.model,'splint','invented goal')['status']=='UNKNOWN'


def test_checkpoint_roundtrip_retains_method_audit():
    m,c,task=fixture();m.method_reviews.append({'status':'UNSUPPORTED_METHOD_SUBSTITUTION'})
    other=MethodMemory();other.load(json.loads(json.dumps(m.state())))
    assert other.method_commitment==m.method_commitment
    assert other.method_reviews==m.method_reviews


def test_death_during_navigation_does_not_ground_loss_at_departure():
    from scar_public.method_repair import observed_loss_sites
    m,_,_=fixture()
    m.observations=['Current Location: origin\nI have equipped 1 bag.\nI am holding no objects.',
                    'I revived but lost all items in hand, equipped items, and inventory items at the place I died.']
    m.ledger='Action 0: enter destination\n'
    assert observed_loss_sites(m,'bag')==[]
    m.ledger='Action 0: attack creature\n'
    assert observed_loss_sites(m,'bag')==['origin']
