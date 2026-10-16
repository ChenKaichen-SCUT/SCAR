"""Exhaustive contexts/subsets in the SAME 64 generated machines as before."""
from itertools import combinations
import json
from pathlib import Path

from scar_public.control_capacity import ControlCapacity
from scar_public.information_reference import independent_oracle, reachable_contexts
from scar_public.observation_capacity import ObservationCapacity
from scar_public.validate_information_bound import state_machine


def audit_generated(count=64):
    checked=capacity_checks=strict=disabled=0
    for code in range(count):
        case=state_machine(code)
        oracle=independent_oracle(case)
        coarse=ObservationCapacity(case.models,case.goal,case.allowed)
        refined=ControlCapacity(case.models,case.goal,case.allowed,(0,))
        assert coarse.stats['disabled_reason'] is None
        disabled += refined.stats['disabled_reason'] is not None
        projections=set()
        for belief,horizon in reachable_contexts(case):
            worlds=tuple(belief)
            for size in range(1,len(worlds)+1):
                projections.update((frozenset(subset),horizon) for subset in combinations(worlds,size))
        for belief,horizon in projections:
            old,new,truth=coarse.lower(belief,horizon),refined.lower(belief,horizon),oracle(belief,horizon)
            assert old <= new <= truth,(code,belief,horizon,old,new,truth)
            checked += 1
            strict += new > old
        if refined.stats['disabled_reason'] is None:
            for key in refined.channels:
                for horizon in range(4):
                    assert refined.capacity(key,horizon) <= coarse.capacity(key[0],horizon)
                    capacity_checks += 1
        oracle.cache_clear()
    return dict(generated_models=count,checked_belief_horizon_subproblems=checked,
                capacity_refinement_inequality_checks=capacity_checks,strict_lower_improvements=strict,
                fine_globally_disabled_models=disabled,all_bounds_admissible=True,
                all_effective_bounds_dominate_coarse=True,api_calls=0,random_seeds_used=False,
                scope='Same 64 deterministic machines as previous audit; exhaustive reachable contexts '
                      'and subsets within those machines, not all possible transition systems.')


if __name__ == '__main__':
    result=audit_generated()
    path=Path(__file__).parent/'results/2026-10-16-control-capacity/validation.json'
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result),flush=True)
