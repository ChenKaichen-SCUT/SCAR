import ast
import copy
from pathlib import Path
from scar_sequence.public import ResourceTable
from scar_sequence.planner import Controller


def obs(feedback='',location='room',hands='no objects',equipment='no objects',ground='no objects',neighbors='hall',step=0):
    return {'step':step,'text':f'Current Location: Test, {location}\n\n{feedback}\n\nI am holding {hands}.\nI have equipped {equipment}.\nI see {ground} near me.\nI see no one nearby.\nNeighboring areas: {neighbors}.\n'}


def test_missing_observation_is_unknown():
    t=ResourceTable().observe(obs(hands='1 cloth'))
    t.observe({'step':1,'text':'A flash of darkness obscures the room.'})
    assert t.count('cloth') is None


def test_unlocked_scope_and_unseen_edge():
    t=ResourceTable().observe(obs())
    t.observe(obs('Cannot enter hall, the door is locked.'),'enter hall')
    assert t.enter_status('hall')=='REJECT'
    assert t.enter_status('cellar')=='UNKNOWN'
    t.observe(obs('I used a key to unlock the path to hall. I entered hall.',location='hall'),'enter hall')
    assert t.enter_status('room')=='UNKNOWN'  # reverse direction was not observed
    t.observe(obs('I entered room.'),'enter room')
    assert t.enter_status('hall')=='UNLOCKED'


def test_ground_container_is_not_portable_inventory():
    t=ResourceTable().observe(obs(ground='1 satchel_0'))
    t.observe(obs('I inspected satchel_0: It contains: 2 cloth (capacity: 2/10).',ground='1 satchel_0'),'inspect satchel_0')
    assert t.count('cloth')==0 and t.access('satchel_0')
    t.observe(obs('I entered hall.',location='hall'),'enter hall')
    assert t.count('cloth')==0 and t.access('satchel_0') is False
    assert t.containers['satchel_0']['location']=='room'


def test_quantity_evidence_and_invalidation():
    t=ResourceTable().observe(obs(hands='1 satchel_0'))
    t.observe(obs('I inspected satchel_0: It contains: 2 cloth (capacity: 2/10).',hands='1 satchel_0'),'inspect satchel_0')
    t.observe(obs('I successfully crafted 1 lining. It is on the ground.',hands='1 satchel_0',ground='1 lining'),'craft 1 lining')
    assert t.count('cloth') is None
    t.observe(obs('I inspected satchel_0: It contains: no objects (capacity: 0/10).',hands='1 satchel_0',ground='1 lining'),'inspect satchel_0')
    assert t.recipes['lining']['quantities']=={'cloth':2}
    t.observe(obs('It can be used to craft: lining (made of cloth).'),'inspect cloth')
    assert t.recipes['lining']['quantities']=={'cloth':2}


def test_goal_and_dependency_persist_across_locations_and_save():
    c=Controller();c.set_goal('craft 1 blade','Obtain at least 2 blade')
    c.graph={'blade':{'dependencies':['bar'],'status':'pending'}}
    c.observe(obs(), 'enter hall',obs('I entered hall.',location='hall'))
    restored=Controller.from_dict(copy.deepcopy(c.to_dict()))
    assert restored.target==c.target and restored.graph==c.graph and restored.amount==2


def test_fifo_retains_quantity_of_unsatisfied_head():
    c=Controller('fifo');c.set_goal('craft 1 blade','Obtain at least 1 blade')
    c.table.observe(obs(ground='2 bar',hands='1 bar'))
    c.table.recipes={'blade':{'ingredients':['bar'],'quantities':{'bar':2}}}
    assert c.choose(obs(ground='2 bar',hands='1 bar'),'wait')=='pick up bar'
    assert c.queue_needs['bar']==2


def test_goal_switch_cancels_old_graph_explicitly():
    c=Controller();c.set_goal('pick up bag','Follow the current publicly announced task.',True)
    c.graph={'bag':{'status':'pending'}}
    c.observe(obs(),'pick up bag',obs('I picked up bag.\nRequired action: `equip bag`',hands='1 bag'))
    assert c.target=='equip bag' and c.graph=={}
    assert any(e['event']=='goal_cancelled' for e in c.events)


def test_policy_import_boundary():
    for name in ['public.py','planner.py','agent.py']:
        tree=ast.parse((Path('scar_sequence')/name).read_text())
        imports=[n.module or '' for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
        assert not any(x.startswith(('scar.environment','scar_sequence.build','scar_sequence.evaluate','scar_sequence.supplement','scar_attribution','scar_v3.hard')) for x in imports)
