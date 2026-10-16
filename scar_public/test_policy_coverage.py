"""Semantic regression and exhaustive finite checks; no LLM calls."""
import unittest
from itertools import combinations, product
from math import inf

from scar_public.contingent_benchmarks import bomb_case, closed_form_value
from scar_public.coverage_planner import CoveragePlanner, PolicyCoverage
from scar_public.finite_planner import State, Goal
from scar_public.information_reference import independent_oracle, reachable_contexts
from scar_public.information_transfer import compile_reachable, TransferInstance


def hidden_goal_machine(code):
    """Independent finite enumeration, including goal undo and hidden success."""
    initial=State((0,True),(2,));costs={'a':1,'b':1}
    def step(model,s,a):
        if not s.symbols[1] or s.resources[0]==0:return State((s.symbols[0],False),s.resources),()
        i=int(model);j=int(a=='b');stage=s.symbols[0]
        nxt=(stage+1+i+j+(code%3))%3
        valid=not ((code//3)%2 and stage==2 and j==0)
        observation=(nxt==1,) if (code//6)%2 else ()
        return State((nxt,valid),(s.resources[0]-1,)),observation
    models=[compile_reachable(str(i),initial,((0,1,2),(False,True)),costs,step) for i in range(3)]
    return TransferInstance(str(code),'hidden_goal',models,Goal(((0,1),)),
        frozenset((m.name,initial) for m in models),3,lambda s:s.symbols[1],{})


class PolicyCoverageTests(unittest.TestCase):
    def test_no_goal_sensor(self):
        c=bomb_case('bts',4);p=CoveragePlanner(c.models,c.goal,c.allowed)
        child=next(iter(p.branches(c.belief,'dunk:p0').values()))
        self.assertEqual(len(child),4)
        self.assertEqual({c.goal.holds(s) for _,s in child},{False,True})
        answer=p.solve(c.belief,4)
        self.assertEqual(answer.upper,4)
        self.assertEqual(p.verify(c.belief,4,answer.policy),4)

    def test_invalid_action_is_not_a_test(self):
        c=bomb_case('btcs',3,3,0,5);p=CoveragePlanner(c.models,c.goal,c.allowed,indices=(0,))
        child=next(iter(p.branches(c.belief,'dunk:p0').values()))
        illegal=next(iter(p.branches(child,'dunk:p1').values()))
        self.assertTrue(all(not c.allowed(s) for _,s in illegal))
        self.assertEqual(p.initial(illegal,3).lower,inf)

    def test_fixed_projection_separation(self):
        c=bomb_case('bts',4,3,0,4)
        values={mode:CoveragePlanner(c.models,c.goal,c.allowed,mode=mode,indices=(0,)).initial(c.belief,4).lower
                for mode in CoveragePlanner.MODES}
        self.assertEqual(values,dict(single=1,pair_exact=2,k3=3,coverage=inf,resource_blind=4))

    def test_closed_form_and_solvers(self):
        for family,n,r,s in product(('bts','btcs'),(2,3),(0,1,2,3),(0,1,2)):
            h=2*n-1;c=bomb_case(family,n,r,s,h);oracle=independent_oracle(c)
            truth=oracle(c.belief,h)
            self.assertEqual(truth,closed_form_value(family,n,r,s,h),(family,n,r,s))
            for mode in CoveragePlanner.MODES:
                p=CoveragePlanner(c.models,c.goal,c.allowed,mode=mode,indices=(0,))
                answer=p.solve(c.belief,h)
                self.assertTrue(answer.exact)
                self.assertEqual(answer.upper,truth,(family,n,r,s,mode))
                if truth<inf:self.assertEqual(p.verify(c.belief,h,answer.policy),truth)
            oracle.cache_clear()

    def test_hidden_goals_undo_and_every_subset(self):
        for code in range(12):
            c=hidden_goal_machine(code);oracle=independent_oracle(c)
            bounds=[PolicyCoverage(c.models,c.goal,c.allowed,forget_resources=blind) for blind in (False,True)]
            for belief,h in reachable_contexts(c):
                for size in range(1,len(belief)+1):
                    for sub in combinations(belief,size):
                        sub=frozenset(sub);truth=oracle(sub,h)
                        for bound in bounds:self.assertLessEqual(bound.lower(sub,h),truth,(code,sub,h))
            for mode in CoveragePlanner.MODES:
                p=CoveragePlanner(c.models,c.goal,c.allowed,mode=mode)
                ans=p.solve(c.belief,c.horizon)
                self.assertEqual(ans.upper,oracle(c.belief,c.horizon))
                if ans.upper<inf:p.verify(c.belief,c.horizon,ans.policy)
            oracle.cache_clear()


if __name__=='__main__':unittest.main()
