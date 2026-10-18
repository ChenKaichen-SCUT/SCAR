import copy
from types import SimpleNamespace
from scar_public.hypothesis_repair import validate
from scar_public.objective_repair import (
    ObjectiveRepairAgent,TrialEvidence,requirement_catalog,compile_verification,check_objective,
)
from scar_public.test_hypothesis_repair import case
from scar_public.test_continuation import obs


def setup_source(target='metal',site='yard'):
    m,e,t,g,_=case();e.records=[]
    m.model.recipes['blade']['needs']={'rod':1,target:1}
    # The entity is present in public recipe evidence; its proposed source is unknown.
    m.observations.append('A blade requires 1 '+target+'.')
    original=dict(action='enter vault',frame=dict(goal_quote=g[0]))
    need=next(n for n in requirement_catalog(m,original,g,e) if n['target']==target)
    candidate=dict(goal_quote=g[0],blocker='Missing material',hypothesis='This location may contain the material',
        task_link='Acquire the missing recipe input',basis=['A blade requires 1 '+target+'.'],
        steps=[dict(action='enter '+site,test=dict(kind='at',target=site))],branches=None,
        need_id=need['id'],verification=dict(mode='source',site=site))
    agent=ObjectiveRepairAgent(SimpleNamespace(step=1),'JSON');agent.notebook=m;agent.continuation=e
    programs,rejected=agent.proposals(dict(hypotheses=[candidate]),t,g,[need],299,1)
    assert programs and not rejected
    return agent,t,g,need,candidate,programs[0]


def arrive(agent,place='yard',ground='no objects',held='1 rod'):
    text=obs(place=place,ground=ground,held=held,neighbors='vault, hall')
    agent.notebook.model.observe(text);agent.continuation.current=agent.notebook.model.current
    agent.continuation.observation=text
    return text


def test_arrival_is_not_resource_success_and_objects_are_not_hardcoded():
    for target,site in [('metal','yard'),('material_z','area_q')]:
        if site!='yard':
            # Make the renamed site part of the observed interface.
            a,t,g,n,c,p=setup_source(target)
            a.notebook.model.current['neighbors'].append(site)
            a.notebook.observations.append('Neighboring areas: '+site+'.')
            c['steps'][0]['action']='enter '+site;c['steps'][0]['test']['target']=site;c['verification']['site']=site
            p=a.proposals(dict(hypotheses=[c]),t,g,[n],299,1)[0][0]
        else:a,t,g,n,c,p=setup_source(target,site)
        a.hypothesis_pending=dict(program=p,index=0)
        result,follow=a.assess_pending(dict(text=arrive(a,site)),2,t)
        assert result['execution_outcome'] is True and result['outcome'] is False
        assert result['requirement_resolved'] is False and a.revision_due and follow is None


def test_compiler_uses_fixed_resource_not_model_selected_arrival_test():
    a,t,g,n,c,p=setup_source()
    assert p['objective']['test']==dict(kind='visible',target='metal',count=1,location='yard')
    c['verification']['mode']='access'
    assert a.proposals(dict(hypotheses=[c]),t,g,[n],299,1)[1][0]['reasons']==['VERIFICATION_DOES_NOT_MATCH_REQUIREMENT']


def test_source_presence_selects_guarded_pickup_and_only_acquisition_resolves_requirement():
    a,t,g,n,c,p=setup_source();a.hypothesis_pending=dict(program=p,index=0)
    text=arrive(a,ground='1 metal')
    a.repair_trigger=lambda *args:None
    out=a.finalize_decision(dict(action='enter hall',frame={}),dict(text=text),2,'',lambda _:None)
    assert out['action']=='pick up metal'
    result=out['continuation']['previous_repair']
    assert result['outcome'] is True and result['requirement_resolved'] is False
    assert result['decision_distinguishing'] and result['admitted']
    text=arrive(a,held='1 rod, 1 metal')
    result,_=a.assess_pending(dict(text=text),3,t)
    assert result['requirement_resolved'] is True and a.revision_due is None


def test_source_quantities_account_for_already_held_units_and_known_capacity():
    a,t,g,n,c,p=setup_source();p['objective']['need']['count']=2
    result=check_objective(p['objective'],arrive(a,ground='1 metal',held='1 metal'),a.notebook)
    assert result['outcome'] is True and result['required_ground_quantity']==1
    a.notebook.model.capacity_upper=1
    result=check_objective(p['objective'],a.continuation.observation,a.notebook)
    assert result['outcome'] is True and not result['acquisition_possible_under_known_checks']


def test_darkness_and_failed_arrival_are_unknown_not_source_absence():
    for text in ('Current Location: Estate, yard\nIt is too dark to see anything here.',obs(place='hall',ground='no objects')):
        a,t,g,n,c,p=setup_source();a.hypothesis_pending=dict(program=p,index=0)
        result,_=a.assess_pending(dict(text=text),2,t)
        assert result['outcome'] is None and a.trial_evidence.records[0]['outcome'] is None


def test_absence_blocks_same_source_not_other_sources_and_is_revocable():
    a,t,g,n,c,p=setup_source();a.hypothesis_pending=dict(program=p,index=0)
    a.assess_pending(dict(text=arrive(a)),2,t)
    assert a.trial_evidence.objections(p,a.notebook,3)[0]['reason']=='SOURCE_RECENTLY_TESTED_ABSENT'
    other=copy.deepcopy(p);other['objective']['test']['location']='vault'
    assert not a.trial_evidence.objections(other,a.notebook,3)
    a.continuation.epoch+=20
    a.notebook.model.locations['Estate, yard']['objects']['food']=12
    assert a.trial_evidence.objections(p,a.notebook,3)
    assert not a.trial_evidence.objections(p,a.notebook,27)
    a.notebook.model.locations['Estate, yard']['objects']['metal']=1
    assert not a.trial_evidence.objections(p,a.notebook,3)


def test_failed_trial_forces_one_immediate_revision_with_same_requirement_and_evidence():
    a,t,g,n,c,p=setup_source();a.hypothesis_pending=dict(program=p,index=0)
    text=arrive(a);a.repair_trigger=lambda *args:None;calls=[]
    def query(prompt):
        calls.append(prompt)
        return dict(action='enter vault',hypotheses=[])
    a.finalize_decision(dict(action='enter vault',frame={}),dict(text=text),2,'',query)
    assert len(calls)==1 and 'SOURCE_NOT_OBSERVED' in calls[0] and 'revision_of' in calls[0]
    assert a.revision_due is None and a.trial_evidence.records
    a.finalize_decision(dict(action='enter vault',frame={}),dict(text=text),3,'',query)
    assert len(calls)==1  # no automatic unbounded reflection loop


def test_successful_new_source_can_be_selected_after_refutation():
    a,t,g,n,c,p=setup_source();a.hypothesis_pending=dict(program=p,index=0)
    text=arrive(a);a.repair_trigger=lambda *args:None
    c=copy.deepcopy(c);c['steps'][0]=dict(action='enter vault',test=dict(kind='at',target='vault'))
    c['verification']['site']='vault';c['hypothesis']='Try a different source after observed absence'
    out=a.finalize_decision(dict(action='enter hall',frame={}),dict(text=text),2,'',lambda _:dict(action='enter vault',hypotheses=[c]))
    assert out['action']=='enter vault' and out['continuation']['packet']['revision_of']==0


def test_urgent_actions_and_task_changes_do_not_force_failed_goal():
    for mode in ('urgent','new_task'):
        a,t,g,n,c,p=setup_source();a.hypothesis_pending=dict(program=p,index=0)
        text=arrive(a)
        if mode=='new_task':a.notebook.progress_tasks['new']=dict(quote='Find another object')
        action='attack foe' if mode=='urgent' else 'enter hall'
        a.repair_trigger=lambda *args:None
        out=a.finalize_decision(dict(action=action,frame={}),dict(text=text),2,'',lambda _:(_ for _ in ()).throw(AssertionError('query')))
        assert out['action']==action


def test_access_requirement_still_accepts_new_key_hypothesis_and_compiles_target():
    m,e,t,g,c=case();a=ObjectiveRepairAgent(SimpleNamespace(step=1),'JSON');a.notebook=m;a.continuation=e
    n=next(n for n in requirement_catalog(m,dict(action='enter vault'),g,e) if n['kind']=='access')
    c.update(need_id=n['id'],verification=dict(mode='access'))
    programs,rejected=a.proposals(dict(hypotheses=[c]),t,g,[n],299,1)
    assert programs and not rejected and programs[0]['objective']['test']==dict(kind='at',target='vault')


def test_actor_can_retain_original_despite_a_valid_different_program():
    a,t,g,n,c,p=setup_source();a.repair_trigger=lambda *args:dict(kind='repeat')
    out=a.finalize_decision(dict(action='enter vault',frame={}),dict(text=a.continuation.observation),1,'',
        lambda _:dict(action='enter vault',hypotheses=[c]))
    assert out['action']=='enter vault' and a.hypothesis_pending is None


def test_query_budget_is_shared_by_revisions_and_normal_proposals():
    a,t,g,n,c,p=setup_source();a.hypothesis_pending=dict(program=p,index=0)
    a.hypothesis_queries=[{}]*12;a.repair_trigger=lambda *args:None
    out=a.finalize_decision(dict(action='enter hall',frame={}),dict(text=arrive(a)),2,'',
        lambda _:(_ for _ in ()).throw(AssertionError('budget exceeded')))
    assert out['continuation']['reason']=='REPAIR_QUERY_BUDGET' and a.trial_evidence.records


def test_unstructured_alternative_gets_bounded_schema_correction():
    for first in (dict(action='enter yard'),dict(action='enter yard',hypotheses=[])):
        a,t,g,n,c,p=setup_source();a.repair_trigger=lambda *args:dict(kind='repeat');calls=[]
        def query(prompt):
            calls.append(prompt)
            return first if len(calls)==1 else dict(action='enter yard',hypotheses=[c])
        out=a.finalize_decision(dict(action='enter vault',frame={}),dict(text=a.continuation.observation),1,'',query)
        assert len(calls)==2 and out['action']=='enter yard'
        assert out['continuation']['initial_rejections']


def test_access_and_acquisition_cannot_end_at_unrelated_condition():
    m,e,t,g,c=case();a=ObjectiveRepairAgent(SimpleNamespace(step=1),'JSON');a.notebook=m;a.continuation=e
    n=next(n for n in requirement_catalog(m,dict(action='enter vault'),g,e) if n['kind']=='access')
    c.update(need_id=n['id'],verification=dict(mode='access'))
    c['steps']=[dict(action='enter yard',test=dict(kind='at',target='yard'))]
    assert a.proposals(dict(hypotheses=[c]),t,g,[n],299,1)[1][0]['reasons']==['ACCESS_NOT_REACHED_BY_PLAN']
    a,t,g,n,c,p=setup_source();c['verification']=dict(mode='acquire')
    assert a.proposals(dict(hypotheses=[c]),t,g,[n],299,1)[1][0]['reasons']==['ACQUISITION_NOT_REACHED_BY_PLAN']


def test_source_full_name_can_match_a_public_exit_without_claiming_arrival():
    a,t,g,n,c,p=setup_source();c['verification']['site']='Estate, yard'
    programs,rejected=a.proposals(dict(hypotheses=[c]),t,g,[n],299,1)
    assert programs and not rejected
    assert check_objective(programs[0]['objective'],obs(place='hall'),a.notebook)['outcome'] is None


def test_normal_proposals_reserve_two_calls_for_actual_failed_trials():
    a,t,g,n,c,p=setup_source();a.hypothesis_queries=[{}]*10
    a.repair_trigger=lambda *args:dict(kind='repeat')
    out=a.finalize_decision(dict(action='enter vault',frame={}),dict(text=a.continuation.observation),1,'',
        lambda _:(_ for _ in ()).throw(AssertionError('reserved calls consumed')))
    assert out['continuation']['reason']=='RESERVED_FOR_TRIAL_REVISION'
    a.hypothesis_pending=dict(program=p,index=0);calls=[]
    def revise(prompt):
        calls.append(prompt)
        return dict(action='enter hall') if len(calls)==1 else dict(action='enter hall',hypotheses=[])
    out=a.finalize_decision(dict(action='enter hall',frame={}),dict(text=arrive(a)),2,'',revise)
    assert len(calls)==2 and len(a.hypothesis_queries)==12
    assert out['continuation']['packet']['revision_of']==0
