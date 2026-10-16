from math import inf
from scar_public.test_symbolic_coverage import task,case
from scar_public.information_reference import independent_oracle,reachable_contexts
from scar_public.transition_budgeted_planner import TransitionBudgetedPlanner


def test_forced_midlayer_interruption_keeps_search_exact():
    t=task();c=case(t);oracle=independent_oracle(c)
    for mode in ('cheap','leaf','leaf_lineage_scheduled'):
        p=TransitionBudgetedPlanner(t,mode);p.tail_limit=0
        for belief,h in reachable_contexts(c):
            answer=p.solve(belief,h);truth=oracle(belief,h)
            assert answer.exact and answer.upper==truth
            if truth<inf:assert p.verify(belief,h,answer.policy)==truth
        assert p.tail_steps==0 and p.tail_stops>0


def test_hmax_exhaustion_and_scheduler_skip_are_safe():
    t=task();p=TransitionBudgetedPlanner(t,'leaf_lineage_scheduled')
    p.cost_stats['hmax_work']=2000000;p.cost_stats['coverage_attempts']=32;p.tail_limit=0
    result=p.solve(t.belief,3)
    assert result.exact and result.upper==2 and p.verify(t.belief,3,result.policy)==2
    assert p.cost_stats['hmax_work']==2000000 and p.cost_stats['coverage_attempts']==32
