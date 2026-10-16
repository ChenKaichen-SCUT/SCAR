from itertools import combinations
from math import inf
from scar_public.compiled_task import CompiledTask
from scar_public.test_symbolic_coverage import DOMAIN, PROBLEM, case
from scar_public.information_reference import independent_oracle, reachable_contexts
from scar_public.certificate_refinement import projection_view
from scar_public.decision_coverage import DecisionCoverage
from scar_public.incremental_channels import ChannelPool, IncrementalCoverage, IncrementalPlanner
from scar_public.coverage_separation import make


def normalized(channels):
    return {a:(g,tuple(sorted(children))) for a,g,children in channels if g or children}


def validate():
    pattern_checks = capacity_checks = search_checks = replays = 0
    for resources,costs in [((),None),((1,0),{'make':(1,0),'sense':(0,1),'flag':(1,0)}),
            ((3,1),{'make':(1,0),'sense':(0,1),'flag':(1,0)})]:
        task = CompiledTask(DOMAIN,PROBLEM,resources=resources,resource_costs=costs)
        pool = ChannelPool(task); oracle = independent_oracle(case(task))
        for extra in range(1 << len(task.dynamic)):
            mask = sum(1<<i for j,i in enumerate(sorted(task.dynamic)) if extra & (1<<j))
            view = projection_view(task,mask)
            old,new = DecisionCoverage(view),IncrementalCoverage(view,pool=pool)
            planner = IncrementalPlanner(view)
            for belief,h in reachable_contexts(case(view)):
                for _,s in belief:
                    for static in set(task.static_bits):
                        for a in task.actions.values():
                            p = s.symbols[0] & view.projection_mask
                            x,y = old.pattern(static,p,a),new.pattern(static,p,a)
                            assert x[0] == y[0] and set(x[1]) == set(y[1]); pattern_checks += 1
                    key = new.project(s)
                    for d in range(h+1):
                        assert old.capacity(key,d) == new.capacity(key,d)
                        for candidates in range(1,1<<len(task.models)):
                            assert old.relational_capacity(key,candidates,d) == new.relational_capacity(key,candidates,d)
                            capacity_checks += 1
                    old.get_channels(key);new.get_channels(key)
                    assert normalized(old.mask_channels[key]) == normalized(new.mask_channels[key])
                for size in range(1,len(belief)+1):
                    for ws in combinations(belief,size):
                        sub = frozenset(ws); truth = oracle(sub,h); answer = planner.solve(sub,h)
                        assert answer.exact and answer.upper == truth; search_checks += 1
                        if truth < inf:
                            assert planner.verify(sub,h,answer.policy) == truth; replays += 1
    return dict(pattern_equivalences=pattern_checks,capacity_equivalences=capacity_checks,
        oracle_checks=search_checks,policy_replays=replays,passed=True)


def test_equivalent_channels_and_search():
    assert validate()['capacity_equivalences'] > 0


def test_cross_projection_reuse_and_written_dependencies():
    d = '''(define (domain x) (:predicates (hidden) (done) (p) (q))
      (:action finish :parameters () :effect (when (hidden) (done)))
      (:action change :parameters () :effect (when (p) (q)))
      (:action reset :parameters () :effect (and (not (p)) (not (q)))))'''
    p = '(define (problem x) (:domain x) (:init (unknown (hidden)) (p)) (:goal (done)))'
    task = CompiledTask(d,p); pool = ChannelPool(task)
    ids = {a:i for i,a in enumerate(task.atom_names)}
    pbit,qbit = 1<<ids['p',],1<<ids['q',]
    a,b = IncrementalCoverage(task,pool=pool),IncrementalCoverage(projection_view(task,pbit),pool=pool)
    action = task.actions['finish'];static = task.static_bits[0]
    x = a.pattern(static,0,action);before = pool.stats['pattern_misses']
    y = b.pattern(static,pbit,action)
    assert pool.stats['pattern_misses'] == before and y[0] == x[0]
    assert {n for _,n in y[1]} == {n|pbit for _,n in x[1]}
    c = IncrementalCoverage(projection_view(task,pbit|qbit),pool=pool)
    action = task.actions['change']
    no = c.pattern(static,0,action);yes = c.pattern(static,pbit,action)
    assert {n for _,n in no[1]} != {n for _,n in yes[1]}


def test_identity_separation_is_preserved():
    for n in (3,4,8):
        task = make(n); old,new = DecisionCoverage(task),IncrementalCoverage(task)
        key = old.project(next(iter(task.belief))[1]); mask = (1<<n)-1
        assert old.capacity(key,3) == new.capacity(key,3) == n
        assert old.relational_capacity(key,mask,3) == new.relational_capacity(key,mask,3) == n-1


if __name__ == '__main__':
    import argparse,json
    from pathlib import Path
    p = argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a = p.parse_args()
    test_cross_projection_reuse_and_written_dependencies();test_identity_separation_is_preserved()
    result = validate();a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2));print(json.dumps(result))
