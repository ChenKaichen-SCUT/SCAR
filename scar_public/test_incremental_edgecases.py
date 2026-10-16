from scar_public.compiled_task import CompiledTask
from scar_public.certificate_refinement import projection_view
from scar_public.decision_coverage import DecisionCoverage
from scar_public.incremental_channels import IncrementalCoverage,ChannelPool


def test_negative_goal_disjunction_and_conflicting_effects():
    domain='''(define (domain x) (:predicates (p) (q) (r) (s))
    (:action fix :parameters () :precondition (or (p) (not (r)))
      :effect (and (when (oneof (p) (q)) (not (p))) (when (r) (p)) (q)))
    (:action change :parameters () :effect (and (r) (not (s))))
    (:action sense :parameters () :observe (or (p) (not (s)))))'''
    problem='(define (problem x) (:domain x) (:init (unknown (r)) (unknown (p))) (:goal (and (not (p)) (q))))'
    task=CompiledTask(domain,problem);pool=ChannelPool(task)
    for extra in (0,task.dynamic_mask):
        view=projection_view(task,extra);old=DecisionCoverage(view);new=IncrementalCoverage(view,pool=pool)
        for projected in range(1<<len(task.atom_names)):
            projected &= view.projection_mask
            for static in set(task.static_bits):
                for action in task.actions.values():
                    x,y=old.pattern(static,projected,action),new.pattern(static,projected,action)
                    assert x[0]==y[0] and set(x[1])==set(y[1])
