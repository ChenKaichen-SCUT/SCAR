import copy
from types import SimpleNamespace
from scar_public.continuation import ContinuationMemory,task_key
from scar_public.hypothesis_repair import HypothesisRepairAgent,validate,evaluate,check_steps
from scar_public.test_continuation import obs
from scar_public.task_progress import ProgressMemory


def case(item='token',place='vault'):
    m=ProgressMemory();e=ContinuationMemory()
    text=obs(held='1 rod',ground='1 '+item,neighbors=place+', yard',feedback='guide says: Craft a blade and hold it in your hands.')
    m.prompt(text);m.refresh_tasks();e.observe(text,0);task=task_key(m)
    e.commit('enter '+place,task)
    following=obs(held='1 rod',ground='1 '+item,neighbors=place+', yard',feedback='Cannot enter '+place+', the door is locked.')
    m.prompt(following);m.refresh_tasks();e.observe(following,1)
    m.model.capacity_upper=2;m.model.recipes={'blade':dict(needs={'rod':1,'metal':1},quote='blade (1 rod, 1 metal)')}
    goals=[r['quote'] for r in m.progress_tasks.values()]
    candidate=dict(goal_quote=goals[0],blocker='Access is blocked',hypothesis='The observed object may enable access',
        task_link='Opening access may expose the needed material',basis=['Cannot enter '+place+', the door is locked.', 'I see 1 '+item+' near me.'],
        steps=[dict(action='pick up '+item,test=dict(kind='held',target=item)),
               dict(action='enter '+place,test=dict(kind='at',target=place),may_consume={item:1})],branches=None)
    return m,e,task,goals,candidate


def test_novel_hypothesis_admitted_without_prior_success_and_changed_carried_state_revokes_blocker():
    for item,place in [('token','vault'),('access_x','room_z')]:
        m,e,t,g,c=case(item,place)
        accepted,reasons=validate(c,m,e,t,g,[],[],299)
        assert accepted and not reasons
        assert accepted['checks']['unknown'] and not accepted['information']
        stale=copy.deepcopy(c);stale['steps']=stale['steps'][1:];stale['steps'][0]['may_consume']={}
        assert validate(stale,m,e,t,g,[],[],299)[0] is None


def test_capacity_and_task_reserves_still_constrain_speculation():
    m,e,t,g,c=case();m.model.capacity_upper=1
    assert 'CAPACITY_CONTRADICTION' in validate(c,m,e,t,g,[],[],299)[1]
    m.model.capacity_upper=2;c['steps'][1]['may_consume']={'rod':1}
    assert 'TASK_RESOURCE_RESERVATION' in validate(c,m,e,t,g,[],[],299)[1]


def test_unknown_is_not_success_and_quantity_is_respected():
    test=dict(kind='visible',target='metal',count=2)
    assert evaluate(test,obs(ground='1 metal')) is False
    assert evaluate(test,'Current Location: Estate, hall') is None
    report=dict(kind='report',target='token',true_contains='opens vault',false_contains='decorative only')
    assert evaluate(report,obs(feedback='I inspected token: A shiny item.')) is None
    assert evaluate(report,obs(feedback='I inspected token: opens vault.')) is True
    assert evaluate(report,obs(feedback='I inspected token: decorative only.')) is False
    assert evaluate(report,obs(feedback='I inspected token: opens vault, decorative only.')) is None


def test_information_can_distinguish_actions_without_two_known_resource_sources():
    m,e,t,g,c=case();e.records=[]
    c['steps']=[dict(action='inspect token',test=dict(kind='report',target='token',true_contains='opens vault',false_contains='decorative only'))]
    c['branches']={'true':dict(action='pick up token',test=dict(kind='held',target='token')),
        'false':dict(action='enter yard',test=dict(kind='at',target='yard'))}
    accepted,reasons=validate(c,m,e,t,g,[],[],299)
    assert accepted and accepted['information'] and not reasons
    c['branches']['false']=copy.deepcopy(c['branches']['true'])
    assert 'IDENTICAL_BRANCH_ACTIONS' in validate(c,m,e,t,g,[],[],299)[1]


def test_fabricated_evidence_entities_and_unbounded_plans_rejected():
    m,e,t,g,c=case()
    for field,value,reason in [('basis',['An oracle proved the solution.'],'UNSUPPORTED_SOURCE_QUOTE'),
        ('goal_quote','Collect unrelated coins.','UNANCHORED_GOAL'),('steps',c['steps']*2,'INVALID_PLAN_LENGTH')]:
        bad=copy.deepcopy(c);bad[field]=value
        assert reason in validate(bad,m,e,t,g,[],[],299)[1]
    bad=copy.deepcopy(c);bad['steps'][0]['action']='pick up imaginary_access'
    assert 'UNOBSERVED_ENTITY' in validate(bad,m,e,t,g,[],[],299)[1]


def test_same_hypothesis_cooldown_cannot_be_bypassed_by_rewording():
    m,e,t,g,c=case();p,_=validate(c,m,e,t,g,[],[],299)
    c['hypothesis']='A paraphrase of the same idea'
    assert 'ALREADY_TRIED_IN_THIS_CONTEXT' in validate(c,m,e,t,g,[p],[],299)[1]
    e.epoch+=1
    assert validate(c,m,e,t,g,[p],[],299)[0]


def test_explicit_use_is_recorded_even_with_concurrent_attack():
    a=HypothesisRepairAgent(SimpleNamespace(step=1),'JSON')
    e=a.continuation;e.observe(obs(held='1 token'),0);e.commit('enter vault','goal')
    text=obs(place='vault',feedback='I used a token to unlock the path to vault. I entered vault.\nI was attacked by foe.')
    e.observe(text,1);a.observe_use(text)
    assert a.observed_uses[0]['consumed']=={'token':1}


def test_observed_pickup_enables_a_continuation_and_false_or_threat_cancels():
    for mode in ('success','failed','threat','task'):
        m,e,t,g,c=case();p,_=validate(c,m,e,t,g,[],[],299)
        a=HypothesisRepairAgent(SimpleNamespace(step=2),'JSON');a.notebook=m;a.continuation=e
        a.hypothesis_pending=dict(program=p,index=0);a.repair_trigger=lambda *args:None
        text=obs(held='1 rod, 1 token' if mode!='failed' else '1 rod',ground='no objects')
        if mode=='threat':text+='\nI was attacked by foe.'
        m.model.observe(text);e.current=m.model.current;e.observation=text
        if mode=='task':m.progress_tasks['new']=dict(quote='A new task')
        result=a.finalize_decision(dict(action='inspect rod',frame={}),dict(text=text),2,'',lambda p:None)
        assert result['action']==('enter vault' if mode=='success' else 'inspect rod')


def test_nontriggered_actor_remains_unchanged():
    a=HypothesisRepairAgent(SimpleNamespace(step=0),'JSON');text=obs()
    a.continuation.observe(text,0);a.notebook.model.observe(text)
    original=dict(action='inspect note',frame={})
    result=a.finalize_decision(original,dict(text=text),0,'',lambda p:(_ for _ in ()).throw(AssertionError('Unexpected query')))
    assert result['action']=='inspect note' and not result['continuation']['changed']


def test_one_bounded_correction_gets_actual_state_and_keeps_novel_candidate():
    m,e,t,g,c=case();a=HypothesisRepairAgent(SimpleNamespace(step=1),'JSON')
    a.notebook=m;a.continuation=e;a.repair_trigger=lambda *args:'failed'
    bad=copy.deepcopy(c);bad['basis']=['I am holding 1 rod, 1 token']
    calls=[]
    def query(prompt):
        calls.append(prompt)
        return dict(action='pick up token',hypotheses=[bad if len(calls)==1 else c])
    result=a.finalize_decision(dict(action='enter vault',frame={}),dict(text=e.observation),1,'public prompt',query)
    assert result['action']=='pick up token' and len(calls)==2
    assert 'current_observed_state' in calls[1] and 'UNSUPPORTED_SOURCE_QUOTE' in calls[1]
    assert result['continuation']['initial_rejections']


def test_correction_is_bounded_and_explicit_retain_does_not_spend_extra_query():
    for retain in (False,True):
        m,e,t,g,c=case();a=HypothesisRepairAgent(SimpleNamespace(step=1),'JSON')
        a.notebook=m;a.continuation=e;a.repair_trigger=lambda *args:'failed'
        c['basis']=['fabricated observation'];calls=[]
        def query(prompt):
            calls.append(prompt)
            return dict(action='enter vault',hypotheses=[] if retain else [c])
        result=a.finalize_decision(dict(action='enter vault',frame={}),dict(text=e.observation),1,'',query)
        assert result['action']=='enter vault' and len(calls)==(1 if retain else 2)
