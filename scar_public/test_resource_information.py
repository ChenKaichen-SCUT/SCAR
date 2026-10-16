from itertools import combinations
from math import inf
from scar_public.compiled_task import CompiledTask
from scar_public.test_symbolic_coverage import DOMAIN, PROBLEM, case
from scar_public.information_reference import independent_oracle, reachable_contexts
from scar_public.resource_information import ResourceInformation
from scar_public.amortized_refinement import AmortizedPlanner


def validate():
    checks = replays = prunes = 0
    for resources,costs in [((),None),((1,0),{'make':(1,0),'sense':(0,1),'flag':(1,0)}),
            ((3,1),{'make':(1,0),'sense':(0,1),'flag':(1,0)})]:
        task = CompiledTask(DOMAIN,PROBLEM,resources=resources,resource_costs=costs)
        oracle = independent_oracle(case(task)); control = ResourceInformation(task,work_limit=10000000)
        planners = [AmortizedPlanner(task,m) for m in ('amortized_count','amortized_relation')]
        for belief, depth in reachable_contexts(case(task)):
            if any(not task.allowed(s) for _,s in belief):
                continue
            for k in range(1,len(belief)+1):
                for subset in combinations(belief,k):
                    sub = frozenset(subset); truth = oracle(sub,depth)
                    reject,_ = control.decide(sub,depth)
                    assert not reject or truth == inf
                    prunes += reject
                    for planner in planners:
                        answer = planner.solve(sub,depth)
                        assert answer.exact and answer.upper == truth
                        if truth < inf:
                            assert planner.verify(sub,depth,answer.policy) == truth
                            replays += 1
                    checks += 1
    return dict(context_checks=checks,policy_replays=replays,certified_prunes=prunes,passed=True)


def test_resource_control_and_amortized_search_against_oracle():
    assert validate()['context_checks'] > 0


def test_kraft_certificate_and_interruption():
    domain = '''(define (domain x) (:types item) (:predicates (hidden ?x - item) (done))
      (:action sense :parameters (?x - item) :observe (hidden ?x))
      (:action finish :parameters (?x - item) :precondition (hidden ?x) :effect (done)))'''
    problem = '''(define (problem x) (:domain x) (:objects a b c - item)
      (:init (oneof (hidden a) (hidden b) (hidden c))) (:goal (done)))'''
    task = CompiledTask(domain,problem,resources=(1,1),resource_costs={'sense':(0,1),'finish':(1,0)})
    control = ResourceInformation(task)
    reject,e = control.decide(task.belief,3)
    assert reject and e['kraft_numerator'] == 3 and e['kraft_denominator'] == 2
    assert set(e['observation_caps'].values()) == {1}
    assert independent_oracle(case(task))(task.belief,3) == inf
    stopped = ResourceInformation(task,work_limit=0)
    reject,e = stopped.decide(task.belief,3)
    assert not reject and not e['complete']


def test_goal_may_continue_and_observing_effects_count_once():
    domain = '''(define (domain x) (:predicates (hidden) (done))
     (:action sense-finish :parameters () :effect (done) :observe (hidden))
     (:action undo :parameters () :effect (not (done))))'''
    problem = '(define (problem x) (:domain x) (:init (unknown (hidden)) (done)) (:goal (done)))'
    task = CompiledTask(domain,problem,resources=(2,),resource_costs={'sense-finish':(1,)})
    control = ResourceInformation(task)
    assert all(control.max_observations(s,3)==2 for _,s in task.belief)
