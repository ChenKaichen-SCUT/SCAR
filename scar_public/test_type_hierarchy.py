import pytest
from scar_public.compiled_task import CompiledTask
from scar_public.decision_coverage import DecisionPlanner
from scar_public.information_reference import independent_oracle
from scar_public.test_symbolic_coverage import case


DOMAIN='''(define (domain x) (:types tool other - object wrench - tool socket - wrench)
 (:constants s - socket w - wrench t - tool o - other)
 (:predicates (usable ?x - tool) (done))
 (:action use :parameters (?x - tool) :precondition (usable ?x) :effect (done)))'''
PROBLEM='''(define (problem x) (:domain x) (:init (usable s) (usable w) (usable t)) (:goal (done)))'''


def test_transitive_subtypes_and_static_join_grounding():
    task=CompiledTask(DOMAIN,PROBLEM)
    assert set(task.actions)=={'use s','use w','use t'}
    assert all(task.goal.holds(task.step(state,'use s')[0]) for _,state in task.belief)
    planner=DecisionPlanner(task,'leaf');answer=planner.solve(task.belief,2)
    assert answer.exact and answer.upper==independent_oracle(case(task))(task.belief,2)==1
    assert planner.verify(task.belief,2,answer.policy)==1


def test_invalid_type_hierarchies_are_rejected():
    for types in ('a - b b - a','a - missing'):
        with pytest.raises(ValueError):
            CompiledTask('(define (domain x) (:types '+types+') (:predicates (done)))',
                '(define (problem x) (:domain x) (:init) (:goal (done)))')
