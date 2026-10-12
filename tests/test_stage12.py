import ast
import copy
import json
from pathlib import Path

import pytest
from tests.test_stage10 import obs
from tests.test_stage11 import controller as fixture
from scar_stage12.public import candidate_set,controller,confirmed,descriptor,next_action,primitive_candidate,public_view
from scar_stage12.prompts import messages,validate


def state():
    c=fixture('E0');c.table.recipes['bridge']={'ingredients':['raw'],'stations':['bench']}
    return c.to_dict(),obs(hands='1 final',ground='1 bench, 1 unrelated')


def test_unconnected_visible_candidate_is_retained():
    s,o=state();kept,dropped=candidate_set(s,o)
    assert any(c['target']=='unrelated' and not c['confirmed_connection'] for c in kept)
    assert any(c['kind']=='craft' and c['target']=='bridge' for c in kept)


def test_candidate_generation_is_pure_and_roundtrip_deterministic():
    s,o=state();before=copy.deepcopy(s);a=candidate_set(s,o,['wait','inspect final'])
    assert s==before and a==candidate_set(json.loads(json.dumps(s)),o,['wait','inspect final'])


def test_cropping_keeps_types_and_audits_every_removed_candidate():
    s,o=state();o=obs(hands='1 final',ground=', '.join('1 raw'+str(i) for i in range(40))+', 1 bench')
    kept,dropped=candidate_set(s,o,['wait','inspect final'])
    assert len(kept)==16 and len(dropped)>0
    assert {primitive_candidate(a)['id'] for a in ['wait','inspect final']}<={c['id'] for c in kept}
    assert any(c['category']=='known_craft' for c in kept)
    assert any(c['category']=='unconnected_visible' for c in kept)
    assert not ({c['id'] for c in kept}&{c['id'] for c in dropped})


def test_goal_is_not_inferred_from_semantics():
    s,o=state();c=controller(s,o)
    assert confirmed(c)=={'final'}
    assert 'bridge' not in confirmed(c)
    assert public_view(c)['unresolved_public_nodes']==['final']


def test_hypothesis_cannot_mutate_public_table():
    s,o=state();c=controller(s,o);before=copy.deepcopy(c.table.to_dict())
    candidate=descriptor('craft','bridge','known_craft',hypothesized_connection='bridge -> invented_hidden')
    next_action(c,candidate)
    assert c.table.to_dict()==before and 'invented_hidden' not in c.table.recipes


def test_executor_inherits_original_batch_and_acquisition():
    s,o=state();c=controller(s,o);d=descriptor('craft','bridge','known_craft')
    assert next_action(c,d)==c._batch_action('craft 1 bridge')


def test_exact_rule_first_action_not_changed():
    s,o=state();c=controller(s,o)
    assert next_action(c,primitive_candidate('craft 1 bridge'))=='craft 1 bridge'
    assert next_action(c,primitive_candidate('enter elsewhere'))=='enter elsewhere'


def test_primitive_transport_not_assigned_invented_recipe_intent():
    s,o=state();c=controller(s,o)
    assert next_action(c,primitive_candidate('enter elsewhere'),[{'action':'enter elsewhere','feedback':'entered'}]) is None


def test_actual_new_product_is_inspected_on_ground():
    s,o=state();c=controller(s,o);after=obs('I successfully crafted 2 bridge.',hands='1 final',ground='1 bench, 2 bridge',step=1)
    c.observe(o,'craft 2 bridge',after)
    assert next_action(c,descriptor('craft','bridge','known_craft'),[{'action':'craft 2 bridge','feedback':'I successfully crafted 2 bridge.'}])=='inspect bridge'


def test_disappeared_product_not_assumed_to_be_in_bag():
    s,o=state();c=controller(s,o)
    assert next_action(c,descriptor('craft','bridge','known_craft'),[{'action':'craft 2 bridge','feedback':'I successfully crafted 2 bridge.'}]) is None


def test_failed_production_does_not_trigger_product_inspection():
    s,o=state();c=controller(s,o);after=obs('Cannot craft a single bridge.',hands='1 final',ground='1 bench',step=1)
    c.observe(o,'craft 2 bridge',after)
    assert next_action(c,descriptor('craft','bridge','known_craft'),[{'action':'craft 2 bridge','feedback':'Cannot craft a single bridge.'}])!='inspect bridge'


def test_already_produced_item_not_repeated_as_trial():
    s,o=state();s['quantity_facts']['produced']['bridge']=2
    kept,drop=candidate_set(s,o)
    assert not any(c['kind']=='craft' and c['target']=='bridge' for c in kept+drop)


def test_visit_identity_includes_location():
    a=descriptor('visit','raw','known_location',location='a');b=descriptor('visit','raw','known_location',location='b')
    assert a['id']!=b['id']


def test_json_schema_validates_ids_not_plausible_prose():
    candidates=[{'id':n} for n in ['a','b','c']]
    good={'selected_candidate_id':'a','ranked_candidate_ids':['a','b','c'],'reason':'unknown',
          'hypothesized_connection':'uncertain','confidence':.5,'expected_information':'rules','alternative_if_failed':'b'}
    assert not validate(good,'J3',candidates)
    assert validate(dict(good,selected_candidate_id='hidden_answer'),'J3',candidates)
    assert validate(dict(good,ranked_candidate_ids=['a','a','b']),'J3',candidates)


@pytest.mark.parametrize('value',[None,[],{},1,True,float('nan')])
def test_malformed_candidate_fields_are_recorded_not_crashed(value):
    p={'selected_candidate_id':value,'ranked_candidate_ids':None,'confidence':value,'alternative_if_failed':value}
    assert validate(p,'J3',[{'id':'a'}])


def test_prompt_whitelist_excludes_evaluator_and_source_fields():
    s={'base_system':'public','facts_text':'facts','memory':['old'],'observation':{'text':'now'},
       'public_view':{'target':'goal'},'candidates':[{'id':'a'}], 'recipe_graph':'HIDDEN','physical_hash':'SECRET',
       'source_task':'DO_NOT_PASS','future_rows':['LEAK']}
    for method in ['J2','J3']:
        text=' '.join(messages(s,method))
        assert all(x not in text for x in ['HIDDEN','SECRET','DO_NOT_PASS','LEAK'])
    assert 'exploration_candidates' not in messages(s,'J2')[1]
    assert 'exploration_candidates' in messages(s,'J3')[1]


def test_policy_modules_have_no_hidden_imports_or_specific_answers():
    for name in ['public','prompts']:
        source=Path('scar_stage12',name+'.py').read_text();tree=ast.parse(source)
        imports=[n.module or '' for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
        assert not any(any(x in m for x in ['environment','evaluate','diagnostic','audit','pathlib']) for m in imports)
        assert not any(x in source for x in ['wooden_rod','wood_strip','hellfire_bomb','fiend_helm','hunter_gauntlets','recipe_graph','family_id'])
