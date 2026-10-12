import copy
import pytest
from scar_stage14.test_knowledge import native,names,quantities
from scar_stage15.knowledge import PublicTable,PublicFacts15
from scar_stage15.controller import Controller15,SWITCHES
from scar_stage14.common import load

@pytest.mark.parametrize('row',load('results/stage14/parser_gold.json')['rows'],ids=lambda r:r['id'])
def test_gold_online(row):
    t=PublicTable();t.observe(row['observation'],row['action']);gold=row['expected']
    assert {n:set(r['ingredients']) for n,r in t.recipes.items() if r['ingredients']}=={n:set(v) for n,v in gold['recipes'].items()}
    assert {n:r['quantities'] for n,r in t.recipes.items() if r['quantities']}==gold['quantities']


def ctrl(method='P6'):
    c=Controller15(method);c.set_goal('craft 1 final','Obtain at least 2 final')
    c.table.state={'location':'room','ground':{},'hands':{'final':1},'equipment':{},'neighbors':['next'],'step':10,'feedback':''}
    c.table.places={'room':{'objects':{},'step':10}};c.table.links={'room':['next']}
    return c


def test_upgrades_not_overwritten_and_serialized():
    t=PublicTable();t.observe(names(),'inspect ore');assert t.recipes['bar']['quantities'] is None
    t.observe(quantities(),'pick up ore');t.observe(names(3),'inspect ore')
    assert t.recipes['bar']['quantities']=={'ore':.5,'fuel':2}
    u=PublicTable(**t.to_dict());assert u.to_dict()==t.to_dict()
    assert len(u.knowledge15.events)==3
    u.observe(names(3));assert len(u.knowledge15.events)==3


def test_conflict_retracts_actionable_recipe():
    t=PublicTable();t.observe(names(),'inspect ore')
    t.observe(native('I inspected ore: Rock.\nIt can be used to craft: bar (made of ore, wood).',2),'inspect ore')
    assert 'bar' not in t.recipes


def test_model_summary_exact_unknown_and_decimal():
    f=PublicFacts15();f.observe(names(),'pick up ore',quantities())
    records=f.records(quantities());r=next(x for x in records if x['kind']=='recipe')
    assert r['value']['quantities']=={'ore':.5,'fuel':2}
    assert PublicFacts15.from_dict(f.to_dict()).to_dict()==f.to_dict()


def test_no_untrusted_legacy_recipe_promotion():
    t=PublicTable();t.observe(native('A storyteller says sword (made of ore, fuel).'),'talk to bard')
    assert not t.recipes


def test_quantity_does_not_shrink_unknown_batch():
    c=ctrl('P2');c.table.recipes={'bar':{'ingredients':['ore'],'quantities':None}}
    assert c.quantity('craft 2 bar')[0]=='craft 2 bar'


def test_quantity_shared_nominal_demands_not_times_outputs():
    c=ctrl('P2');c.table.recipes={'final':{'ingredients':['a','b'],'quantities':{'a':1,'b':1}},
      'a':{'ingredients':['bar'],'quantities':{'bar':2}},'b':{'ingredients':['bar'],'quantities':{'bar':1}},'bar':{'ingredients':['ore'],'quantities':{'ore':1}}}
    c.table.state['hands']['ore']=1
    demand,_=c.demand();assert demand['bar']==3
    a,m=c.quantity('craft 2 bar');assert a=='craft 3 bar' and m['batch_expected_consumption']=='UNKNOWN'


def test_known_shortfall_acquired_not_repeated_craft():
    c=ctrl('P2');c.table.state['ground']={'ore':1};c.table.recipes={'bar':{'ingredients':['ore'],'quantities':{'ore':1}}}
    a,m=c.quantity('craft 2 bar');assert a=='pick up ore' and m['reason']=='acquire_explicit_nominal_shortfall'


def test_direct_final_possession_not_production():
    c=ctrl('P3');assert c.direct_finish('wait')[0] is None
    c.table.state['ground']={'final':1};assert c.direct_finish('wait')[0]=='pick up final'
    c.table.state['hands']={'final':2};assert c.direct_finish('wait')[0] is None


def test_finish_does_not_invent_missing_recipe():
    c=ctrl('P3');assert c.finish('wait')[0] is None
    c.table.recipes={'final':{'ingredients':['a'],'quantities':{'a':1}}}
    assert c.finish('wait')[0] is None
    c.table.state['hands']['a']=1;assert c.finish('wait')[0]=='craft 1 final'
    c.step15=39;assert c.finish('wait')[0] is None


def test_protection_public_dependency_departure_and_risk():
    c=ctrl('P4');c.table.state['ground']={'ore':1,'unrelated':2};c.table.recipes={'final':{'ingredients':['ore'],'quantities':{'ore':1}}}
    assert c.protect('inspect final')[0] is None
    assert c.protect('enter next')[0]=='pick up ore'
    c.risk15=True;assert c.protect('enter next')[0] is None
    c.risk15=False;c.table.recipes={};assert c.protect('enter next')[0] is None


def test_protection_hand_capacity_and_direct_priority():
    c=ctrl('P4');c.table.recipes={'final':{'ingredients':['ore'],'quantities':{'ore':1}}};c.table.state['ground']={'ore':1,'final':1}
    assert c.protect('enter next')[0] is None
    c.table.state['ground'].pop('final');c.table.state['hands']['tool']=1
    assert c.protect('enter next')[0] is None


def test_continuation_requires_actual_acceptance_quota_and_stops():
    c=ctrl('P5');c.table.recipes={'bar':{'ingredients':['ore'],'quantities':{'ore':1}}};c.table.state['ground']={'ore':1}
    c.exploration_spent=18;assert c.continuation_next()[0] is None
    c.intent15={'product':'bar','actual_actions':1,'produced':False};c.exploration_spent=17
    assert c.continuation_next()[0] is None
    c.exploration_spent=18;assert c.continuation_next()[0]=='pick up ore'
    c.risk15=True;assert c.continuation_next()[0] is None
    c.risk15=False;c.continuation_used15=7;assert c.continuation_next()[0] is None
    c.continuation_used15=0;c.intent15['stopped']='first_failed_continuation_action';assert c.continuation_next()[0] is None


def test_continuation_no_missing_material_or_station_exploration():
    c=ctrl('P5');c.exploration_spent=18;c.intent15={'product':'bar','actual_actions':1,'produced':False}
    c.table.recipes={'bar':{'ingredients':['ore'],'quantities':{'ore':1}}}
    assert c.continuation_next()[0] is None
    c.table.state['hands']['ore']=1;c.table.recipes['bar']['stations']=['furnace']
    assert c.continuation_next()[0] is None


def test_independent_switches_and_roundtrip():
    for m,flags in SWITCHES.items():
        c=ctrl(m);assert c.modules15==list(flags)
        assert Controller15.from_dict(c.to_dict()).to_dict()==c.to_dict()


def test_restore_does_not_mutate_serialized_input():
    c=ctrl();c.quantity_facts.effects=[{'target':'bar','consumed':{'ore':1}}]
    data=copy.deepcopy(c.to_dict());before=copy.deepcopy(data);restored=Controller15.from_dict(data)
    restored.table.state['hands']['ore']=100
    restored.quantity_facts.effects[0]['consumed']['ore']=20
    assert data==before
