from scar_public.compiled_task import CompiledTask
from scar_public.certificate_refinement import projection_view
from scar_public.incremental_channels import IncrementalCoverage


def test_single_static_group_collapses_to_scalar():
    d='''(define (domain x) (:predicates (hidden) (done) (phase))
    (:action sense :parameters () :observe (hidden))
    (:action flip :parameters () :effect (and (hidden) (phase)))
    (:action finish :parameters () :precondition (phase) :effect (when (hidden) (done))))'''
    p='(define (problem x) (:domain x) (:init (unknown (hidden))) (:goal (done)))'
    task=CompiledTask(d,p,resources=(2,),resource_costs={'sense':(1,),'flip':(1,),'finish':(1,)})
    assert len(set(task.static_bits)) == 1
    for projected in (0,task.dynamic_mask):
        view=projection_view(task,projected);bound=IncrementalCoverage(view)
        for bits in (0,projected):
            for resource in range(3):
                for depth in range(5):
                    key=(resource,),bits;count=bound.capacity(key,depth)
                    assert count in (0,len(task.models))
                    for mask in range(1,1<<len(task.models)):
                        assert bound.relational_capacity(key,mask,depth) == (mask.bit_count() if count else 0)
