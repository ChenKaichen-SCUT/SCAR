from math import inf
from scar_public.compiled_task import CompiledTask
from scar_public.test_symbolic_coverage import DOMAIN, PROBLEM, case
from scar_public.information_reference import independent_oracle, reachable_contexts
from scar_public.witness_refinement import WitnessPlanner, WitnessCoverage
from scar_public.incremental_channels import IncrementalCoverage


def test_witness_gate_preserves_threshold_decisions_and_exact_search():
    for resources,costs in [((),None),((1,0),{'make':(1,0),'sense':(0,1),'flag':(1,0)}),
                           ((3,1),{'make':(1,0),'sense':(0,1),'flag':(1,0)})]:
        task=CompiledTask(DOMAIN,PROBLEM,resources=resources,resource_costs=costs)
        oracle=independent_oracle(case(task));planner=WitnessPlanner(task)
        old,new=IncrementalCoverage(task),WitnessCoverage(task)
        for belief,depth in reachable_contexts(case(task)):
            if any(not task.allowed(s) for _,s in belief):continue
            assert old.decide(belief,depth,'relation_threshold')[0] == new.decide(belief,depth,'relation_threshold')[0]
            truth=oracle(belief,depth);answer=planner.solve(belief,depth)
            assert answer.exact and answer.upper==truth
            if truth<inf:assert planner.verify(belief,depth,answer.policy)==truth
