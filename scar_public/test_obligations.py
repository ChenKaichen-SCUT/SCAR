import json

from scar_public.obligations import ExecutionModel, explicit_role_bindings
from scar_public.obligation_agent import ObligationAgent, ObligationMemory


def obs(place='Home, workshop',holding='no objects',ground='1 wood',extra=''):
    return (f'Current Location: {place}\nI am holding {holding}.\nI have equipped no objects.\n'
            f'I see {ground} near me.\nNeighboring areas: forge, workshop.\n'+extra)


def test_goal_does_not_promote_ingredients_categories_or_unseen_instruction():
    m=ExecutionModel()
    task='Craft a metal sword and hold it in your hands.'
    m.observe(obs(ground='1 metal_bar, 1 metal_sword',extra='Task: '+task))
    c=m.goal_contract(task)
    assert {(p['kind'],p['item']) for p in c['supported_literals']}=={('crafted','metal_sword'),('held','metal_sword')}
    assert not c['confirmed']
    assert m.goal_contract('Hold a metal bar.')['supported_literals']==[]
    category='Obtain and equip a weapon before engaging enemies.'
    m.observe(obs(extra='[1] '+category))
    assert m.goal_contract(category)['supported_literals']==[]


def test_dependency_search_collects_remote_inputs_and_crafts_intermediates():
    m=ExecutionModel()
    m.observe(obs(ground='1 wood, 1 bench'))
    m.observe(obs('Home, forge',ground='2 ore, 1 furnace',extra='I entered forge.'),'enter forge')
    m.observe(obs(ground='1 wood, 1 bench',extra='I entered workshop.'),'enter workshop')
    m.capacity_lower=m.capacity_upper=2
    m.recipes={'bar':{'needs':{'ore':2}},'handle':{'needs':{'wood':1}},'sword':{'needs':{'bar':1,'handle':1}}}
    m.stations={'bar':{'name':'furnace'},'handle':{'name':'bench'},'sword':{'name':'furnace'}}
    result=m.acquisition('sword',max_nodes=18000,seconds=5)
    assert result['status']=='candidate',result
    assert sum(a.startswith('craft ') for a in result['plan'])==3
    # Independent tiny executor: moves cannot teleport; production consumes real inputs.
    loc='workshop'; hands={}; floor={'workshop':{'wood':1},'forge':{'ore':2}}
    stations={'bar':'forge','handle':'workshop','sword':'forge'}
    recipes={'bar':{'ore':2},'handle':{'wood':1},'sword':{'bar':1,'handle':1}}
    for action in result['plan']:
        if action.startswith('enter '):
            dest=action[6:];assert dest!=loc and dest in floor;loc=dest
        elif action.startswith('pick up '):
            item=action[8:];assert floor[loc].get(item,0)>=1
            floor[loc][item]-=1;hands[item]=hands.get(item,0)+1
        elif action.startswith('drop '):
            item=action[5:];assert hands.get(item,0)>=1
            hands[item]-=1;floor[loc][item]=floor[loc].get(item,0)+1
        elif action.startswith('craft 1 '):
            item=action[8:];assert loc==stations[item]
            for ingredient,count in recipes[item].items():
                assert hands.get(ingredient,0)>=count;hands[ingredient]-=count
            floor[loc][item]=floor[loc].get(item,0)+1
        else:raise AssertionError(action)
        assert sum(hands.values())<=2
    assert hands.get('sword')==1


def test_current_adjacency_invalidates_historical_return_route():
    m=ExecutionModel()
    m.observe(obs());m.observe(obs('Home, forge',extra='I entered forge.'),'enter forge')
    m.observe(obs(extra='I entered workshop.'),'enter workshop')
    m.observe(obs().replace('forge, workshop','cellar'))
    assert m.routes()['Home, workshop']=={}


def test_failed_historical_route_is_temporarily_excluded_until_conditions_change():
    m=ExecutionModel();m.observe(obs())
    m.observe(obs('Home, forge',extra='I entered forge.'),'enter forge')
    m.observe(obs(extra='I entered workshop.'),'enter workshop')
    m.observe(obs(extra='Cannot enter forge, the door is locked.'),'enter forge')
    assert 'forge' not in m.routes()['Home, workshop']
    m.observe(obs(holding='1 key',extra='I picked up key.'),'pick up key')
    assert m.routes()['Home, workshop']['forge']=='Home, forge'


def test_role_binding_does_not_substitute_another_observed_phrase():
    goal='Record the access code on a note.'
    lines=['The access code is GATE-7.', 'The restoration clause is RESTORE-ALL.']
    assert [b['value'] for b in explicit_role_bindings(goal,lines)]==['GATE-7']
    assert explicit_role_bindings('Record the recovery code on a note.',lines)==[]


def test_write_probe_predicts_different_full_results_and_records_actual_append():
    m=ExecutionModel()
    m.observe(obs(holding='1 note, 1 pen',extra='I inspected note: paper.\nIt writes: OLD'))
    m.observe(obs(holding='1 note, 1 pen',extra='I wrote on note: NEW'),'write NEW note')
    assert m.write_probe['hypotheses']=={'append':'OLDNEW','replace':'NEW'}
    m.observe(obs(holding='1 note, 1 pen',extra='I inspected note: paper.\nIt writes: OLDNEW'),'inspect note')
    assert m.semantic_trials[-1]['consistent']==['append']
    assert 'note' in m.append_documents
    empty=ExecutionModel()
    empty.observe(obs(extra='I inspected note: paper.\nIt writes: '))
    empty.observe(obs(extra='I wrote on note: NEW'),'write NEW note')
    assert empty.write_probe is None  # Same prediction is not an informative experiment.


def test_probe_workflow_executes_inspect_write_inspect_without_optional_model_schema():
    class Fake:
        step=0
        def generate(self,p,s):
            response={'reasoning':'write requested text','action':'write NEW note','frame':{
                'goal_quote':'Record the new code on the note.','method':'write','assessment':'untested','expected':'recorded'}}
            return {'response':json.dumps(response),'num_input_tokens':1,'num_output_tokens':1}
    fake=Fake();a=ObligationAgent(fake,'Action space: write inspect')
    initial=obs(holding='1 note, 1 pen',extra='[1] Record the new code on the note.')
    assert a.act({'text':initial})[0]=='inspect note'
    fake.step+=1
    assert a.act({'text':obs(holding='1 note, 1 pen',extra='I inspected note: paper.\nIt writes: OLD')})[0]=='write NEW note'
    fake.step+=1
    assert a.act({'text':obs(holding='1 note, 1 pen',extra='I wrote on note: NEW')})[0]=='inspect note'
    saved=json.loads(json.dumps(a.notebook.state()));restored=ObligationMemory();restored.load(saved)
    assert restored.state()==a.notebook.state()
    assert restored.model.write_probe==a.notebook.model.write_probe


def test_controller_selects_semantic_probe_even_when_actor_would_wait():
    class NeverCalled:
        step=4
        def generate(self,p,s):raise AssertionError('Known unresolved obligation should activate without actor request')
    a=ObligationAgent(NeverCalled(),'Action space: write inspect')
    m=a.notebook
    m.last_action=None
    m.prompt(obs(holding='1 scratch, 1 pen',extra='I inspected scratch: paper.\nIt writes: '))
    m.last_action='write TEST scratch'
    m.prompt(obs(holding='1 scratch, 1 pen',extra='I wrote on scratch: TEST'))
    m.last_action='inspect note'
    current=obs(holding='1 note, 1 pen',extra='[1] Record the access code on a note.\nThe access code is GATE-7.\nI inspected note: paper.\nIt writes: OLD')
    action,_,_,response=a.act({'text':current})
    assert action=='inspect note'
    assert a.notebook.pending_write['payload']=='GATE-7'
    assert a.notebook.active_write_attempts


def test_contradicted_public_recipe_model_does_not_drive_automatic_repetition():
    m=ExecutionModel()
    extra='It can be used to craft: sheet (0.5 pulp)\nCannot craft a single sheet. Do not have sufficient amount of necessary ingredients.'
    m.observe(obs(holding='1 pulp',ground='2 pulp',extra='It can be used to craft: sheet (0.5 pulp)'))
    m.capacity_lower=m.capacity_upper=2
    m.observe(obs(holding='1 pulp',ground='2 pulp',extra=extra),'craft 1 sheet')
    assert len(m.recipe_counterexamples)==1
    # A changed quantity is a different conditional test; a second counterexample
    # prevents blind recipe-model search but does not forbid all actor actions.
    m.observe(obs(holding='2 pulp',ground='1 pulp'),'pick up pulp')
    m.observe(obs(holding='2 pulp',ground='1 pulp',extra=extra),'craft 1 sheet')
    result=m.acquisition('sheet')
    assert result['status']=='unknown'
    assert result['automatic_recipe_models_suspended_pending_new_evidence']==['sheet']
    assert m.check_action('craft 1 sheet')['status']=='unknown'
