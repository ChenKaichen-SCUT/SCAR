from itertools import combinations
from math import inf
from types import SimpleNamespace
from unittest.mock import patch

from scar_public.finite_planner import State
from scar_public.information_reference import independent_oracle,reachable_contexts
from scar_public.symbolic_task import SymbolicTask
from scar_public.symbolic_coverage import SymbolicCoverage,ExplicitCoverage,LazyCoveragePlanner,Unavailable


DOMAIN='''(define (domain check) (:types box)
(:predicates (hidden ?b - box) (done) (flag))
(:action sense :parameters (?b - box) :observe (hidden ?b))
(:action make :parameters (?b - box) :effect (when (hidden ?b) (done)))
(:action flag :parameters () :effect (and (flag) (when (flag) (done))))
(:action undo :parameters () :effect (not (done))))'''
PROBLEM='''(define (problem check) (:domain check) (:objects a b c - box)
(:init (oneof (hidden a) (hidden b) (hidden c))) (:goal (done)))'''


def task(resources=(),costs=None,projection=()):
    return SymbolicTask(DOMAIN,PROBLEM,resources=resources,resource_costs=costs,projection_predicates=projection)


def case(t,h=3):return SimpleNamespace(models=t.models,goal=t.goal,allowed=t.allowed,belief=t.belief,horizon=h)


def test_initial_worlds_and_simultaneous_effects():
    t=task();assert len(t.models)==3
    for _,s in t.belief:
        first,obs=t.step(s,'flag');assert not t.goal.holds(first) and obs==()
        second,_=t.step(first,'flag');assert t.goal.holds(second)
        third,_=t.step(second,'undo');assert not t.goal.holds(third)


def test_symbolic_channels_overapproximate_reachable_channels():
    for projection in ((),('flag',)):
        t=task((2,1),{'make':(1,0),'sense':(0,1)},projection)
        a=SymbolicCoverage(t);e=ExplicitCoverage(t)
        for key in e.channels:
            for h in range(4):assert e.capacity(key,h)<=a.capacity(key,h)
        assert a.stats['concrete_states_enumerated']==0
        assert e.stats['concrete_states_enumerated']>0


def test_bounds_and_all_solver_variants_against_enumeration():
    for resources,costs in [((),None),((1,0),{'make':(1,0),'sense':(0,1),'flag':(1,0)}),
                            ((3,1),{'make':(1,0),'sense':(0,1),'flag':(1,0)})]:
        t=task(resources,costs,('flag',));c=case(t);oracle=independent_oracle(c)
        bounds=[SymbolicCoverage(t),SymbolicCoverage(t,True),ExplicitCoverage(t)]
        for belief,h in reachable_contexts(c):
            for size in range(1,len(belief)+1):
                for sub in combinations(belief,size):
                    sub=frozenset(sub);truth=oracle(sub,h)
                    for bound in bounds:assert bound.lower(sub,h)<=truth
        truth=oracle(c.belief,c.horizon)
        for mode in LazyCoveragePlanner.MODES:
            p=LazyCoveragePlanner(t,mode);ans=p.solve(c.belief,c.horizon)
            assert ans.exact and ans.upper==truth
            if truth<inf:assert p.verify(c.belief,c.horizon,ans.policy)==truth


def test_incomplete_sat_is_never_infeasibility():
    t=task();b=SymbolicCoverage(t)
    with patch.object(b,'pattern',side_effect=Unavailable('deliberate unknown')):
        assert b.lower(t.belief,3)==0
    assert b.lower(t.belief,3)==0 and b.stats['disabled_reason']


def test_ambiguous_projection_is_optimistic_extra_channel_only():
    t=task(projection=('done',));b=SymbolicCoverage(t)
    p=LazyCoveragePlanner(t)
    child=p.branches(t.belief,'make a')
    assert len(child)==1 and len(next(iter(child.values())))==3
    assert b.lower(t.belief,3)<=2
