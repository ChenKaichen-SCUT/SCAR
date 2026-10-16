"""Independent AST/set interpreter and exhaustive small-instance bound checks."""
import argparse,json
from collections import deque
from itertools import combinations
from math import inf
from pathlib import Path
from types import SimpleNamespace

from scar_public.benchmark_suite import configurations,load_case,source_text
from scar_public.contingent_benchmarks import sexpr
from scar_public.information_reference import independent_oracle,reachable_contexts
from scar_public.symbolic_task import SymbolicTask
from scar_public.symbolic_coverage import SymbolicCoverage,ExplicitCoverage,LazyCoveragePlanner


def source_conformance(cache):
    """Every action on sampled reachable states, using raw ASTs and fact sets.

    Reachable-state sampling is bounded at depth 3 / 500 states per source task;
    transition agreement is not claimed as proof for the entire PDDL language.
    """
    result=[]
    for config in configurations():
        if config['cohort']!='original':continue
        task,_=load_case(cache,config);d,p,_=source_text(cache,config['family'],config['instance'])
        domain,problem=sexpr(d),sexpr(p)
        schemas={a[1]:dict(zip(a[2::2],a[3::2])) for a in domain if isinstance(a,list) and a and a[0]==':action'}
        goal=next(x[1] for x in problem if isinstance(x,list) and x and x[0]==':goal')
        def facts(s):return frozenset(a for i,a in enumerate(task.atom_names) if s.symbols[0]&(1<<i))
        def holds(x,fs,env):
            if not x:return True
            op=x[0]
            if op=='not':return not holds(x[1],fs,env)
            if op=='and':return all(holds(y,fs,env) for y in x[1:])
            if op=='or':return any(holds(y,fs,env) for y in x[1:])
            if op=='oneof':return sum(holds(y,fs,env) for y in x[1:])==1
            if op=='=':return env.get(x[1],x[1])==env.get(x[2],x[2])
            return tuple(env.get(y,y) for y in x) in fs
        def transition(fs,name):
            verb,*args=name.split();fields=schemas[verb]
            params=[v for v in fields.get(':parameters',[]) if v.startswith('?')]
            env=dict(zip(params,args))
            if not holds(fields.get(':precondition',[]),fs,env):return None
            add=set();delete=set()
            def effects(x):
                if not x:return
                if x[0]=='and':
                    for y in x[1:]:effects(y)
                elif x[0]=='when':
                    if holds(x[1],fs,env):effects(x[2])
                elif x[0]=='not':delete.add(tuple(env.get(y,y) for y in x[1]))
                else:add.add(tuple(env.get(y,y) for y in x))
            effects(fields.get(':effect',[]));nxt=(fs-delete)|add
            obs=(holds(fields[':observe'],nxt,env),) if ':observe' in fields else ()
            return nxt,obs
        initial=sorted((s for _,s in task.belief),key=lambda s:s.symbols)
        queue=deque((s,0) for s in initial);seen=set(initial);states=checks=goals=0
        while queue and states<500:
            s,depth=queue.popleft();states+=1;fs=facts(s)
            assert task.goal.holds(s)==holds(goal,fs,{});goals+=1
            for action in task.actions:
                reference=transition(fs,action);nxt,obs=task.step(s,action);checks+=1
                if reference is None:assert not task.allowed(nxt)
                else:
                    assert task.allowed(nxt) and (facts(nxt),obs)==reference,(config['id'],action)
                    if depth<3 and nxt not in seen:seen.add(nxt);queue.append((nxt,depth+1))
        result.append(dict(id=config['id'],checked_states=states,transition_checks=checks,goal_checks=goals,
                           depth_limit=3,state_limit=500,remaining_queue=len(queue)))
    return result


def exact_checks():
    domain='''(define (domain test) (:types box) (:predicates (hidden ?b - box) (done) (ready))
    (:action sense :parameters (?b - box) :observe (hidden ?b))
    (:action make :parameters (?b - box) :effect (when (hidden ?b) (done)))
    (:action prepare :parameters () :effect (and (ready) (when (ready) (done))))
    (:action undo :parameters () :effect (not (done))))'''
    problem='''(define (problem test) (:domain test) (:objects a b c - box)
    (:init (oneof (hidden a) (hidden b) (hidden c))) (:goal (done)))'''
    checks=dominance=solves=replays=contexts=0
    for resources in ((),(0,0),(1,0),(2,1),(3,1)):
        for projection in ((),('ready',),('ready','done')):
            costs={} if not resources else {'make':(1,0),'sense':(0,1),'prepare':(1,0)}
            t=SymbolicTask(domain,problem,resources=resources,resource_costs=costs,projection_predicates=projection)
            c=SimpleNamespace(models=t.models,goal=t.goal,allowed=t.allowed,belief=t.belief,horizon=3)
            oracle=independent_oracle(c)
            bounds=[SymbolicCoverage(t),SymbolicCoverage(t,True),ExplicitCoverage(t)]
            for belief,h in reachable_contexts(c):
                contexts+=1
                for size in range(1,len(belief)+1):
                    for sub in combinations(belief,size):
                        sub=frozenset(sub);truth=oracle(sub,h)
                        for bound in bounds:assert bound.lower(sub,h)<=truth;checks+=1
            for key in bounds[2].channels:
                for h in range(4):assert bounds[2].capacity(key,h)<=bounds[0].capacity(key,h);dominance+=1
            truth=oracle(c.belief,c.horizon)
            for mode in LazyCoveragePlanner.MODES:
                p=LazyCoveragePlanner(t,mode);answer=p.solve(c.belief,c.horizon)
                assert answer.exact and answer.upper==truth;solves+=1
                if truth<inf:assert p.verify(c.belief,c.horizon,answer.policy)==truth;replays+=1
    return dict(contexts=contexts,admissibility_checks=checks,channel_capacity_dominance_checks=dominance,
                solver_value_checks=solves,policy_replays=replays)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();result=dict(exact=exact_checks(),source_conformance=source_conformance(a.cache))
    a.output.write_text(json.dumps(result,indent=2));print(json.dumps(result['exact']))
    print('Source transition checks:',sum(r['transition_checks'] for r in result['source_conformance']))
