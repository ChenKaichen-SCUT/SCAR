"""Meaningful regressions for public input isolation, protection and bounded coverage."""
import copy
import json
from pathlib import Path
import pytest
from scar_stage12.public import controller, primitive_candidate
from scar_stage13.policy import decide, entries, intent, suffix_count
from scar_stage13.prepare import public_history


def test_intent_aliases():
    assert intent({'kind':'visit','target':'x','location':'r'})==intent({'kind':'inspect','target':'x'})
    assert intent(primitive_candidate('craft 1 x'))==intent(primitive_candidate('craft 2 x'))
    assert intent(primitive_candidate('store 1 x inventory'))!=intent(primitive_candidate('inspect x'))


def test_real_prefix_progress_and_exclusive_stop():
    import gzip
    ep=json.loads(next(gzip.open('results/stage10/trajectories_S1.jsonl.gz','rt')))
    hs=public_history(ep,4)
    assert len(hs)==4 and max(h['index'] for h in hs)==3
    for h in hs:
        assert h['progress']==bool(h['new_recipes'] or h['public_acquisition'] or h['public_production'] or h['new_place'])
        assert 'physical_after' not in h
    altered=copy.deepcopy(ep)
    for r in altered['rows']:
        for k in ['physical_before','physical_after','proposed_truth','proposed_effect','diagnostic_goal_reached']:
            r[k]={'poison':True}
    assert public_history(altered,4)==hs


def fixture():
    s=json.loads(Path('results/stage12/diagnostic/states.json').read_text())[0]
    return {'controller':s['public_controller'],'observation':s['observation'],'candidates':s['candidates'],
            'history':[],'base_proposal':s['frozen_base_proposal'],'s1_action':s['rule_actions']['J0'],
            'remaining_actions':s['remaining_actions'],'j3_selected':s['candidates'][0]['id']}


def test_no_trigger_from_single_preparatory_action():
    p=fixture();p['history']=[{'index':0,'action':'enter cellar','feedback':'I entered cellar.',
        'new_recipes':[],'new_public_necessary_recipes':[],'blocked':False,'progress':False,'unconnected_inspection':False}]
    d=decide(p);assert not d['features']['C1_trigger'] and not d['features']['C2_trigger']
    assert len(set(d['choices'].values()))==1


def test_stall_trigger_is_bounded_and_cooldown_works():
    p=fixture();p['history']=[{'index':i,'action':'wait','feedback':'waiting',
        'new_recipes':[],'new_public_necessary_recipes':[],'blocked':False,'progress':False,'unconnected_inspection':False} for i in range(3)]
    d=decide(p);assert d['features']['C2_trigger']
    if d['choices']['C2']!=d['choices']['C0']:
        chosen=next(r for r in d['entry_ledger'] if r['candidate_id']==d['choices']['C2'])
        assert chosen['estimated_actions']<=4 and not chosen['inspected']
    p['history'][-1]['unconnected_inspection']=True
    assert not decide(p)['features']['C2_trigger']
    p['history'][-1]['unconnected_inspection']=False;p['remaining_actions']=2
    assert decide(p)['choices']['C2']==d['choices']['C0']


def test_new_recipe_or_material_resets_stall():
    hs=[{'progress':False},{'progress':True},{'progress':False}]
    assert suffix_count(hs,'progress')==1


def test_policy_immutable_and_label_independent():
    p=fixture();old=copy.deepcopy(p);d=decide(p)
    assert p==old
    for poison in [{'oracle':True,'case_id':'secret'},{'oracle':False,'case_id':'other'}]:
        q=copy.deepcopy(p);q.update(poison)
        got=decide(q)
        assert got['choices']==d['choices'] and got['features']==d['features']


def test_direct_goal_pickup_protected_under_stall():
    states=json.loads(Path('results/stage12/diagnostic/states.json').read_text())
    s=next(s for s in states if s['state_id']=='d12_ab8371feb0410772')
    p=fixture();p.update(controller=s['public_controller'],observation=s['observation'],candidates=s['candidates'],s1_action=s['rule_actions']['J0'],j3_selected=s['candidates'][0]['id'])
    p['history']=[{'index':i,'action':'wait','feedback':'wait','new_recipes':[],
        'new_public_necessary_recipes':[],'blocked':False,'progress':False,'unconnected_inspection':False} for i in range(3)]
    d=decide(p);assert d['features']['s1_public_execution_protected']
    assert d['choices']['C3']==d['choices']['C0']
