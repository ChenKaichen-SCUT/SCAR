from math import inf
from itertools import combinations
from scar_public.online_cost_model import Survival,PredictiveCapacity,LifetimeModel,timely_forecast
from scar_public.predictive_scheduler import PredictivePlanner
from scar_public.frontier_scheduler import Frame
from scar_public.compiled_task import CompiledTask
from scar_public.test_symbolic_coverage import DOMAIN,PROBLEM,case
from scar_public.test_frontier_scheduler import complete
from scar_public.catalog_capacity import CatalogCapacity
from scar_public.indexed_planner import IndexedPlanner
from scar_public.information_reference import independent_oracle,reachable_contexts


def test_censored_tail_is_not_a_short_lifetime_or_false_label():
    s=Survival();s.add(2,True);s.add(10,False)
    assert s.residual(0,3)==(.5,.5)
    assert s.residual(0,11)==(0.,.5)
    assert s.residual(3,2)==(1.,1.)
    assert s.residual(11,2)==(0.,1.)
    assert s.residual(1,0)==(1.,1.)
    assert s.median_remaining(0)==2


def test_expansion_lifetime_not_wall_time_and_no_future_update():
    t=CompiledTask(DOMAIN,PROBLEM);m=LifetimeModel();f=Frame(t.belief,3,0)
    table=m.table(f);before=table.residual(0,8);version=table.version
    assert before==(0.,1.) and version==0
    m.observe(f,12,True)
    assert table.version==1 and before==(0.,1.)
    assert table.residual(0,8)==(1.,1.)


def test_prediction_has_no_planning_or_cache_side_effect():
    t=CompiledTask(DOMAIN,PROBLEM,projection_predicates=('flag','done'))
    e=PredictiveCapacity(t);key=e.owner.project(next(iter(t.belief))[1]);n=e.node(key,7,4)
    before=dict(e.work);forecast=e.predict(n)
    assert before==e.work and not e.catalogs and not e.templates
    assert forecast['median']>0 and forecast['fallback']
    e.advance(n,units=64,seconds=1)
    before=dict(e.work);e.predict(n);assert e.work==before


def test_lower_depth_closed_work_predicts_hidden_recursion():
    t=CompiledTask(DOMAIN,PROBLEM);e=PredictiveCapacity(t)
    key=e.owner.project(next(iter(t.belief))[1]);n=e.node(key,7,4)
    for _ in range(8):e.action_samples[(1,)].append(10);e.action_samples[(2,)].append(40)
    values,samples,fallback=e.action_distribution(n)
    assert samples==8 and fallback and values[2]==640


def test_same_capacity_and_work_under_one_unit_slices():
    t=CompiledTask(DOMAIN,PROBLEM,projection_predicates=('done','flag'),
        resources=(3,1),resource_costs={'make':(1,0),'sense':(0,1),'flag':(1,0)})
    a,b,old=PredictiveCapacity(t),PredictiveCapacity(t),CatalogCapacity(t)
    key=a.owner.project(next(iter(t.belief))[1]);mask=7
    roots=[e.node(key,mask,4) for e in (a,b,old)]
    assert complete(a,roots[0],1)==complete(b,roots[1])==complete(old,roots[2])
    skip={'seconds','pattern_seconds','slices'}
    assert {k:v for k,v in a.work.items() if k not in skip}=={k:v for k,v in old.work.items() if k not in skip}
    assert dict(a.action_samples)==dict(b.action_samples)


def test_current_slice_and_global_budget_are_in_forecast():
    s=Survival()
    for _ in range(16):s.add(10,True)
    cost=dict(units=[100]*5)
    p=timely_forecast(cost,s,0,100,1.,1e-6,1.)
    assert p['probability']==1
    p=timely_forecast(cost,s,0,0,1.,1e-6,1.)
    assert p['probability']==0
    p=timely_forecast(cost,s,0,100,1.,1.,1.)
    assert p['probability']==0


def test_spent_action_work_does_not_erase_future_action_cost():
    t=CompiledTask(DOMAIN,PROBLEM);e=PredictiveCapacity(t)
    key=e.owner.project(next(iter(t.belief))[1]);n=e.node(key,7,3)
    e.catalogs[key[1]]=tuple((i,0,()) for i in range(4))
    e.meta[n]=dict(units=1000,at_close=0)
    for _ in range(8):e.action_samples[e.profile(n)].append(10)
    assert e.predict(n)['median']==30


def test_no_prediction_work_after_no_future_admissions():
    t=CompiledTask(DOMAIN,PROBLEM);p=PredictivePlanner(t,'shadow');leaf=IndexedPlanner(t)
    p.scheduler_stats['admitted']=64
    a=p.solve(t.belief,4);b=leaf.solve(t.belief,4)
    assert a.upper==b.upper and p.expanded==leaf.expanded
    assert p.life.observed==0 and not p.engines and not p.frame_meta


def validate():
    checks=replays=equalities=0
    for projection in ((),('flag',),('done','flag')):
        for resources,costs in [((),None),((1,0),{'make':(1,0),'sense':(0,1),'flag':(1,0)}),
                                ((3,1),{'make':(1,0),'sense':(0,1),'flag':(1,0)})]:
            t=CompiledTask(DOMAIN,PROBLEM,projection_predicates=projection,resources=resources,resource_costs=costs)
            oracle=independent_oracle(case(t));e=PredictiveCapacity(t);old=CatalogCapacity(t)
            planners=[PredictivePlanner(t,m) for m in ('shadow','observe','joint')]
            leaf=IndexedPlanner(t)
            for belief,depth in reachable_contexts(case(t)):
                for count in range(1,len(belief)+1):
                    for selected in combinations(belief,count):
                        sub=frozenset(selected)
                        if any(not t.allowed(s) for _,s in sub):continue
                        truth=oracle(sub,depth);live=[(n,s) for n,s in sub if not t.goal.holds(s)]
                        keys={e.owner.project(s) for _,s in live}
                        if len(keys)==1:
                            key=next(iter(keys));mask=sum(e.owner.model_bits[n] for n,_ in live)
                            assert complete(e,e.node(key,mask,depth))==complete(old,old.node(key,mask,depth));equalities+=1
                        for p in planners:
                            answer=p.solve(sub,depth);assert answer.exact and answer.upper==truth
                            if truth<inf:assert p.verify(sub,depth,answer.policy)==truth;replays+=1
                        leaf.solve(sub,depth)
                        assert planners[0].expanded==leaf.expanded
                        checks+=1
    return dict(contexts=checks,capacity_equalities=equalities,policy_replays=replays)


def test_predictors_do_not_change_exact_answers_or_shadow_expansions():
    assert validate()['contexts']>100
