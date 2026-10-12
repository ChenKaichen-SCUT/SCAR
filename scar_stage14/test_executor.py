import copy
from types import SimpleNamespace
from unittest.mock import MagicMock,patch
import pytest
from scar_stage14.common import OLD,load,records
from scar_stage14.intents import normalize,recorded_goal
from scar_stage14.executor import Executor


def fake(intent,remaining=8):
    ctrl=MagicMock();ctrl.context.return_value={}
    ctrl.table=SimpleNamespace(state={'feedback':'','ground':{},'location':'room'},recipes={},places={},count=lambda x:0)
    ctrl.visible.return_value=set();ctrl.quotas={};ctrl.target='craft 1 final'
    ctrl.observe.side_effect=lambda before,a,after:ctrl.table.state.update(feedback=after['text'])
    with patch('scar_stage14.executor.controller',return_value=ctrl):
        e=Executor({'controller':{},'observation':{},'remaining_actions':remaining},intent)
    return e


@pytest.mark.parametrize('action',['store 2 ore inventory','pick up ore','enter room','craft 2 bar','inspect ore'])
def test_exact_first_even_if_invalid(action):
    e=fake({'first_action':action,'target':'bar','operation':'craft_inspect','clarity':'explicit'})
    assert e.next()==action


def test_failed_craft_does_not_inspect_imaginary_product():
    e=fake({'first_action':'craft 1 bar','target':'bar','operation':'craft_inspect','clarity':'explicit'})
    a=e.next();e.observe(a,{}, {'text':'Cannot craft a single bar.'})
    assert not e.made and e.next() is None and not e.completed


def test_actual_craft_then_inspect():
    e=fake({'first_action':'craft 1 bar','target':'bar','operation':'craft_inspect','clarity':'explicit'})
    e.observe(e.next(),{}, {'text':'I successfully crafted 1 bar. It is now on the ground.'})
    e.ctrl.visible.return_value={'bar'}
    assert e.next()=='inspect bar'
    e.observe('inspect bar',{}, {'text':'I inspected bar: A bar.'})
    assert e.completed and e.completion_step==2 and e.next() is None


def test_crafted_wrong_product_not_witness():
    e=fake({'first_action':'craft 1 bar','target':'bar','operation':'craft_inspect','clarity':'explicit'})
    e.observe(e.next(),{}, {'text':'I successfully crafted 1 other. It is now on the ground.'})
    assert not e.made


def test_failed_acquire_no_suffix():
    e=fake({'first_action':'pick up ore','target':'ore','operation':'atomic','clarity':'incomplete'})
    e.observe(e.next(),{}, {'text':'Cannot pick up ore.'})
    assert e.next() is None and not e.completed


def test_failed_acquire_explicit_goal_rechecks_material():
    e=fake({'first_action':'pick up ore','target':'bar','operation':'craft_inspect','clarity':'explicit'})
    e.ctrl.table.recipes={'bar':{'ingredients':['ore']}}
    e.ctrl._acquire.return_value=None
    e.observe(e.next(),{}, {'text':'Cannot pick up ore.'})
    assert e.next() is None and e.stop=='public_material_unavailable'


def test_budget_no_second_action():
    e=fake({'first_action':'craft 1 bar','target':'bar','operation':'craft_inspect','clarity':'explicit'},remaining=1)
    e.observe(e.next(),{}, {'text':'I successfully crafted 1 bar. It is now on the ground.'})
    e.ctrl.visible.return_value={'bar'}
    assert e.next() is None and e.stop=='action_budget' and not e.completed


def test_same_context_repeat_suppressed():
    e=fake({'first_action':'craft 1 bar','target':'bar','operation':'craft_inspect','clarity':'explicit'})
    e.ctrl.table.recipes={'bar':{'ingredients':['ore']}};e.ctrl.table.count=lambda x:2
    e.ctrl._batch_action.return_value='craft 1 bar';e.ctrl.assess.return_value={'status':'UNKNOWN'}
    e.observe(e.next(),{}, {'text':'Cannot craft a single bar.'})
    assert e.next() is None and e.stop=='same_context_repeat'


def test_unknown_station_does_not_launch_unrelated_exploration():
    e=fake({'first_action':'craft 1 bar','target':'bar','operation':'craft_inspect','clarity':'explicit'})
    e.ctrl.table.recipes={'bar':{'ingredients':[],'stations':['forge']}}
    e.observe(e.next(),{}, {'text':'Cannot craft bar. Missing necessary forge in the current area.'})
    assert e.next() is None and e.stop=='public_station_location_unknown'
    e.ctrl._explore.assert_not_called()


def test_historical_first_actions_all_candidates():
    states={s['state_id']:s for s in load(OLD/'states.json')};n=0
    for r in records(OLD/'native_branches.jsonl.gz'):
        s=states[r['state_id']];pub={'controller':s['public_controller'],'observation':s['observation'],'remaining_actions':s['remaining_actions']}
        for b in r['branches'].values():
            i=normalize(pub,b['candidate']);e=Executor(pub,i)
            assert e.next()==b['trace'][0]['action'];n+=1
    assert n==363


def test_no_rival_goal_borrowing():
    s=next(s for s in load(OLD/'states.json') if s['state_id']=='d12_b5a72f68b5457ab1')
    a=s['rule_actions']['J0']
    assert recorded_goal(s['rule_decisions']['J0'],a)['target']=='war_parchment'
    assert recorded_goal(s['rule_decisions']['J1'],a)['target']=='hellcoal_concentrate'


def test_normalizer_does_not_read_truth_or_future():
    s=load(OLD/'states.json')[0];pub={'controller':s['public_controller'],'observation':s['observation'],'remaining_actions':s['remaining_actions']}
    before=copy.deepcopy(pub);c=s['candidates'][0];i=normalize(pub,c)
    pub.update(recipe_graph={'poison':'target'},future_observation={'text':'secret'},native_useful=True)
    assert i==normalize(pub,c) and {k:pub[k] for k in before}==before
