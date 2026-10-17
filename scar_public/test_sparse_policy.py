from itertools import combinations
from math import inf
import z3
from scar_public.sparse_policy import SparseEncoding, SparsePolicyPlanner, SparsePolicyCoverage, replay_rule, compress_rule
from time import perf_counter
from scar_public.finite_planner import State
from scar_public.test_progress_carrier import microtask
from scar_public.test_compact_progress import reachable
from scar_public.test_reachable_labels import dynamic_identity
from scar_public.compiled_task import CompiledTask
from scar_public.information_reference import independent_oracle
from scar_public.budgeted_planner import InferenceStop


def sensing_task(sensors):
    domain = '''(define (domain s) (:predicates (hidden) (g))
      (:action sense :parameters () :observe (hidden))
      (:action yes :parameters () :effect (when (hidden) (g)))
      (:action no :parameters () :effect (when (not (hidden)) (g))))'''
    problem = '(define (problem s) (:domain s) (:init (unknown (hidden))) (:goal (g)))'
    return CompiledTask(domain, problem, resources=(1,sensors),
        resource_costs={'yes':(1,0),'no':(1,0),'sense':(0,1)})


def test_actual_observations_and_resources_control_action_agreement():
    for sensors in (0,1):
        task = sensing_task(sensors)
        e = SparseEncoding(task, 2)
        for n,s in task.belief:
            e.add_candidate(n,s,task.dynamic)
        assert e.check() == (z3.sat if sensors else z3.unsat)
        if not sensors:
            assert len(e.certificate()['members']) == 2
        for world in task.belief:
            single = SparseEncoding(task, 2); single.add_candidate(*world,task.dynamic)
            assert single.check() == z3.sat


def test_no_false_rejection_against_independent_small_oracle():
    checks = 0
    for resources in ((2,0),(2,1),(3,1)):
        task,_=microtask(resources,0); oracle=independent_oracle(task)
        for belief in reachable(task,1):
            worlds=sorted(belief,key=lambda w:w[0])
            for size in range(1,len(worlds)+1):
                for subset in combinations(worlds,size):
                    live=[w for w in subset if not task.goal.holds(w[1])]
                    if not live:continue
                    for h in range(4):
                        if oracle(frozenset(subset),h) == inf:continue
                        for pattern in ((),tuple(task.dynamic)):
                            e=SparseEncoding(task,h)
                            for world in live:e.add_candidate(*world,pattern)
                            assert e.check()==z3.sat
                            checks+=1
    assert checks>20


def test_sparse_refinement_finds_sufficient_links_and_core():
    # Initial ready=false is forgotten at first, allowing a spurious finish.
    d='''(define (domain r) (:predicates (ready) (g))
       (:action finish :parameters () :effect (when (ready) (g)))
       (:action repair :parameters () :effect (ready)))'''
    p='(define (problem r) (:domain r) (:init) (:goal (g)))'
    task=CompiledTask(d,p);e=SparseEncoding(task,1)
    rejected,answer=e.run(task.belief)
    assert rejected and answer['certificate']['members']==['m0']
    assert e.stats['refinements']>=1
    assert ('ready',) in [task.atom_names[p] for p in e.frames['m0']['retained']]
    # The sufficient core itself must be independently UNSAT when assumed.
    assumptions=[z3.Bool(label) for label in answer['certificate']['core_labels']]
    assert e.check(assumptions)==z3.unsat


def test_retirement_is_optimistic_not_a_real_plan():
    d='''(define (domain o) (:predicates (h) (g))
      (:action a :parameters () :effect (and (not (g)) (when (h) (g))))
      (:action b :parameters () :effect (and (not (g)) (when (not (h)) (g)))))'''
    p='(define (problem o) (:domain o) (:init (unknown (h))) (:goal (g)))'
    task=CompiledTask(d,p)
    assert independent_oracle(task)(task.belief,2)==inf
    e=SparseEncoding(task,2)
    for w in task.belief:e.add_candidate(*w,task.dynamic)
    assert e.check()==z3.sat  # each name may retire at a different hidden time


def test_no_interruption_is_a_certificate():
    task=sensing_task(0)
    def stop():raise InferenceStop()
    e=SparseEncoding(task,2,stop)
    try:e.run(task.belief)
    except InferenceStop:pass
    else:assert False
    assert not e.frames


def test_search_preserves_optimum_and_replay():
    for task in (sensing_task(0),sensing_task(1),dynamic_identity(3)):
        h=4;expected=independent_oracle(task)(task.belief,h)
        for mode in ('sparse_policy','sparse_fresh','sparse_full'):
            planner=SparsePolicyPlanner(task,mode);r=planner.solve(task.belief,h)
            assert r.exact and r.upper==expected
            if expected<inf:assert planner.verify(task.belief,h,r.policy)==expected


def test_core_minimization_and_progress_resource_guards():
    task=sensing_task(0); e=SparseEncoding(task,2)
    for w in task.belief:e.add_candidate(*w,task.dynamic)
    assert e.check()==z3.unsat
    cert=e.minimize_certificate();assert cert['minimal']
    labels=[z3.Bool(s) for s in cert['core_labels']]
    assert e.check(labels)==z3.unsat
    for label in labels:
        assert e.check([x for x in labels if str(x)!=str(label)])==z3.sat
    c=SparsePolicyCoverage(task);c.rules=[e.rule(cert)]
    assert replay_rule(task,c.rules[0])
    assert c.match_rule(task.belief,2)
    assert c.match_rule(task.belief,1)
    assert not c.match_rule(task.belief,3)
    more=frozenset((n,State(s.symbols,(1,1))) for n,s in task.belief)
    assert c.match_rule(more,2) is None
    finished=frozenset((n,State((s.symbols[0] | (1<<next(iter(task.dynamic))),True),s.resources)) for n,s in task.belief)
    assert c.match_rule(finished,2) is None


def test_compression_enriches_true_states_and_retains_old_proof_on_stop():
    d='''(define (domain c) (:predicates (h0) (h1) (h2) (g))
      (:action a :parameters () :effect (when (h0) (g)))
      (:action b :parameters () :effect (when (h1) (g)))
      (:action c :parameters () :effect (when (h2) (g))))'''
    p='(define (problem c) (:domain c) (:init (oneof (h0) (h1) (h2))) (:goal (g)))'
    task=CompiledTask(d,p,resources=(1,),resource_costs={n:(1,) for n in ('a','b','c')})
    e=SparseEncoding(task,2)
    for world in task.belief:e.add_candidate(*world,task.dynamic)
    assert e.check()==z3.unsat
    rule=e.rule(e.certificate(e.assumptions()))
    assert len(rule['certificate']['members'])==3 and replay_rule(task,rule)
    compressed,stats=compress_rule(task,task.belief,rule,perf_counter()+5.)
    assert stats['candidate_reduced'] and len(compressed['certificate']['members'])==2
    assert replay_rule(task,compressed)
    old,stats=compress_rule(task,task.belief,rule,perf_counter()-1.)
    assert old==rule and stats['unknown']


def test_genuine_three_candidate_core_survives_pair_compression():
    # Every pair can share one action, but all three require two resource units.
    # This is a correctness fixture, not a separation from a counting bound.
    d='''(define (domain k) (:predicates (h0) (h1) (h2) (g))
      (:action a :parameters () :effect (when (not (h0)) (g)))
      (:action b :parameters () :effect (when (not (h1)) (g)))
      (:action c :parameters () :effect (when (not (h2)) (g))))'''
    p='(define (problem k) (:domain k) (:init (oneof (h0) (h1) (h2))) (:goal (g)))'
    task=CompiledTask(d,p,resources=(1,),resource_costs={n:(1,) for n in ('a','b','c')})
    oracle=independent_oracle(task)
    for pair in combinations(task.belief,2):assert oracle(frozenset(pair),2)==1
    assert oracle(task.belief,2)==inf
    e=SparseEncoding(task,2)
    for world in task.belief:e.add_candidate(*world,task.dynamic)
    assert e.check()==z3.unsat
    rule=e.rule(e.minimize_certificate())
    assert len(rule['certificate']['members'])==3
    compressed,stats=compress_rule(task,task.belief,rule,perf_counter()+5.)
    assert not stats['candidate_reduced'] and not stats['unknown']
    assert compressed==rule and replay_rule(task,compressed)
