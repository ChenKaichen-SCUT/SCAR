from types import SimpleNamespace
from scar_public.effect_repair import EffectRepairAgent,compact_request,site_index,resolve_site
from scar_public.plan_repair import child_need,need_key
from scar_public.continuation import task_key
from scar_public.test_hypothesis_repair import case
from scar_public.test_continuation import obs


def setup(item='token',place='vault'):
    m,e,t,g,_=case(item,place)
    a=EffectRepairAgent(SimpleNamespace(step=1),'JSON');a.notebook=m;a.continuation=e
    original=dict(action='enter '+place,frame=dict(goal_quote=g[0]))
    return a,t,g,original


def test_missing_material_keeps_public_recipe_parent_instead_of_locked_destination():
    a,t,g,o=setup();a.plan=a.root_plan(o,t,1)
    assert a.plan['root_need']['target']=='blade'
    f=a.expand_known(a.compiler(t,1))
    assert f['kind']=='CHOOSE_METHOD' and f['need']['target']=='metal'
    assert [n['target'] for n in f['chain']]==['blade','metal']
    assert a.plan['bindings'][need_key(a.plan['root_need'])]['kind']=='recipe'


def test_readable_hypothesis_is_grounded_and_changes_access_before_searching_material():
    for item,place in [('token','vault'),('object_q','room_z')]:
        a,t,g,o=setup(item,place);seen=[]
        def query(p):
            seen.append(p)
            return dict(action=o['action'],keep_original=False,methods=[dict(kind='source',site=place,via_item=item,why='This observed object might enable the blocked source')])
        result=a.finalize_decision(o,dict(text=a.continuation.observation),1,'UNRELATED HISTORICAL PROMPT',query)
        assert result['action']=='pick up '+item and len(seen)==1
        assert 'UNRELATED HISTORICAL PROMPT' not in seen[0]
        assert a.plan['root_need']['target']=='blade'
        assert a.plan_pending['need']['target']=='metal'


def test_actual_acquisition_continues_parent_craft_without_more_proposals():
    a,t,g,o=setup();a.plan=a.root_plan(o,t,1);f=a.expand_known(a.compiler(t,1))
    a.plan['bindings'][need_key(f['need'])]=dict(kind='source',site_id=resolve_site('yard',site_index(a.compiler(t,1))))
    a.notebook.model.observe(obs(place='yard',held='1 rod, 1 metal',ground='no objects'), 'enter yard')
    compiled=a.expand_known(a.compiler(t,2))
    assert compiled['action']=='craft 1 blade' and compiled['need']['target']=='blade'


def test_ambiguous_or_invented_locations_are_not_guessed():
    a,t,g,o=setup();a.notebook.model.locations['Other, vault']=dict(objects={},neighbors=[])
    entries=site_index(a.compiler(t,1))
    assert resolve_site('vault',entries) is None
    assert resolve_site('invented',entries) is None
    assert resolve_site('Other, vault',entries) is not None


def test_no_task_link_does_not_turn_stale_failed_entrance_into_mandatory_destination():
    a,t,g,o=setup();a.notebook.progress_tasks={};a.notebook.model.recipes={}
    o=dict(action='inspect note',frame=dict(goal_quote='Investigate the district carefully.'))
    a.notebook.observations.append(o['frame']['goal_quote'])
    assert a.root_plan(o,t,1) is None
    o['action']='enter vault';p=a.root_plan(o,t,1)
    assert p['root_need']['kind']=='access'


def test_failed_source_revision_uses_same_child_and_keeps_parent():
    a,t,g,o=setup();a.plan=a.root_plan(o,t,1);c=a.compiler(t,1);f=a.expand_known(c)
    response=dict(keep_original=False,methods=[dict(kind='source',site='yard',why='Another unvisited source')])
    plans,errors=a.ground_methods(response,f,c,t,1)
    assert plans and not errors
    p=plans[0]['plan'];assert p['root_need']['target']=='blade'
    assert p['bindings'][need_key(p['root_need'])]['kind']=='recipe'
    assert p['bindings'][need_key(f['need'])]['kind']=='source'


def test_source_absence_and_no_known_reverse_route_still_reject_methods():
    a,t,g,o=setup();a.plan=a.root_plan(o,t,1);c=a.compiler(t,1);f=a.expand_known(c)
    for site,reason in [('hall','SOURCE_ABSENT'),('unknown','UNKNOWN_OR_AMBIGUOUS_SITE')]:
        plans,errors=a.ground_methods(dict(keep_original=False,methods=[dict(kind='source',site=site,why='Trial')]),f,c,t,1)
        assert not plans and any(reason in e['reasons'] for e in errors)


def test_positive_visible_material_is_preserved_without_call_and_budget_is_bounded():
    a,t,g,o=setup();a.notebook.model.current['ground']['metal']=1
    a.notebook.model.locations[a.notebook.model.current['location']]['objects']['metal']=1
    a.plan_queries=[dict(context='old',step=-999)]*12
    out=a.finalize_decision(o,dict(text=a.continuation.observation),1,'',lambda _:(_ for _ in ()).throw(AssertionError('paid call')))
    assert out['action']=='pick up metal'
    a,t,g,o=setup();a.plan_queries=[dict(context='old',step=-999)]*12
    out=a.finalize_decision(o,dict(text=a.continuation.observation),1,'',lambda _:(_ for _ in ()).throw(AssertionError('paid call')))
    assert out['action']==o['action'] and out['continuation']['reason']=='REPAIR_QUERY_BUDGET'


def test_malformed_reply_gets_one_correction_and_no_extra_selector():
    a,t,g,o=setup();calls=[]
    def query(p):
        calls.append(p)
        return dict(action=o['action']) if len(calls)==1 else dict(action=o['action'],keep_original=True,methods=[])
    out=a.finalize_decision(o,dict(text=a.continuation.observation),1,'',query)
    assert len(calls)==2 and out['action']==o['action'] and len(a.plan_queries)==2


def test_access_means_cannot_relabel_resource_end_condition():
    a,t,g,o=setup();a.plan=a.root_plan(o,t,1);c=a.compiler(t,1);f=a.expand_known(c)
    choices,errors=a.ground_methods(dict(methods=[dict(kind='access',site='vault',via_item='token',why='Enable the material source')]),f,c,t,1)
    assert choices and not errors
    p=choices[0]['plan'];assert p['root_need']['target']=='blade'
    assert p['bindings'][need_key(f['need'])]['kind']=='source'
    a.notebook.model.observe(obs(place='vault',held='1 rod',ground='no objects',feedback='I entered vault.'),'enter vault')
    result=a.compiler(t,2).compile(p)
    assert result['kind']=='SOURCE_ABSENT' and result['need']['target']=='metal'


def test_method_selection_does_not_require_llm_to_predict_compiled_first_action():
    a,t,g,o=setup()
    result=a.finalize_decision(o,dict(text=a.continuation.observation),1,'',
        lambda _:dict(action=o['action'],methods=[dict(kind='site',site='vault',via_item='token',why='Enable the material source')]))
    assert result['action']=='pick up token'


def test_exact_registered_task_alias_is_not_a_second_resource_reservation():
    a,t,g,o=setup();record=next(iter(a.notebook.progress_tasks.values()))
    o['frame']['goal_quote']=record['source'];a.plan=a.root_plan(o,t,1)
    assert a.plan['goals']==[record['source']]
    a.notebook.model.observe(obs(held='1 rod, 1 metal',ground='no objects'))
    compiled=a.expand_known(a.compiler(t,1))
    assert compiled['action']=='craft 1 blade'


def test_alias_fix_preserves_reservation_for_a_different_registered_task():
    a,t,g,o=setup();record=next(iter(a.notebook.progress_tasks.values()))
    other='Craft a metal emblem and hold it.'
    a.notebook.progress_tasks['other']=dict(quote=other,source='other says: '+other,aliases=[other],block=other)
    a.notebook.model.recipes['metal_emblem']=dict(needs={'metal':1},quote='metal_emblem (1 metal)')
    o['frame']['goal_quote']=record['source'];a.plan=a.root_plan(o,t,1)
    a.notebook.model.observe(obs(held='1 rod, 1 metal',ground='no objects'))
    assert other in a.plan['goals']
    assert a.expand_known(a.compiler(t,1))['kind']=='OTHER_TASK_RESOURCE'


def test_access_only_commitment_yields_when_actor_moves_on_to_an_object_action():
    for action in ('pick up token','store 1 token bag','inspect token'):
        a,t,g,o=setup();a.notebook.model.recipes={}
        a.notebook.progress_tasks={};o['frame']['goal_quote']='Explore the district carefully.'
        a.notebook.observations.append(o['frame']['goal_quote']);t=task_key(a.notebook);a.plan=a.root_plan(o,t,1)
        assert a.plan['root_need']['kind']=='access'
        out=a.finalize_decision(dict(action=action),dict(text=a.continuation.observation),2,'',lambda _:(_ for _ in ()).throw(AssertionError('query')))
        assert out['action']==action and a.plan is None
        assert out['continuation']['reason']=='ACCESS_PLAN_YIELDS_TO_NON_NAVIGATION'


def test_material_parent_still_authorizes_a_relevant_compiled_step():
    a,t,g,o=setup();a.plan=a.root_plan(o,t,1)
    a.notebook.model.current['ground']['metal']=1
    a.notebook.model.locations[a.notebook.model.current['location']]['objects']['metal']=1
    out=a.finalize_decision(dict(action='pick up token'),dict(text=a.continuation.observation),2,'',lambda _:(_ for _ in ()).throw(AssertionError('query')))
    assert out['action']=='pick up metal' and a.plan['root_need']['target']=='blade'
