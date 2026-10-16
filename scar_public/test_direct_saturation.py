from itertools import combinations
from math import inf
from scar_public.compiled_task import CompiledTask
from scar_public.test_symbolic_coverage import DOMAIN,PROBLEM,case
from scar_public.information_reference import independent_oracle,reachable_contexts
from scar_public.direct_saturation import SaturationCoverage,DirectPlanner


def validate():
    certificates=checks=replays=0
    for projection in ((),('flag',),('done','flag')):
        for resources,costs in [((),None),((1,0),{'make':(1,0),'sense':(0,1),'flag':(1,0)}),
                ((3,1),{'make':(1,0),'sense':(0,1),'flag':(1,0)})]:
            t=CompiledTask(DOMAIN,PROBLEM,resources=resources,resource_costs=costs,projection_predicates=projection)
            c=case(t);oracle=independent_oracle(c);b=SaturationCoverage(t);p=DirectPlanner(t)
            for belief,h in reachable_contexts(c):
                for size in range(1,len(belief)+1):
                    for ws in combinations(belief,size):
                        sub=frozenset(ws)
                        if b.direct_saturation(sub,h):
                            live=[(n,s) for n,s in sub if not t.goal.holds(s)]
                            key=b.project(live[0][1]);mask=sum(b.model_bits[n] for n,_ in live)
                            assert b.relational_capacity(key,mask,h)==len(live);certificates+=1
                        truth=oracle(sub,h);r=p.solve(sub,h);checks+=1
                        assert r.exact and r.upper==truth
                        if truth<inf:assert p.verify(sub,h,r.policy)==truth;replays+=1
    return dict(certificates_checked=certificates,oracle_checks=checks,policy_replays=replays,passed=True)


def test_certificates_and_search():assert validate()['certificates_checked']>0


def test_negative_goal_and_conflicting_effects():
    d='''(define (domain x) (:predicates (p) (q))
    (:action fix :parameters () :effect (and (not (p)) (q))))'''
    p='(define (problem x) (:domain x) (:init (unknown (p)) (unknown (q))) (:goal (and (not (p)) (q))))'
    t=CompiledTask(d,p);b=SaturationCoverage(t)
    assert b.direct_saturation(t.belief,1)
    d2=d.replace('(not (p)) (q)', '(not (p)) (p) (q)')
    t2=CompiledTask(d2,p);b2=SaturationCoverage(t2)
    assert not b2.direct_saturation(t2.belief,1)


if __name__=='__main__':
    import argparse,json
    from pathlib import Path
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    test_negative_goal_and_conflicting_effects();r=validate()
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2));print(json.dumps(r))
