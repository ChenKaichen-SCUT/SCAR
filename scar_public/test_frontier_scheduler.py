from itertools import combinations
from math import inf
from time import perf_counter
from scar_public.compiled_task import CompiledTask
from scar_public.incremental_channels import IncrementalCoverage
from scar_public.resumable_capacity import ResumableCapacity
from scar_public.frontier_scheduler import FrontierPlanner,Frame,Query,AncestorRejected
from scar_public.test_symbolic_coverage import DOMAIN,PROBLEM,case
from scar_public.information_reference import independent_oracle,reachable_contexts
from scar_public.coverage_separation import make
from scar_public.catalog_capacity import CatalogCapacity
from scar_public.focused_scheduler import FocusedPlanner


def complete(engine,node,slice_units=100000):
    for _ in range(100000):
        if node.done:return node.lower
        engine.advance(node,units=slice_units,seconds=1)
    raise AssertionError('continuation made no progress')


def test_resumed_recurrence_matches_c1_without_repeating_prefix_work():
    task=CompiledTask(DOMAIN,PROBLEM,projection_predicates=('done','flag'),
        resources=(3,1),resource_costs={'make':(1,0),'sense':(0,1),'flag':(1,0)})
    a,b=ResumableCapacity(task),ResumableCapacity(task)
    key=a.owner.project(next(iter(task.belief))[1]);mask=(1<<len(task.models))-1
    n=a.node(key,mask,3);m=b.node(key,mask,3)
    expected=IncrementalCoverage(task).relational_capacity(key,mask,3)
    assert complete(a,n,1)==complete(b,m)==expected
    # Slice boundaries retain both recurrence and channel builders; all logical
    # work counters except timing/slice count must agree, even with one-unit slices.
    skip={'seconds','pattern_seconds','slices'}
    assert {k:v for k,v in a.work.items() if k not in skip}=={k:v for k,v in b.work.items() if k not in skip}


def test_hot_templates_still_charge_visits_and_avoid_reassembly():
    task=CompiledTask(DOMAIN,PROBLEM,projection_predicates=('done','flag'),
        resources=(4,),resource_costs={'make':(1,),'sense':(1,),'flag':(1,)})
    e=ResumableCapacity(task);s=next(iter(task.belief))[1];key=e.owner.project(s)
    mask=(1<<len(task.models))-1
    # Warm every retained valuation/action pair, including actions that a first
    # saturated query can legitimately leave unvisited.
    for packed in range(1<<len(task.projection)):
        projected=sum(1<<i for j,i in enumerate(task.projection) if packed&(1<<j))
        for index in range(len(e.actions)):list(e.template(projected,index))
    complete(e,e.node(key,mask,3));before=dict(e.work)
    complete(e,e.node(((2,),key[1]),mask,3))
    assert e.work['template_hits']>before['template_hits']
    assert e.work['edge_visits']>before['edge_visits']
    assert e.work['units']>before['units']
    assert e.work['outcome_assemblies']==before['outcome_assemblies']


def test_incomplete_interval_never_uses_partial_maximum_to_reject():
    task=make(4,3);e=ResumableCapacity(task)
    key=e.owner.project(next(iter(task.belief))[1]);n=e.node(key,15,3)
    for _ in range(10):
        e.advance(n,units=1,seconds=1)
        assert n.lower<=4<=n.upper
    assert complete(e,n)==4


def test_shared_dependency_can_resume_from_two_queries():
    task=CompiledTask(DOMAIN,PROBLEM,projection_predicates=('flag','done'))
    e=ResumableCapacity(task);key=e.owner.project(next(iter(task.belief))[1])
    roots=[e.node(key,7,3),e.node(key,3,3)]
    for _ in range(20000):
        for n in roots:e.advance(n,units=3,seconds=1)
        if all(n.done for n in roots):break
    else:raise AssertionError('shared continuation stalled')
    old=IncrementalCoverage(task)
    for n in roots:assert n.lower==old.relational_capacity(n.key,n.mask,n.depth)


def test_ancestor_rejection_only_exits_its_own_active_frame():
    task=make(4);p=FrontierPlanner(task,'priority')
    parent=Frame(task.belief,3,0,remaining_actions=10)
    child=Frame(task.belief,2,1)
    e=p.engine(0);key=e.owner.project(next(iter(task.belief))[1]);n=e.node(key,15,3)
    assert complete(e,n)==3
    parent.job=Query(parent,e,n,0,4,list(task.belief));p.jobs=[parent.job];p.stack=[parent,child]
    p.scheduler_start=perf_counter()-1
    try:p.service(child)
    except AncestorRejected as rejected:assert rejected.frame is parent
    else:raise AssertionError('expected targeted ancestor exit')
    assert p.record(task.belief).lower==4
    assert p.scheduler_stats['ancestor_prunes']==1


def test_catalog_slices_and_depth_one_shortcut():
    task=CompiledTask(DOMAIN,PROBLEM,projection_predicates=('done','flag'),
        resources=(3,1),resource_costs={'make':(1,0),'sense':(0,1),'flag':(1,0)})
    a,b=CatalogCapacity(task),CatalogCapacity(task)
    key=a.owner.project(next(iter(task.belief))[1]);mask=(1<<len(task.models))-1
    n=a.node(key,mask,3);m=b.node(key,mask,3)
    assert complete(a,n,1)==complete(b,m)==IncrementalCoverage(task).relational_capacity(key,mask,3)
    skip={'seconds','pattern_seconds','slices'}
    assert {k:v for k,v in a.work.items() if k not in skip}=={k:v for k,v in b.work.items() if k not in skip}
    assert a.work['depth_one_actions']>0
    assert a.work['resource_assemblies']>0


def test_warm_catalog_still_charges_resource_and_child_assembly():
    task=CompiledTask(DOMAIN,PROBLEM,projection_predicates=('done','flag'),
        resources=(4,),resource_costs={'make':(1,),'sense':(1,),'flag':(1,)})
    e=CatalogCapacity(task);key=e.owner.project(next(iter(task.belief))[1]);mask=(1<<len(task.models))-1
    for packed in range(1<<len(task.projection)):
        projected=sum(1<<i for j,i in enumerate(task.projection) if packed&(1<<j))
        list(e.catalog(projected))
    complete(e,e.node(key,mask,3));before=dict(e.work)
    complete(e,e.node(((2,),key[1]),mask,3))
    assert e.work['catalog_hits']>before['catalog_hits']
    assert e.work['catalog_action_scans']==before['catalog_action_scans']
    assert e.work['template_lookups']==before['template_lookups']
    assert e.work['resource_assemblies']>before['resource_assemblies']
    assert e.work['child_assemblies']>before['child_assemblies']
    assert e.work['units']>before['units']


def test_deferred_admission_does_not_burn_quota_on_closed_frames():
    task=make(4);p=FocusedPlanner(task,'focused')
    for _ in range(100):p.admit(Frame(task.belief,3,1))
    assert not p.engines and p.scheduler_stats['admitted']==0
    root=Frame(task.belief,3,0);p.stack=[root];p.admit(root)
    p.service(root)
    assert p.scheduler_stats['admitted']==1
    assert p.focus_stats['unstarted_retired']==100
    assert root.job is not None


def validate(focused=False):
    checks=replays=bound_checks=0
    for projection in ((),('flag',),('done','flag')):
        for resources,costs in [((),None),((1,0),{'make':(1,0),'sense':(0,1),'flag':(1,0)}),
                                ((3,1),{'make':(1,0),'sense':(0,1),'flag':(1,0)})]:
            task=CompiledTask(DOMAIN,PROBLEM,projection_predicates=projection,resources=resources,resource_costs=costs)
            old=IncrementalCoverage(task);engine=(CatalogCapacity if focused else ResumableCapacity)(task)
            oracle=independent_oracle(case(task))
            planners=([FocusedPlanner(task,m) for m in ('root_only','focused','focused_multistep')] if focused
                      else [FrontierPlanner(task,m) for m in ('fifo','priority','priority_multistep')])
            for belief,depth in reachable_contexts(case(task)):
                for count in range(1,len(belief)+1):
                    for selected in combinations(belief,count):
                        sub=frozenset(selected)
                        if any(not task.allowed(s) for _,s in sub):continue
                        truth=oracle(sub,depth)
                        live=[(n,s) for n,s in sub if not task.goal.holds(s)]
                        keys={old.project(s) for _,s in live}
                        if len(keys)==1:
                            key=next(iter(keys));mask=sum(old.model_bits[n] for n,_ in live)
                            node=engine.node(key,mask,depth)
                            result=complete(engine,node)
                            assert result==old.relational_capacity(key,mask,depth)
                            assert result>=len(live) or truth==inf
                            bound_checks+=1
                        for p in planners:
                            answer=p.solve(sub,depth)
                            assert answer.exact and answer.upper==truth
                            if truth<inf:
                                assert p.verify(sub,depth,answer.policy)==truth;replays+=1
                        checks+=1
    return dict(contexts=checks,capacity_equalities=bound_checks,policy_replays=replays)


def test_interval_and_search_against_independent_oracle():
    assert validate()['capacity_equalities']>100


def test_catalog_and_focused_search_against_independent_oracle():
    assert validate(focused=True)['capacity_equalities']>100
