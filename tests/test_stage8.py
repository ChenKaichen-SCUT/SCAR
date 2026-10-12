import copy
from scar_stage8.controller import ReliableController,make_controller,NoCandidate

def controller(method='P3'):
    c=make_controller(method);c.set_goal('craft 1 final','Obtain at least 2 final')
    c.table.state={'location':'a','hands':{'final':1},'equipment':{'bag':1},'ground':{},'neighbors':[]}
    c.table.inventory='bag';c.table.containers={'bag':{'counts':{},'load':0,'capacity':20,'location':'a','step':0,'source':'test'}}
    return c

def test_transfer_semantics():
    c=controller();c.table.state['hands']={};c.table.state['ground']={'final':2}
    assert c.collection('final',2,'store 2 final inventory')=='store 2 final inventory'

def test_held_copy_store_count():
    c=controller();c.table.state['ground']={'final':1}
    assert c.collection('final',2)=='store 2 final inventory'

def test_hand_full_pickup_blocked():
    c=controller();c.table.state['hands']['raw']=1;c.table.state['ground']={'final':1}
    assert not c.admissible('pick up final')

def test_historical_not_current():
    c=controller();c.table.places={'b':{'objects':{'final':2}}}
    assert c.collection('final',2) is None

def test_already_owned():
    c=controller();c.table.state['hands']={'final':2};c.table.state['ground']={'final':1}
    assert c.collection('final',2) is None
    assert not c.admissible('pick up final')

def test_failed_pickup_context():
    c=controller();c.table.state['ground']={'final':1};a='pick up final'
    c.failed_actions[c.failure_key(a)]={'context':c.action_context(a),'target':'final'}
    assert not c.admissible(a)
    c.table.state['step']=100;c.table.state['feedback']='unrelated';assert not c.admissible(a)
    c.table.state['ground']['final']=2;assert c.admissible(a)

def test_no_duplicate_product():
    c=controller();c.table.state['ground']={'cord':2};c.queue_needs={'cord':2}
    assert c.protect_craft('craft 2 cord','store 2 cord inventory')=='store 2 cord inventory'

def test_no_owned_goal_consumption():
    c=controller();c.table.recipes={'downstream':{'ingredients':['final']}}
    assert c.protect_craft('craft 1 downstream','craft 1 downstream') is None

def test_unknown_station_safe():
    c=controller('P4');c.table.recipes={'product':{'ingredients':['raw'],'stations':['bench']}}
    try:c._station('product')
    except NoCandidate:pass
    else:assert False
    assert c.solving==[]

def test_cycle_guard():
    c=controller()
    try:
        with c.solving_node('a'):
            with c.solving_node('a'):pass
    except NoCandidate:pass
    else:assert False
    assert not c.solving

def test_station_retry():
    c=controller();c.table.recipes={'product':{'ingredients':['raw'],'stations':['bench']}}
    c.retry_records={'craft:product':{'state':'BLOCKED_BY_PRECONDITION','failure_type':'station','context':c.public_context('product')}}
    assert not c.retry_allowed('craft 1 product')
    c.table.state['ground']['bench']=1;assert c.retry_allowed('craft 1 product')

def test_restore_all_state():
    c=controller();c.failed_actions={'x':{'context':{'a':1}}};c.no_progress={'x':2}
    d=ReliableController.from_dict(copy.deepcopy(c.to_dict()));assert d.to_dict()==c.to_dict()

def test_full_container_and_unknown_contents():
    c=controller();c.table.state['ground']['final']=2;c.table.containers['bag'].update(load=20,counts=None)
    assert not c.admissible('store 1 final inventory')
    assert not c.admissible('take out raw inventory')

def test_no_volume_assumption():
    c=controller();c.table.containers['bag']['load']=None;c.table.state['hands']={'raw':2};c.table.state['ground']['final']=1
    assert c.collection('final',2) is None
