from itertools import combinations
from scar_public.test_symbolic_coverage import task,case
from scar_public.information_reference import independent_oracle,reachable_contexts
from scar_public.symbolic_coverage import SymbolicCoverage,ExplicitCoverage
from scar_public.invariant_coverage import InvariantCoverage,InvariantCoveragePlanner

def test_refinement_sandwich_and_admissibility():
    for resources,costs in [((),None),((1,0),{'make':(1,0),'sense':(0,1),'flag':(1,0)}),
                            ((3,1),{'make':(1,0),'sense':(0,1),'flag':(1,0)})]:
        t=task(resources,costs,('flag',));c=case(t);oracle=independent_oracle(c)
        raw=SymbolicCoverage(t);filtered=InvariantCoverage(t,False);refined=InvariantCoverage(t);explicit=ExplicitCoverage(t)
        assert refined.invariant_stats['verified']
        for key in explicit.channels:
            for h in range(4):
                assert explicit.capacity(key,h)<=refined.capacity(key,h)<=raw.capacity(key,h)
                assert filtered.capacity(key,h)==raw.capacity(key,h)
        for belief,h in reachable_contexts(c):
            for size in range(1,len(belief)+1):
                for sub in combinations(belief,size):
                    sub=frozenset(sub);assert refined.lower(sub,h)<=oracle(sub,h)
        for mode in ('symbolic_filtered','symbolic_invariants'):
            p=InvariantCoveragePlanner(t,mode);answer=p.solve(c.belief,c.horizon)
            assert answer.exact and answer.upper==oracle(c.belief,c.horizon)

def test_specific_static_support_is_proved():
    from scar_public.symbolic_task import SymbolicTask
    d='''(define (domain door) (:predicates (open) (there) (done))
    (:action enter :parameters () :precondition (open) :effect (there))
    (:action finish :parameters () :precondition (there) :effect (done)))'''
    p='''(define (problem door) (:domain door) (:init (unknown (open))) (:goal (done)))'''
    t=SymbolicTask(d,p,projection_predicates=('there',));b=InvariantCoverage(t)
    assert b.invariant_stats['verified'] and b.invariant_stats['candidate_invariants']>0
    explicit=ExplicitCoverage(t)
    for key in explicit.channels:
        for h in range(4):assert explicit.capacity(key,h)<=b.capacity(key,h)
