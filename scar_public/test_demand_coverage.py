from itertools import combinations, product
from math import inf
from pathlib import Path
import z3
from scar_public.test_symbolic_coverage import task, case
from scar_public.information_reference import independent_oracle, reachable_contexts
from scar_public.relational_coverage import RelationalCoverage
from scar_public.demand_coverage import DemandCoverage, DemandPlanner, formula
from scar_public.symbolic_task import ze


def test_mixed_boolean_formulas():
    vs = [z3.Bool('v'+str(i)) for i in range(3)]
    expressions = [('and',(1,('not',(2,)),3)),('or',(1,2,3)),('oneof',(1,2,3)),
        ('oneof',(1,1,('not',(2,)))),('not',(('oneof',(1,2,3)),)),('and',()),('or',()),True,False]
    for constants in product((None,False,True),repeat=3):
        values = [v if c is None else c for v,c in zip(vs,constants)]
        baseline = [z3.BoolVal(v) if type(v) is bool else v for v in values]
        for expr in expressions:
            a,b = formula(expr,lambda i:values[i]),ze(expr,baseline)
            s=z3.Solver();s.add(a!=b);assert s.check()==z3.unsat


def test_channel_equality_and_exact_values():
    for projection in ((),('flag',),('flag','done')):
        t=task((3,1),{'make':(1,0),'sense':(0,1),'flag':(1,0)},projection)
        original=RelationalCoverage(t,'matching',None)
        demand=DemandCoverage(t,'matching',None)
        for resources in product(range(4),range(2)):
            for bits in product((False,True),repeat=len(t.projection)):
                q=resources,sum(1<<i for i,b in zip(t.projection,bits) if b)
                assert demand.get_channels(q)==original.get_channels(q)
                assert demand.mask_channels[q]==original.mask_channels[q]
        c=case(t);oracle=independent_oracle(c)
        planners=[DemandPlanner(t,m) for m in DemandPlanner.MODES]
        for belief,h in reachable_contexts(c):
            for size in range(1,len(belief)+1):
                for subset in combinations(belief,size):
                    b=frozenset(subset);truth=oracle(b,h)
                    assert demand.lower(b,h)==original.lower(b,h)<=truth
                    for p in planners:
                        r=p.solve(b,h);assert r.exact and r.upper==truth
                        if truth<inf:assert p.verify(b,h,r.policy)==truth


def benchmark_channel_validation(cache):
    from scar_public.benchmark_suite import configurations,load_case
    checks=0;cases=[]
    for identity in ('doors_5_sNone','rovers_pfile2_sNone','medical_pfile004_sNone'):
        c=next(c for c in configurations() if c['id']==identity)
        t,_=load_case(cache,c)
        a=RelationalCoverage(t,'counts');b=DemandCoverage(t,'counts')
        x=b.lower(t.belief,c['horizon'])
        # Every abstract state queried by the optimized root, including
        # unreachable witnesses, is compared to the old channel constructor.
        for q in list(b.channels):
            assert a.get_channels(q)==b.get_channels(q)
            assert a.mask_channels[q]==b.mask_channels[q]
            checks+=1
        assert a.lower(t.belief,c['horizon'])==x
        cases.append(dict(id=identity,abstract_states=len(b.channels),root=str(x)))
    return dict(channel_states_checked=checks,cases=cases,all_passed=True)


if __name__=='__main__':
    import argparse,json
    p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    test_mixed_boolean_formulas();test_channel_equality_and_exact_values()
    result=benchmark_channel_validation(a.cache)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2))
    print(json.dumps(result))
