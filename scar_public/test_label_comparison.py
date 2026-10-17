from math import inf
from scar_public.label_scale_suite import normalize
from scar_public.label_pair_control import TimedPairs,PairControlPlanner
from scar_public.coverage_separation import make
from scar_public.compiled_task import CompiledTask
from scar_public.symbolic_task import SymbolicTask
from scar_public.bounded_resource_coverage import BoundedResourceCoverage

def test_observation_conversion_preserves_two_branches():
    d='(define (domain d) (:predicates (h) (g)) (:action inspect :parameters () :effect (and (observe (h)) (observe (not (h))))))'
    p='(define (problem p) (:domain d) (:init (uncertain (h))) (:goal (g)))'
    d,p,notes=normalize(d,p);t=CompiledTask(d,p)
    outcomes={t.step(s,'inspect')[1] for _,s in t.belief}
    assert len(outcomes)==2 and len(notes)==2

def test_resource_pair_complete_and_interrupted():
    t=make(4);c=TimedPairs(t)
    assert c.pair_lower(t.belief,2)==2
    c=TimedPairs(t);c.deadline=0
    assert c.pair_lower(t.belief,2)==0 and c.stats['pair_fallbacks']==1

def test_reverse_label_separation():
    d='(define (domain d) (:predicates (h) (p) (done)) (:action sustain :parameters () :precondition (p) :effect (p)) (:action finish :parameters () :precondition (p) :effect (done)))'
    p='(define (problem p) (:domain d) (:init (unknown (h))) (:goal (done)))'
    t=CompiledTask(d,p,resources=(1,),resource_costs={'sustain':(1,),'finish':(1,)})
    c=BoundedResourceCoverage(t,'lineage',10000)
    # p cannot appear in any labelled planning graph. Existential omission can invent it.
    assert c.lower(t.belief,1)==1
    assert all(not t.applicable(s) for _,s in t.belief)
    q=PairControlPlanner(t);r=q.solve(t.belief,1)
    assert r.exact and r.upper==inf
