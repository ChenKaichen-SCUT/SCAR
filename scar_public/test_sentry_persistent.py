import copy
import json
import pytest
from scar_public.sentry_persistent import PersistentRepair,validate_card,apply_choice,action_valid
from scar_public.sentry_evidence import LongContextActor

SYSTEM='Action space:\n- inspect <object>\n- enter <area>\n- craft <amount> <object>\n- wait'
OBS='The passage is locked. There is a brass plate beside the passage.'
FAIL=[dict(type='escape_result',resolved=False,event_id='random',justification='Still blocked.')]

def card():
    return dict(status='act',goal='Reach the chamber',blocker='Passage locked',hypothesis='A plate might explain access',
        revision='No attempt yet',evidence=[dict(cycle=0,quote='The passage is locked.')],
        next=dict(action='inspect plate',kind='test',changes='Learn the access requirement',preconditions='Visible plate',
            resource_check='No known consumed resource',expected='A condition for access',
            outcomes=[dict(observe='A key is needed',then='Search for the key'),dict(observe='A code is needed',then='Search for the code')]),resolution='')

class Provider:
    def __init__(self,outputs):self.outputs=iter(outputs);self.prompts=[]
    def request(self,messages,**kwargs):
        self.prompts.append(messages)
        return dict(choices=[dict(finish_reason='stop',message=dict(content=json.dumps(next(self.outputs))))])

def test_observation_citations_cannot_use_action_or_paraphrase():
    c=card();c['evidence'][0]['quote']='The passage needs a key.'
    with pytest.raises(ValueError,match='quote absent'):validate_card(c,[dict(cycle=0,observation=OBS)],SYSTEM,None,0)

def test_goal_cannot_silently_change_to_easier_target():
    old=card();new=card();new['goal']='Pick up anything'
    with pytest.raises(ValueError,match='original goal'):validate_card(new,[dict(cycle=0,observation=OBS)],SYSTEM,old,0)

def test_probe_must_change_later_decision():
    c=card();c['next']['outcomes'][1]['then']='Search for the key'
    with pytest.raises(ValueError,match='subsequent plan'):validate_card(c,[dict(cycle=0,observation=OBS)],SYSTEM,None,0)

def test_closure_requires_latest_observation_not_old_evidence():
    c=card();c.update(status='resolved',next=None,resolution='Passage accessible')
    with pytest.raises(ValueError,match='current observation'):validate_card(c,[dict(cycle=0,observation=OBS),dict(cycle=1,observation='Still locked.')],SYSTEM,None,1)

def test_unresolved_opens_case_but_ordinary_execution_uses_no_calls():
    p=Provider([card()]);c=PersistentRepair(p,SYSTEM);c.seed(OBS)
    assert c.observe(0,dict(action='wait'),OBS,[])=='' and c.calls==0
    output=card();output['evidence'][0]['cycle']=1;p.outputs=iter([output])
    assert 'UNRESOLVED' in c.observe(1,dict(action='wait'),OBS,FAIL)
    assert c.calls==1 and 'event_id' not in p.prompts[0][1]['content']

def test_stale_or_wrong_step_operation_cannot_override():
    c=PersistentRepair(Provider([card()]),SYSTEM);c.seed(OBS);c.observe(0,dict(action='wait'),OBS,FAIL)
    proposed=dict(action='wait',reasoning='ordinary')
    assert c.choose(2,OBS,proposed)==proposed
    assert c.choose(1,'A different situation',proposed)==proposed
    assert c.choose(1,OBS,proposed)['action']=='inspect plate'

def test_actual_execution_not_recommendation_updates_attempt():
    nxt=card();nxt['evidence']=[dict(cycle=1,quote='The passage is locked.')]
    p=Provider([card(),nxt]);c=PersistentRepair(p,SYSTEM,mode='advice');c.seed(OBS)
    c.observe(0,dict(action='wait'),OBS,FAIL);c.observe(1,dict(action='enter chamber'),OBS,[])
    packet=json.loads(p.prompts[1][1]['content'])
    assert packet['attempts'][-1]['executed']=='enter chamber'
    assert packet['attempts'][-1]['matched'] is False
    assert packet['previous_card']['goal']=='Reach the chamber'

def test_suspension_preserves_case_without_claiming_success():
    p=Provider([card()]);c=PersistentRepair(p,SYSTEM,burst=1);c.seed(OBS)
    c.observe(0,dict(action='wait'),OBS,FAIL)
    assert c.observe(1,dict(action='inspect plate'),OBS,[])==''
    assert c.card['goal']=='Reach the chamber' and c.remaining==0 and c.calls==1

def test_invalid_response_preserves_original_behavior_and_counts_calls():
    bad=card();bad['next']['action']='teleport chamber'
    c=PersistentRepair(Provider([bad,bad]),SYSTEM,max_calls=2);c.seed(OBS)
    assert c.observe(0,dict(action='wait'),OBS,FAIL)==''
    assert c.calls==2 and c.pending is None
    assert c.choose(1,OBS,dict(action='wait',reasoning='original'))['action']=='wait'

def test_conversation_records_action_actually_executed():
    c=PersistentRepair(Provider([card()]),SYSTEM);c.seed(OBS);c.observe(0,dict(action='wait'),OBS,FAIL)
    class ActorProvider:
        def generate(self,*args):return dict(response=json.dumps(dict(reasoning='Original',action='wait')))
    actor=LongContextActor(ActorProvider(),SYSTEM);proposed,_=actor.act(OBS)
    selected=apply_choice(actor,1,OBS,proposed,c)
    assert selected['action']=='inspect plate' and actor.memory.endswith('Action: inspect plate\n')
    assert not actor.memory.endswith('Action: wait\n')

def test_action_schema_is_supplied_by_host():
    assert action_valid('craft 1 item',SYSTEM) and action_valid('wait',SYSTEM)
    assert not action_valid('craft item',SYSTEM) and not action_valid('teleport chamber',SYSTEM)
