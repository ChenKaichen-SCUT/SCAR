import copy
from types import SimpleNamespace
from scar_public.test_hypothesis_repair import case
from scar_public.test_continuation import obs
from scar_public.plan_repair import PlanRepairAgent,LocalPlanCompiler,catalog,child_need,need_key,route


def setup(target='metal'):
    m,e,t,g,_=case();e.records=[]
    a=PlanRepairAgent(SimpleNamespace(step=1),'JSON');a.notebook=m;a.continuation=e
    n=child_need(target,1,'Public recipe requires this material')
    return a,t,g,n


def source_method(a,n,g,place='yard',**kwargs):
    c=catalog(a.notebook)
    sid=next(k for k,v in c['sites'].items() if v['name']==place)
    return dict(kind='source',need_id=n['id'],goal_quote=g[0],site_id=sid,
        hypothesis='This observed location may supply the missing material',
        evidence_ids=[c['sites'][sid]['evidence_id']],**kwargs)


def plan(a,t,g,n,method):
    return dict(root_need=n,task=t,goal_quote=g[0],goals=g,bindings={need_key(n):method},completed=[],started=1)


def update(a,text,step,action):
    a.notebook.model.observe(text,action);a.notebook.observations.append(text)
    a.continuation.observe(text,step)


def test_route_compiler_uses_directed_edges_and_never_invents_reverse_paths():
    a,t,g,n=setup();m=a.notebook.model
    m.locations['Estate, origin']=dict(objects={'metal':1},neighbors=['hall'])
    m.edges={'Estate, origin':{'hall':'Estate, hall'}}
    c=catalog(a.notebook);site=next(v for v in c['sites'].values() if v['location']=='Estate, origin')
    assert route(m,site,a.continuation,t)[0] is None
    method=source_method(a,n,g,'origin')
    p=plan(a,t,g,n,method)
    assert a.compiler(t,1).compile(p)['kind']=='NO_OBSERVED_ROUTE'


def test_unknown_offered_exit_reference_survives_successful_traversal():
    a,t,g,n=setup();method=source_method(a,n,g);p=plan(a,t,g,n,method)
    assert a.compiler(t,1).compile(p)['action']=='enter yard'
    update(a,obs(place='yard',ground='1 metal',held='1 rod',neighbors='hall',feedback='I entered yard.'),2,'enter yard')
    assert a.compiler(t,2).compile(p)['action']=='pick up metal'


def test_long_known_route_is_compiled_one_step_at_a_time_without_three_action_limit():
    a,t,g,n=setup();m=a.notebook.model;m.current['neighbors']=['r0'];m.locations['Estate, hall']['neighbors']=['r0']
    prev='Estate, hall'
    for i in range(5):
        dest='Estate, r'+str(i);m.edges.setdefault(prev,{})['r'+str(i)]=dest
        m.locations[dest]=dict(objects={'metal':1} if i==4 else {},neighbors=['r'+str(i+1)] if i<4 else [])
        prev=dest
    p=plan(a,t,g,n,source_method(a,n,g,'r4'));c=a.compiler(t,1).compile(p)
    assert c['action']=='enter r0' and len(c['route'])==5


def test_false_source_preserves_root_and_revises_only_missing_child():
    a,t,g,n=setup();root=child_need('blade',1,'Craft blade')
    parent_method=dict(kind='recipe');p=plan(a,t,g,root,parent_method)
    # Rod already held; missing metal is the only unresolved recipe input.
    c=a.compiler(t,1).compile(p);assert c['need']['target']=='metal' and c['kind']=='CHOOSE_METHOD'
    child=c['need'];method=source_method(a,child,g)
    choices,errors=a.parse_methods(dict(keep_original=False,methods=[method]),[child],g,a.compiler(t,1),t,1,p)
    assert choices and not errors
    chosen=choices[0]['plan'];assert chosen['bindings'][need_key(root)]==parent_method
    assert chosen['root_need']==root and chosen['bindings'][need_key(child)]['kind']=='source'


def test_compiler_backchains_observed_recipe_and_picks_material_without_extra_query():
    a,t,g,n=setup('blade');m=a.notebook.model
    m.current['ground']['metal']=1;m.locations[m.current['location']]['objects']['metal']=1
    p=plan(a,t,g,n,dict(kind='recipe'));c=a.compiler(t,1).compile(p)
    assert c['action']=='pick up metal' and [x['target'] for x in c['chain']]==['blade','metal']
    update(a,obs(held='1 rod, 1 metal',ground='no objects'),2,'pick up metal')
    assert a.compiler(t,2).compile(p)['action']=='craft 1 blade'
    update(a,obs(held='no objects',ground='1 blade',feedback='I successfully crafted 1 blade.'),3,'craft 1 blade')
    assert a.compiler(t,3).compile(p)['action']=='pick up blade'
    update(a,obs(held='1 blade',ground='no objects'),4,'pick up blade')
    assert a.compiler(t,4).compile(p)['status']=='done'


def test_capacity_repair_keeps_source_and_only_stores_unrelated_item():
    a,t,g,n=setup();m=a.notebook.model
    text=obs(held='1 rod, 1 pebble',ground='1 metal, 1 bag');update(a,text,2,None)
    m.current['equipped']={'bag':1};m.containers['bag']=dict(items={},used=0,capacity=2)
    method=source_method(a,n,g,'hall');p=plan(a,t,g,n,method);c=a.compiler(t,2).compile(p)
    assert c['action']=='store 1 pebble bag' and p['bindings'][need_key(n)]==method
    m.containers['bag']['used']=2
    assert a.compiler(t,2).compile(p)['kind']=='CAPACITY'


def test_darkness_is_observation_frontier_not_material_absence():
    a,t,g,n=setup();p=plan(a,t,g,n,source_method(a,n,g))
    update(a,'Current Location: Estate, yard\nI entered yard.\nIt is too dark to see anything here.',2,'enter yard')
    assert a.compiler(t,2).compile(p)['kind']=='VISIBILITY_UNKNOWN'


def test_empty_source_is_scoped_and_new_material_revokes_it():
    a,t,g,n=setup();p=plan(a,t,g,n,source_method(a,n,g))
    update(a,obs(place='yard',ground='no objects',held='1 rod',feedback='I entered yard.',neighbors='hall'),2,'enter yard')
    c=a.compiler(t,2).compile(p);assert c['kind']=='SOURCE_ABSENT';a.remember(c,t,2)
    update(a,obs(held='1 rod'),3,'enter hall')
    assert a.compiler(t,3).compile(p)['kind']=='SOURCE_ABSENT'
    a.notebook.model.locations['Estate, yard']['objects']['metal']=1
    assert a.compiler(t,3).compile(p)['status']=='ready'


def test_actual_source_failure_immediately_changes_executable_method():
    a,t,g,n=setup();a.plan=plan(a,t,g,n,source_method(a,n,g));a.repair_trigger=lambda *args:None
    first=a.finalize_decision(dict(action='enter vault'),dict(text=a.continuation.observation),1,'',lambda _:None)
    assert first['action']=='enter yard'
    update(a,obs(place='yard',ground='no objects',held='1 rod',neighbors='hall',feedback='I entered yard.'),2,'enter yard')
    calls=[]
    def query(prompt):
        calls.append(prompt);m=source_method(a,n,g,'hall')
        return dict(action='enter yard',keep_original=False,methods=[m])
    result=a.finalize_decision(dict(action='inspect note'),dict(text=a.continuation.observation),2,'',query)
    assert len(calls)==1 and result['action']=='enter hall' and 'SOURCE_ABSENT' in calls[0]
    assert result['continuation']['plan']['root_need']==n


def test_container_inspection_selects_retrieval_only_after_observed_contents():
    a,t,g,n=setup();m=a.notebook.model;m.current['ground']['box']=1
    p=plan(a,t,g,n,dict(kind='container',container='box'))
    assert a.compiler(t,1).compile(p)['action']=='inspect box'
    m.containers['box']=dict(items={'metal':1},used=1,capacity=2)
    assert a.compiler(t,2).compile(p)['action']=='take out 1 metal box'
    m.containers['box']['items']={}
    assert a.compiler(t,3).compile(p)['kind']=='CONTAINER_EMPTY'


def test_references_prevent_invented_sources_recipes_and_command_strings():
    a,t,g,n=setup();method=source_method(a,n,g)
    for changed,reason in [(dict(site_id='invented'),'UNKNOWN_SITE_REFERENCE'),
                           (dict(evidence_ids=['invented']),'UNKNOWN_EVIDENCE_REFERENCE'),
                           (dict(kind='recipe'),'RECIPE_NOT_OBSERVED'),(dict(site_id=[]),'UNKNOWN_SITE_REFERENCE')]:
        bad={**method,**changed}
        plans,errors=a.parse_methods(dict(keep_original=False,methods=[bad]),[n],g,a.compiler(t,1),t,1)
        assert not plans and reason in errors[0]['reasons']


def test_access_hypothesis_acquires_public_item_before_retry_without_hardcoded_entity():
    for item,place in [('token','vault'),('object_q','room_z')]:
        m,e,t,g,_=case(item,place);a=PlanRepairAgent(SimpleNamespace(step=1),'JSON');a.notebook=m;a.continuation=e
        n=child_need('metal',1,'Material');method=source_method(a,n,g,place,via_item=item)
        p=plan(a,t,g,n,method)
        assert a.compiler(t,1).compile(p)['action']=='pick up '+item


def test_recipe_cycles_are_bounded_and_missing_parent_is_not_task_success():
    a,t,g,n=setup('blade');a.notebook.model.recipes['metal']=dict(needs={'blade':1},quote='Observed cycle')
    p=plan(a,t,g,n,dict(kind='recipe'));p['bindings'][need_key(child_need('metal',1,''))]=dict(kind='recipe')
    assert a.compiler(t,1).compile(p)['kind']=='DEPENDENCY_LIMIT'


def test_urgent_actions_and_explicit_retention_preserve_original_behavior():
    a,t,g,n=setup();a.plan=plan(a,t,g,n,source_method(a,n,g))
    out=a.finalize_decision(dict(action='attack foe'),dict(text=a.continuation.observation),1,'',lambda _:None)
    assert out['action']=='attack foe' and a.plan_pending is None
    a.plan=None;a.repair_trigger=lambda *args:dict(kind='repeat')
    out=a.finalize_decision(dict(action='enter vault'),dict(text=a.continuation.observation),2,'',
        lambda _:dict(action='enter vault',keep_original=True,methods=[]))
    assert out['action']=='enter vault'


def test_query_budget_and_completed_recipe_do_not_require_new_queries():
    a,t,g,n=setup();a.plan_queries=[{}]*12;a.plan=plan(a,t,g,n,source_method(a,n,g))
    update(a,obs(place='yard',ground='1 metal',held='1 rod',feedback='I entered yard.'),2,'enter yard')
    out=a.finalize_decision(dict(action='enter hall'),dict(text=a.continuation.observation),2,'',lambda _:(_ for _ in ()).throw(AssertionError('query')))
    assert out['action']=='pick up metal'


def test_failed_access_is_not_reenabled_by_travel_but_new_resource_revokes_it():
    m,e,t,g,_=case();a=PlanRepairAgent(SimpleNamespace(step=1),'JSON');a.notebook=m;a.continuation=e
    n=child_need('metal',1,'Material');p=plan(a,t,g,n,source_method(a,n,g,'vault'))
    e.step=10;e.epoch+=5
    assert a.compiler(t,10).compile(p)['kind']=='NO_OBSERVED_ROUTE'
    m.model.current['holding']['token']=1
    assert a.compiler(t,10).compile(p)['action']=='enter vault'


def test_later_success_and_expiry_revoke_access_deferral():
    for mode in ('success','expiry'):
        m,e,t,g,_=case();a=PlanRepairAgent(SimpleNamespace(step=1),'JSON');a.notebook=m;a.continuation=e
        n=child_need('metal',1,'Material');p=plan(a,t,g,n,source_method(a,n,g,'vault'))
        if mode=='success':
            success=copy.deepcopy(e.records[-1]);success['feedback']=[];success['after']['location']='Estate, vault'
            e.records.append(success)
        e.step=10 if mode=='success' else 18
        assert a.compiler(t,e.step).compile(p)['status']=='ready'


def test_proposer_sees_scoped_route_failure_and_stable_evidence_ids():
    m,e,t,g,_=case();a=PlanRepairAgent(SimpleNamespace(step=1),'JSON');a.notebook=m;a.continuation=e
    view=a.compiler(t,1).proposal_view()
    site=next(v for v in view['sites'].values() if v['name']=='vault')
    assert site['route_check']['status']=='no_supported_route'
    assert site['route_check']['blocked'] and site['evidence_id'] in view['evidence']
