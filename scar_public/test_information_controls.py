from itertools import combinations
from math import inf
from scar_public.test_symbolic_coverage import task,case
from scar_public.information_reference import independent_oracle,reachable_contexts
from scar_public.information_controls import InformationControls
from scar_public.budgeted_planner import BudgetedPlanner,MeteredCoverage,InferenceStop


def validate():
    checks=replays=0
    for resources,costs in [((),None),((0,0),{'make':(1,0),'sense':(0,1),'flag':(1,0)}),
            ((1,0),{'make':(1,0),'sense':(0,1),'flag':(1,0)}),
            ((3,1),{'make':(1,0),'sense':(0,1),'flag':(1,0)})]:
        t=task(resources,costs,('flag',));c=case(t);oracle=independent_oracle(c)
        controls=InformationControls(t)
        planners=[BudgetedPlanner(t,m) for m in BudgetedPlanner.MODES]
        for belief,h in reachable_contexts(c):
            for size in range(1,len(belief)+1):
                for subset in combinations(belief,size):
                    b=frozenset(subset);truth=oracle(b,h)
                    assert controls.leaf_lower(b,h)<=truth
                    assert controls.pair_lower(b,h)<=truth;checks+=2
                    for p in planners:
                        for _,s in b:assert p.hmax(s)<=oracle(frozenset([(next(n for n,v in b if v==s),s)]),h)
                        r=p.solve(b,h);assert r.exact and r.upper==truth;checks+=1
                        if truth<inf:assert p.verify(b,h,r.policy)==truth;replays+=1
    return dict(oracle_checks=checks,policy_replays=replays,all_passed=True)


def test_oracle_and_replay():assert validate()['oracle_checks']>0


def test_exhausted_work_and_time_are_safe():
    t=task();c=InformationControls(t,work_limit=0)
    assert c.leaf_lower(t.belief,3)==0 and c.pair_lower(t.belief,3)==0
    for mode in ('counts','lineage'):
        b=MeteredCoverage(t,mode);b.deadline=0
        try:b.lower(t.belief,3)
        except InferenceStop:pass
        else:assert False
        b.deadline=inf;assert b.lower(t.belief,3)<=2
    p=BudgetedPlanner(t,'leaf_lineage_scheduled');p.bfs_used=4096
    p.cost_stats['coverage_seconds']=3
    r=p.solve(t.belief,3);assert r.exact and r.upper==2


if __name__=='__main__':
    import argparse,json
    from pathlib import Path
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    test_exhausted_work_and_time_are_safe();result=validate()
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2))
    print(json.dumps(result))
