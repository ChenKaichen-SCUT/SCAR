from collections import deque
from itertools import combinations
from math import inf
from scar_public.compiled_task import CompiledTask
from scar_public.symbolic_task import SymbolicTask
from scar_public.finite_planner import State
from scar_public.test_symbolic_coverage import DOMAIN,PROBLEM,case
from scar_public.information_reference import independent_oracle,reachable_contexts
from scar_public.decision_coverage import DecisionCoverage,DecisionPlanner
from scar_public.budgeted_planner import InferenceStop


def signature(task,state):
    return frozenset(n for i,n in enumerate(task.atom_names) if state.symbols[0]&(1<<i)),state.symbols[1],state.resources


def translate(old,new,state):
    names,valid,resources=signature(old,state)
    return State((sum(1<<i for i,n in enumerate(new.atom_names) if n in names),valid),resources)


def equivalence(domain,problem,depth=3,**kwargs):
    old=SymbolicTask(domain,problem,**kwargs);new=CompiledTask(domain,problem,**kwargs)
    assert {signature(old,s) for _,s in old.belief}=={signature(new,s) for _,s in new.belief}
    queue=deque((s,0) for _,s in old.belief);seen=set();checks=0
    while queue:
        s,d=queue.popleft()
        if s in seen:continue
        seen.add(s);ns=translate(old,new,s)
        assert old.goal.holds(s)==new.goal.holds(ns)
        applicable=set(new.applicable(ns));legal=set()
        for action in old.actions:
            child,obs=old.step(s,action)
            if not old.allowed(child):continue
            legal.add(action);assert action in new.actions
            actual,actual_obs=new.step(ns,action)
            assert signature(old,child)==signature(new,actual) and obs==actual_obs
            if d<depth:queue.append((child,d+1))
            checks+=1
        assert legal==applicable
    return checks


def test_static_joins_uncertain_facts_and_index_preserve_transitions():
    assert equivalence(DOMAIN,PROBLEM)>0
    domain='''(define (domain check) (:predicates (conn ?x ?y) (at ?x) (blocked ?x) (done))
    (:action move :parameters (?x ?y) :precondition (and (conn ?x ?y) (at ?x) (not (= ?x ?y)))
      :effect (and (not (at ?x)) (at ?y)))
    (:action finish :parameters (?x) :precondition (and (at ?x) (or (not (blocked ?x)) (conn ?x ?x))) :effect (done))
    (:action see :parameters (?x) :observe (not (blocked ?x))))'''
    problem='''(define (problem check) (:domain check) (:objects a b c)
    (:init (at a) (conn a b) (unknown (conn b c)) (unknown (blocked c))) (:goal (done)))'''
    assert equivalence(domain,problem)>0


def test_static_join_avoids_cartesian_limit_without_truncation():
    domain='''(define (domain join) (:predicates (edge ?a ?b) (tag ?c) (done))
    (:action act :parameters (?a ?b ?c ?d) :precondition (and (edge ?a ?b) (tag ?c) (= ?d ?a)) :effect (done)))'''
    problem='(define (problem join) (:domain join) (:objects '+' '.join('p'+str(i) for i in range(40))+') (:init (edge p0 p1) (tag p2)) (:goal (done)))'
    t=CompiledTask(domain,problem,ground_limit=2)
    assert list(t.actions)==['act p0 p1 p2 p0']
    assert t.grounding_stats['cartesian_bindings']==40**4
    assert t.grounding_stats['emitted_bindings']==1


def validate():
    checks=replays=witness_checks=0
    for resources,costs in [((),None),((1,0),{'make':(1,0),'sense':(0,1),'flag':(1,0)}),
            ((3,1),{'make':(1,0),'sense':(0,1),'flag':(1,0)})]:
        t=CompiledTask(DOMAIN,PROBLEM,resources=resources,resource_costs=costs,projection_predicates=('flag',))
        c=case(t);oracle=independent_oracle(c);bound=DecisionCoverage(t)
        planners=[DecisionPlanner(t,m) for m in DecisionPlanner.MODES]
        for belief,h in reachable_contexts(c):
            for size in range(1,len(belief)+1):
                for subset in combinations(belief,size):
                    b=frozenset(subset);truth=oracle(b,h)
                    for m in ('count_threshold','relation_threshold','relation_gate'):
                        prune,e=bound.decide(b,h,m)
                        assert not prune or truth==inf;checks+=1
                    live=[(n,s) for n,s in b if not t.goal.holds(s)]
                    keys={bound.project(s) for _,s in live}
                    if live and len(keys)==1:
                        key=next(iter(keys));mask=sum(bound.model_bits[n] for n,_ in live)
                        w=bound.witness_value(key,mask,h);r=bound.relational_capacity(key,mask,h)
                        assert 0<=w<=r<=min(mask.bit_count(),bound.capacity(key,h));witness_checks+=1
                    for p in planners:
                        result=p.solve(b,h);assert result.exact and result.upper==truth;checks+=1
                        if truth<inf:assert p.verify(b,h,result.policy)==truth;replays+=1
    return dict(oracle_checks=checks,witness_inequalities=witness_checks,policy_replays=replays,passed=True)


def test_bound_witness_and_search_agree_with_independent_oracle():assert validate()['passed']


def test_no_budget_fallback_is_safe():
    t=CompiledTask(DOMAIN,PROBLEM)
    p=DecisionPlanner(t);p.tail_limit=0;p.target_seconds=3
    result=p.solve(t.belief,3)
    assert result.exact and result.upper==2 and p.verify(t.belief,3,result.policy)==2
    b=DecisionCoverage(t);b.deadline=0
    try:b.decide(t.belief,2,'relation_gate')
    except InferenceStop:pass
    else:assert False
    b.deadline=inf;assert b.decide(t.belief,2,'relation_gate')[0] is False


if __name__=='__main__':
    import argparse,json
    from pathlib import Path
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    test_static_joins_uncertain_facts_and_index_preserve_transitions()
    test_static_join_avoids_cartesian_limit_without_truncation();test_no_budget_fallback_is_safe()
    r=validate();a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2));print(json.dumps(r))
