from itertools import combinations,product
from math import inf
from scar_public.test_symbolic_coverage import task,case
from scar_public.information_reference import independent_oracle,reachable_contexts
from scar_public.invariant_coverage import InvariantCoverage
from scar_public.relational_coverage import matching_size,RelationalCoverage,RelationalPlanner


def brute_match(buckets,n):
    best=0
    for assignment in product(range(-1,len(buckets)),repeat=n):
        counts=[0]*len(buckets);valid=True
        for i,j in enumerate(assignment):
            if j<0:continue
            if not buckets[j][0]&(1<<i):valid=False;break
            counts[j]+=1
        if valid and all(c<=cap for c,(_,cap) in zip(counts,buckets)):best=max(best,sum(counts))
    return best


def test_matching_against_all_small_assignments():
    for n in range(1,4):
        for masks in product(range(1<<n),repeat=3):
            for caps in product((1,2),repeat=3):
                buckets=list(zip(masks,caps));assert matching_size(buckets)==brute_match(buckets,n)


def toy(mode,table,count=3):
    b=RelationalCoverage.__new__(RelationalCoverage)
    b.model_count=count;b.channels={q:tuple((a,f.bit_count(),tuple((u.bit_count(),s) for u,s in children)) for a,f,children in rows) for q,rows in table.items()}
    b.mask_channels=table;b.cache={};b.relation_cache={};b.node_limit=None;b.relation_mode=mode
    b._stats={'dp_nodes':0}
    b.relation_stats=dict(nodes=0,fallbacks=0,matching_calls=0,matching_seconds=0,sibling_deduplications=0,capacity_reductions=0,mask_cardinalities={})
    return b


def test_strict_sibling_overlap_and_lineage_examples():
    # Every model can succeed individually; two overlapping branches cannot
    # count model 0 twice to conceal a capacity-one bottleneck for models 1,2.
    table={0:(('a',0,((1,1),(1,2),(6,3))),),1:(('f',1,()),),2:(('f',1,()),),3:(('f1',2,()),('f2',4,()))}
    lineage=toy('lineage',table);matching=toy('matching',table)
    assert lineage.capacity(0,2)==lineage.relational_capacity(0,7,2)==3
    assert matching.relational_capacity(0,7,2)==2
    assert all(matching.relational_capacity(0,1<<i,2)==1 for i in range(3))
    # Downstream witnesses for model 1 cannot complete an incoming model 0.
    b=toy('lineage',{0:(('a',0,((1,1),)),),1:(('f',2,()),)},2)
    assert b.capacity(0,2)==1 and b.relational_capacity(0,1,2)==0


def exhaustive_validation():
    checks=capacity_checks=values=replays=contexts=0
    for resources,costs in [((),None),((0,0),{'make':(1,0),'sense':(0,1),'flag':(1,0)}),
            ((1,0),{'make':(1,0),'sense':(0,1),'flag':(1,0)}),((2,1),{'make':(1,0),'sense':(0,1),'flag':(1,0)}),
            ((3,1),{'make':(1,0),'sense':(0,1),'flag':(1,0)})]:
        for projection in ((),('flag',),('flag','done')):
            t=task(resources,costs,projection);c=case(t);oracle=independent_oracle(c)
            raw=InvariantCoverage(t,False)
            count,lineage,matching=[RelationalCoverage(t,m,None) for m in RelationalCoverage.MODES]
            fallback=RelationalCoverage(t,'matching',0)
            for belief,h in reachable_contexts(c):
                contexts+=1
                for size in range(1,len(belief)+1):
                    for sub in combinations(belief,size):
                        sub=frozenset(sub);truth=oracle(sub,h)
                        base=raw.lower(sub,h);assert count.lower(sub,h)==base
                        left=lineage.lower(sub,h);right=matching.lower(sub,h)
                        assert base<=left<=right<=truth
                        assert fallback.lower(sub,h)<=truth;checks+=5
                        live=[(n,s) for n,s in sub if not t.goal.holds(s)]
                        if live and all(t.allowed(s) for _,s in sub):
                            keys={count.project(s) for _,s in live}
                            if len(keys)==1:
                                q=next(iter(keys));mask=sum(count.model_bits[n] for n,_ in live)
                                a=lineage.relational_capacity(q,mask,h);b=matching.relational_capacity(q,mask,h)
                                assert b<=a<=min(mask.bit_count(),count.capacity(q,h));capacity_checks+=1
            truth=oracle(c.belief,c.horizon)
            for mode in RelationalCoverage.MODES:
                p=RelationalPlanner(t,mode,None);answer=p.solve(c.belief,c.horizon)
                assert answer.exact and answer.upper==truth;values+=1
                if truth<inf:assert p.verify(c.belief,c.horizon,answer.policy)==truth;replays+=1
    return dict(contexts=contexts,lower_checks=checks,capacity_order_checks=capacity_checks,solver_values=values,policy_replays=replays)


def test_admissibility_ordering_and_exact_search():
    assert exhaustive_validation()['lower_checks']>0


def test_budget_fallback_is_an_upper_bound():
    b=toy('matching',{0:(('a',0,((1,1),)),),1:(('f',2,()),)},2);b.node_limit=0
    assert b.relational_capacity(0,1,2)==1 and b.relation_stats['fallbacks']==1


if __name__=='__main__':
    import argparse,json
    from pathlib import Path
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    test_matching_against_all_small_assignments();test_strict_sibling_overlap_and_lineage_examples();test_budget_fallback_is_an_upper_bound()
    result=exhaustive_validation();result.update(matching_checks=sum((1<<n)**3*8 for n in range(1,4)),all_passed=True)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2));print(json.dumps(result))
