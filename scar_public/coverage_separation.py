"""Constructed scale family separating identity capacity from pair/leaf controls.

Explicitly synthetic, not public benchmark evidence. n>=3 initial alternatives;
choose an omitted model; two shared productive actions complete all other models.
A resource-blind recovery exists but costs a third actuation. Every pair is
solvable with two actions, so pair projections and resource-blind leaf conflicts
miss the all-model two-resource obstruction. Scalar channels count the same
already-completed model at a later stage; identity propagation prevents this.
"""
from pathlib import Path
from time import perf_counter
import argparse,json
from scar_public.symbolic_task import SymbolicTask
from scar_public.bounded_resource_coverage import BoundedResourceCoverage
from scar_public.information_controls import InformationControls
from scar_public.budgeted_planner import BudgetedPlanner
from scar_public.finite_planner import printable


def make(n,budget=2):
    assert n>=3
    # prepare-o finishes one non-omitted witness; finish-o finishes all
    # non-omitted witnesses INCLUDING that already-finished one.
    predicates=' '.join(f'(h{i}) (p{i})' for i in range(n))
    actions=[]
    for omit in range(n):
        first=(omit+1)%n
        actions.append(f'(:action sense{omit} :parameters () :observe (h{omit}))')
        actions.append(f'(:action prepare{omit} :parameters () :precondition (start) '
            f':effect (and (not (start)) (p{omit}) (when (h{first}) (done))))')
        effects=' '.join(f'(when (h{i}) (done))' for i in range(n) if i!=omit)
        actions.append(f'(:action finish{omit} :parameters () :precondition (p{omit}) '
            f':effect (and (not (p{omit})) (end) {effects}))')
    actions.append('(:action recover :parameters () :precondition (end) :effect (done))')
    d='(define (domain separation) (:predicates (start) (end) (done) '+predicates+') '+' '.join(actions)+')'
    p='(define (problem separation) (:domain separation) (:init (start) (oneof '+\
        ' '.join(f'(h{i})' for i in range(n))+')) (:goal (done)))'
    costs={f'{verb}{i}':(1,) for i in range(n) for verb in ('prepare','finish','sense')};costs['recover']=(1,)
    return SymbolicTask(d,p,resources=(budget,),resource_costs=costs,
        projection_predicates=('start','end')+tuple(f'p{i}' for i in range(n)))


def evaluate():
    rows=[]
    for n in (3,4,8,16):
        t=make(n);row=dict(models=n,actuation_budget=2,horizon=3)
        for mode in ('counts','lineage'):
            b=BoundedResourceCoverage(t,mode,100000);s=perf_counter()
            lower=b.lower(t.belief,3)
            row[mode]=dict(lower=printable(lower),seconds=perf_counter()-s,stats=b.stats)
        c=InformationControls(t,work_limit=1000000);s=perf_counter()
        leaf=c.leaf_lower(t.belief,3);row['leaf']=dict(lower=printable(leaf),seconds=perf_counter()-s)
        s=perf_counter();pair=c.pair_lower(t.belief,3)
        row['pair']=dict(lower=printable(pair),seconds=perf_counter()-s,stats=c.stats)
        assert leaf==0 and pair<=2
        assert row['counts']['lower']==2 and row['lineage']['lower']=='infinity'
        if n<=8:
            q=BudgetedPlanner(t,'cheap');r=q.solve(t.belief,3)
            assert r.exact and r.upper==float('inf')
            t3=make(n,3);q=BudgetedPlanner(t3,'cheap');r=q.solve(t3.belief,3)
            assert r.exact and r.upper==3 and q.verify(t3.belief,3,r.policy)==3
        rows.append(row)
    return dict(rows=rows,all_passed=True,scope='Constructed structural separation and scale check, not independent public evaluation.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    r=evaluate();a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2))
    print(json.dumps([dict(models=x['models'],counts=x['counts']['lower'],lineage=x['lineage']['lower'],
        leaf=x['leaf']['lower'],pair=x['pair']['lower']) for x in r['rows']]))
