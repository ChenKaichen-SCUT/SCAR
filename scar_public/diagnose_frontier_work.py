"""New-engine kernel audit against values already stored by previous studies."""
import argparse,json,os
from pathlib import Path
from time import perf_counter
from scar_public.fresh_resource_suite import configurations,load
from scar_public.certificate_refinement import RefinementCoverage,projection_view,indices
from scar_public.resumable_capacity import ResumableCapacity


def main():
    p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--catalog',action='store_true');a=p.parse_args()
    from scar_public.catalog_capacity import CatalogCapacity
    engine_class=CatalogCapacity if a.catalog else ResumableCapacity
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    configs={c['id']:c for c in configurations()}
    rows=[]
    for identity,queries in [('rover4_a16s1',[(8,3),(9,3)]),
                              ('rover6_original',[(3,12)]),('rover8_original',[(3,4)])]:
        task,_=load(a.cache,configs[identity]);sel=RefinementCoverage(task)
        live=[(n,s) for n,s in task.belief if not task.goal.holds(s)]
        sel.deadline=perf_counter()+.25;extra,_=sel.select(live)
        e=engine_class(projection_view(task,extra))
        for depth,expected in queries:
            before=dict(e.work);node=e.node(e.owner.project(live[0][1]),sum(e.owner.model_bits[n] for n,_ in live),depth)
            start=perf_counter();deadline=start+8
            while not node.done and perf_counter()<deadline:e.advance(node,units=4096,seconds=.1)
            if node.done:assert node.lower==expected
            rows.append(dict(id=identity,depth=depth,previous_stored_value=expected,
                status='MATCH' if node.done else 'UNKNOWN',value=node.lower if node.done else None,
                warm_prior_depth=8 if depth==9 else None,seconds=perf_counter()-start,
                projection=[task.atom_names[i] for i in indices(extra)],
                work={k:v-before[k] for k,v in e.work.items()}))
    a.output.write_text(json.dumps(dict(rows=rows,scope='New engine only, same automatically selected projection. Expected values from prior multistep queries.json: Rover4 a16s1 d8/d9 C1=3; Rover6/8 original d3 C1=N. Warm d9 differs in depth from cold d8; do not use their ratio as a speedup.'),indent=2))


if __name__=='__main__':main()
