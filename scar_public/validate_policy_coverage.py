"""Persist independently computed semantic checks, outside timed experiments."""
from itertools import combinations, product
import json
from math import inf
from pathlib import Path

from scar_public.contingent_benchmarks import bomb_case, closed_form_value, check_source_conformance
from scar_public.coverage_planner import CoveragePlanner, PolicyCoverage
from scar_public.information_reference import independent_oracle, reachable_contexts
from scar_public.test_policy_coverage import hidden_goal_machine


def main():
    counts=dict(source_transition_checks=check_source_conformance('../planning_sources/contff-tests.tgz'),
                analytic_reference_checks=0,solver_value_checks=0,policy_replays=0,
                hidden_goal_subset_queries=0,coverage_admissibility_checks=0,
                raw_capacity_final_success_checks=0,hidden_goal_machines=12)
    for family,n,r,s in product(('bts','btcs'),(2,3),(0,1,2,3),(0,1,2)):
        h=2*n-1;c=bomb_case(family,n,r,s,h);oracle=independent_oracle(c)
        truth=oracle(c.belief,h)
        assert truth==closed_form_value(family,n,r,s,h)
        counts['analytic_reference_checks']+=1
        for mode in CoveragePlanner.MODES:
            p=CoveragePlanner(c.models,c.goal,c.allowed,mode=mode,indices=(0,))
            ans=p.solve(c.belief,h);assert ans.exact and ans.upper==truth
            counts['solver_value_checks']+=1
            if truth<inf:
                assert p.verify(c.belief,h,ans.policy)==truth;counts['policy_replays']+=1
        oracle.cache_clear()
    for code in range(12):
        c=hidden_goal_machine(code);oracle=independent_oracle(c)
        bounds=[PolicyCoverage(c.models,c.goal,c.allowed,forget_resources=b) for b in (False,True)]
        queries=set()
        for belief,h in reachable_contexts(c):
            for size in range(1,len(belief)+1):
                queries.update((frozenset(s),h) for s in combinations(belief,size))
        for belief,h in queries:
            truth=oracle(belief,h);counts['hidden_goal_subset_queries']+=1
            for b in bounds:
                assert b.lower(belief,h)<=truth
                counts['coverage_admissibility_checks']+=1
                if truth<inf and not any(c.goal.holds(s) for _,s in belief):
                    keys={b.project(s) for _,s in belief}
                    if len(keys)==1 and not b.stats['disabled_reason']:
                        assert b.capacity(next(iter(keys)),h)>=len(belief)
                        counts['raw_capacity_final_success_checks']+=1
        for mode in CoveragePlanner.MODES:
            p=CoveragePlanner(c.models,c.goal,c.allowed,mode=mode)
            ans=p.solve(c.belief,c.horizon)
            assert ans.exact and ans.upper==oracle(c.belief,c.horizon)
            counts['solver_value_checks']+=1
            if ans.upper<inf:
                p.verify(c.belief,c.horizon,ans.policy);counts['policy_replays']+=1
        oracle.cache_clear()
    result=dict(counts,all_checks_passed=True,api_calls=0,random_seeds_used=False,
                scope='Finite deterministic generated systems and 48 small resource configurations; '
                      'exhaustive reachable contexts/subsets in the 12 hidden-goal machines, not all machines.')
    path=Path('scar_public/results/2026-10-16-policy-coverage/validation.json')
    path.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))


if __name__=='__main__':main()
