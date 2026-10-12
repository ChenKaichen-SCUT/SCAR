import ast
import copy
import json
from pathlib import Path
from scar_unknown17.controller import SimpleController
from scar_unknown17.facts import PublicFacts


def obs(feedback='',location='room',hands='no objects',equipment='no objects',ground='no objects',neighbors='hall',step=0):
    return {'step':step,'text':f'Current Location: Test, {location}\n\n{feedback}\n\nI am holding {hands}.\nI have equipped {equipment}.\nI see {ground} near me.\nI see no one nearby.\nNeighboring areas: {neighbors}.\n'}


def test_station_only_is_unknown_recipe():
    f=PublicFacts();f.set_goal('craft 1 widget','Obtain at least 2 widget')
    f.observe(obs(),'craft 1 widget',obs('Cannot craft widget. Missing necessary bench in the current area.'))
    text,audit=f.render(obs());r=next(x for x in audit['records'] if x['kind']=='recipe')
    assert r['value']['ingredients']=='UNKNOWN' and r['value']['stations']==['bench']


def test_summary_preserves_names_without_inventing_quantities():
    f=PublicFacts();f.observe(obs(),'inspect wire',obs('I inspected wire. It can be used to craft: widget (made of wire, plate).'))
    for i in range(10):f.observe(obs(step=i),'wait',obs(step=i+1))
    text,a=f.render(obs());r=next(r for r in a['records'] if r['kind']=='recipe')
    assert r['value']['ingredients']==['wire','plate'] and r['value']['quantities'].startswith('UNKNOWN')


def test_historical_location_is_not_current_possession():
    f=PublicFacts();f.observe(obs(ground='2 ore'),'enter hall',obs(location='hall'))
    _,a=f.render(obs(location='hall'));r=next(r for r in a['records'] if r['kind']=='location')
    assert 'historical' in r['scope'] and f.table.count('ore')==0


def test_summary_bounds_and_roundtrip():
    f=PublicFacts();f.set_goal('craft 1 target','Obtain at least 2 target')
    for i in range(100):
        f.observe(obs(),'inspect raw',obs(f'I inspected raw. It can be used to craft: product{i} (made of raw).',step=i))
    g=PublicFacts.from_dict(json.loads(json.dumps(f.to_dict())))
    text,a=g.render(obs());assert len(text)<=6000 and len(a['records'])<=48 and len(g.table.recipes)<=48
    assert {'goal','uncertainty','recipe','current'} <= {r['kind'] for r in a['records']}


def test_consumption_is_observed_delta_not_universal_ratio():
    f=PublicFacts()
    f.observe(obs(hands='1 bag'),'inspect bag',obs('I inspected bag: It contains: 2 cloth (capacity: 2/10).',hands='1 bag'))
    before=obs(hands='1 bag');after=obs('I successfully crafted 2 cord. It is now on the ground.',hands='1 bag',ground='2 cord')
    f.observe(before,'craft 2 cord',after)
    f.observe(after,'inspect bag',obs('I inspected bag: It contains: 1 cloth (capacity: 1/10).',hands='1 bag',ground='2 cord'))
    assert f.effects[-1]['consumed']=={'cloth':1} and f.effects[-1]['actual']==2
    assert 'not a universal ratio' in f.effects[-1]['scope']


def test_intervening_action_cancels_quantity_inference():
    f=PublicFacts();f.observe(obs(hands='2 cloth'),'craft 1 cord',obs('I successfully crafted 1 cord.',hands='1 cloth',ground='1 cord'))
    f.observe(obs(hands='1 cloth'),'drop cloth',obs(ground='1 cloth'))
    f.observe(obs(),'inspect inventory',obs())
    assert not f.effects and f.pending is None


def test_directed_exploration_finite_and_public():
    c=SimpleController(True);c.set_goal('craft 1 widget','Obtain at least 2 widget')
    o=obs(hands='1 widget',ground='2 raw');first=c.choose(o,'wait')
    assert first in ['inspect widget','inspect raw']
    c.exploration_spent=c.EXPLORATION_LIMIT
    assert c._explore({'widget'}) is None
    assert set(c.probes)<= {'raw','widget'}


def test_batch_fixed_and_unknown_effect_agree_without_item_exceptions():
    for mode in ['fixed','learned']:
        c=SimpleController(batch=mode);c.set_goal('craft 1 widget','Obtain at least 2 widget')
        c.table.observe(obs(hands='1 widget'))
        assert c._batch_action('craft 1 cord')=='craft 2 cord'
        assert c._batch_action('craft 1 widget')=='craft 1 widget'
        assert c.mechanism_decision['batch']['predicted_consumption'] is None


def test_controller_serialization_keeps_budgets_and_facts():
    c=SimpleController(True,'learned');c.set_goal('craft 1 widget','Obtain at least 2 widget')
    c.choose(obs(hands='1 widget',ground='1 raw'),'wait')
    clone=SimpleController.from_dict(json.loads(json.dumps(c.to_dict())))
    assert clone.to_dict()==c.to_dict()


def test_policy_has_no_engine_data_or_case_access():
    banned=('scar.environment','scar_unknown17.audit','scar_sequence.evaluate','scar_sequence.build','scar_v3.hard')
    for name in ['controller.py','facts.py','agent.py']:
        text=(Path('scar_unknown17')/name).read_text();tree=ast.parse(text)
        imports=[n.module or '' for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
        assert not any(m.startswith(banned) for m in imports)
        assert not any(s in text for s in ['sequence-','bandage_roll','brass_blank','recipe_graph','initial_snapshot'])
