import ast
import copy
import json
from pathlib import Path
from scar_unknown17.controller import SimpleController
from scar_unknown17_stage7.controller import Stage7Controller, FLAGS, CONFIGS


def obs(feedback='',location='room',hands='no objects',equipment='no objects',ground='no objects',neighbors='hall',step=0):
    return {'step':step,'text':f'Current Location: Test, {location}\n\n{feedback}\n\nI am holding {hands}.\nI have equipped {equipment}.\nI see {ground} near me.\nI see no one nearby.\nNeighboring areas: {neighbors}.\n'}


def controller(**flags):
    c=Stage7Controller(**flags);c.set_goal('craft 1 goal','Obtain at least 2 goal')
    c.table.observe(obs(hands='1 goal',ground='1 ore'))
    c.table.recipes['bar']={'ingredients':['ore'],'stations':['bench'],'quantities':None}
    return c


def test_station_retry_requires_correct_station_not_time_or_location():
    c=controller(retry_context_fix=True);o=obs(hands='1 ore')
    c.observe(o,'craft 1 bar',obs('Cannot craft bar. Missing necessary bench in the current area.',hands='1 ore'))
    assert not c.retry_allowed('craft 1 bar')
    c.table.observe(obs(location='hall',hands='1 ore',step=99))
    assert not c.retry_allowed('craft 1 bar')
    c.table.observe(obs(location='workshop',hands='1 ore',ground='1 bench',step=100))
    assert c.retry_allowed('craft 1 bar')


def test_material_retry_requires_relevant_gain():
    c=controller(retry_context_fix=True);o=obs(ground='1 bench');c.table.observe(o)
    c.observe(o,'craft 1 bar',obs('Cannot craft a single bar.',ground='1 bench'))
    c.table.observe(obs(location='hall',hands='1 apple',ground='1 bench',step=33))
    assert not c.retry_allowed('craft 1 bar')
    c.table.observe(obs(hands='1 ore',ground='1 bench'))
    assert c.retry_allowed('craft 1 bar')


def test_failed_forward_trial_retains_cost_not_effective_quota():
    c=controller(retry_context_fix=True);o=obs(hands='1 ore');c.table.observe(o)
    c.trials['bar']=1;c._probe('craft 1 bar','bounded forward recipe trial',{'recipe':'bar'})
    c.observe(o,'craft 2 bar',obs('Cannot craft bar. Missing necessary bench in the current area.',hands='1 ore'))
    assert c.trials['bar']==0 and c.attempt_log[-1]['actual_action_cost']==1
    assert not c.attempt_log[-1]['meaningful_trial']


def test_successful_inspection_not_repeated_same_state():
    c=controller(retry_context_fix=True);o=obs(hands='1 goal',ground='1 ore')
    c.table.inspected=['goal'];c.choose(o,'wait')
    c.observe(o,'inspect ore',obs('I inspected ore.',hands='1 goal',ground='1 ore'))
    assert c._explore({'goal'})!='inspect ore'


def test_gap_update_changes_priority_and_checks_new_product():
    c=controller(knowledge_gap_exploration=True)
    c.table.observe(obs(ground='1 x, 1 y'));c.table.recipes['goal']={'ingredients':['y']}
    assert c._explore({'goal'})=='inspect y'
    c.table.recipes['goal']={'ingredients':['x']};c.update_gap()
    assert 'x' in c.gap['known_dependency_nodes'] and 'y' not in c.gap['known_dependency_nodes']
    c.table.inspected=['x','y'];c.table.observe(obs(ground='1 fresh, 1 z'));c.last_produced='fresh'
    assert c._explore({'goal'})=='inspect fresh'


def test_ready_known_dependency_executes_ahead_of_unknown_head():
    c=controller(explore_execute_switch=True);c.queue=['unknown','bar'];c.queue_needs['bar']=1
    o=obs(hands='1 ore',ground='1 bench');a=c.choose(o,'inspect bench')
    assert a=='craft 2 bar' and c.execution_mode=='EXECUTE'
    assert c.last_choice['stage7']['C_ready_execution']['node']=='bar'


def test_execution_failure_records_local_recovery_without_queue_reset():
    c=controller(explore_execute_switch=True);c.queue=['goal','bar'];o=obs(hands='1 ore')
    c.observe(o,'craft 1 bar',obs('Cannot craft bar. Missing necessary bench in the current area.',hands='1 ore'))
    c._set_mode('inspect bench')
    assert c.execution_mode=='RECOVER' and c.queue==['goal','bar']
    assert c.blocked_execution['node']=='bar'


def test_batch_reserves_shared_downstream_inputs_and_keeps_unknown():
    c=controller(resource_goal_guard=True)
    c.table.recipes['goal']={'ingredients':['bar','ore']};c.queue_needs['bar']=1
    assert c._batch_action('craft 1 bar')=='craft 1 bar'
    b=c.stage7_decision['D_batch'];assert b['shared_inputs']==['ore'] and 'UNKNOWN' in b['quantity_truth']
    c.table.recipes['goal']={'ingredients':['bar']};c.queue_needs['bar']=3
    assert c._batch_action('craft 1 bar')=='craft 3 bar'


def test_exact_scope_sample_allows_efficient_batch_not_universal():
    c=controller(resource_goal_guard=True);o=obs(hands='2 ore',ground='1 bench')
    c.table.observe(o);c.quantity_facts.table.observe(o)
    c.quantity_facts.effects=[{'target':'bar','before_counts':{'ore':2},'actual':2,'requested':2,
        'consumed':{'ore':1},'location':'room','source_step':0}]
    assert c._batch_action('craft 1 bar')=='craft 2 bar'
    c.table.observe(obs(location='hall',hands='2 ore',ground='1 bench'))
    assert c._batch_action('craft 1 bar')=='craft 1 bar'


def test_visible_final_collection_preserves_base_and_no_extra_craft():
    c=controller(resource_goal_guard=True);o=obs(hands='1 goal',ground='1 goal, 1 ore')
    assert c.choose(o,'pick up goal')=='pick up goal'
    assert c.choose(o,'inspect ore')=='pick up goal'
    assert c.choose(obs(hands='2 goal'),'craft 1 goal')=='wait'


def test_final_store_accounts_for_already_held_copy():
    c=controller(resource_goal_guard=True);c.table.observe(obs(hands='1 goal, 1 ore',equipment='1 bag',ground='1 goal'))
    c.table.inventory='bag';c.table.containers['bag']={'counts':{},'load':0,'capacity':10,'location':'room','step':0}
    assert c._goal_action('inspect ore')[0]=='store 2 goal inventory'


def test_all_switches_roundtrip_and_independence():
    for flags in CONFIGS.values():
        c=controller(**flags);c.choose(obs(hands='1 goal',ground='1 ore'),'wait')
        clone=Stage7Controller.from_dict(json.loads(json.dumps(c.to_dict())))
        assert clone.to_dict()==c.to_dict()
        assert clone.flags==flags
        for name,key in [('retry_context_fix','A_suppressed'),('knowledge_gap_exploration','B_selection'),
                         ('explore_execute_switch','C_mode'),('resource_goal_guard','D_goal')]:
            if not flags[name]:assert key not in c.stage7_decision


def test_all_off_matches_original_controller_state_and_actions():
    old=SimpleController(True,'learned');new=Stage7Controller()
    for c in (old,new):c.set_goal('craft 1 goal','Obtain at least 2 goal')
    before=obs(hands='1 goal',ground='1 ore');after=obs('I inspected ore. It can be used to craft: bar (made of ore).',hands='1 goal',ground='1 ore')
    assert old.choose(before,'wait')==new.choose(before,'wait')
    for c in (old,new):c.observe(before,'inspect ore',after)
    assert old.choose(after,'wait')==new.choose(after,'wait')
    assert all(new.to_dict()[k]==v for k,v in old.to_dict().items())


def test_policy_no_hidden_truth_or_item_exceptions():
    for name in ['controller.py','agent.py']:
        text=(Path('scar_unknown17_stage7')/name).read_text();tree=ast.parse(text)
        imports=[n.module or '' for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
        assert not any(m.startswith(('scar.environment','scar_unknown17.audit','scar_sequence.evaluate')) for m in imports)
        assert not any(s in text for s in ['sequence-','bandage_roll','orrery_blade','recipe_graph','initial_snapshot'])


def test_public_numeric_recipe_demand_supports_two_without_hidden_quantities():
    c=controller(resource_goal_guard=True)
    c.table.recipes['goal']={'ingredients':['bar','ore']}
    o=obs(hands='2 ore')
    after=obs('I have acquired a new item: ore. It can be used to craft: goal (1 ore, 2 bar), bar (0.5 ore)',hands='2 ore')
    c.observe(o,'store 2 ore inventory',after)
    assert c.public_quantity_rules['bar']['quantities']=={'ore':0.5}
    # Start with one goal and two ore in a certified carried container.
    c.table.state['hands']={'goal':1,'bag':1}
    c.table.containers['bag']={'counts':{'ore':2},'load':2,'capacity':10,'location':'room','step':0}
    assert c._batch_action('craft 1 bar')=='craft 2 bar'
    assert c.table.recipes['bar']['quantities'] is None


def test_guard_does_not_consume_required_existing_final_copy():
    c=controller(resource_goal_guard=True);c.table.recipes['detour']={'ingredients':['goal']}
    assert c._batch_action('craft 1 detour')=='wait'
    assert 'D_protect_goal' in c.stage7_decision


def test_same_state_unknown_recipe_failure_is_not_retried():
    c=controller(retry_context_fix=True);o=obs(hands='1 ore')
    c.observe(o,'craft 1 mystery',obs("Cannot craft mystery. There's no way to craft this object.",hands='1 ore'))
    assert not c.retry_allowed('craft 1 mystery')
    c.table.observe(obs(location='hall',hands='1 ore',step=88))
    assert not c.retry_allowed('craft 1 mystery')


def test_recovery_mode_does_not_clear_on_unrelated_move():
    c=controller(explore_execute_switch=True);o=obs(hands='1 ore')
    c.observe(o,'craft 1 bar',obs('Cannot craft bar. Missing necessary bench in the current area.',hands='1 ore'))
    c.observe(o,'enter hall',obs(location='hall',hands='1 ore'))
    assert c.blocked_execution is not None
    c.observe(obs(location='hall',hands='1 ore'),'enter workshop',obs(location='workshop',hands='1 ore',ground='1 bench'))
    assert c.blocked_execution is None
