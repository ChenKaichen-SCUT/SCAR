"""Fixed saved queries: identical refined projection and cold/shared-core timing."""
import argparse,json
from pathlib import Path
from time import perf_counter
from scar_public import holdout_suite
from scar_public.compiled_task import CompiledTask
from scar_public.finite_planner import State
from scar_public.certificate_refinement import projection_view
from scar_public.decision_coverage import DecisionCoverage
from scar_public.incremental_channels import IncrementalCoverage,ChannelPool
from scar_public.budgeted_planner import InferenceStop
from scar_public.symbolic_coverage import Unavailable


def main():
    p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,required=True)
    p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    holdout_suite.SymbolicTask=CompiledTask;source=json.loads(a.input.read_text());rows=[]
    for entry in source['public']:
        task,origin=holdout_suite.load_case(a.cache,entry['config']);pool=ChannelPool(task)
        ids={tuple(n):i for i,n in enumerate(task.atom_names)}
        for index,q in enumerate(entry['queries']):
            belief=frozenset((s['name'],State((s['bits'],s['valid']),tuple(s['resources']))) for s in q['belief'])
            extra=sum(1<<ids[tuple(n)] for n in q['selection_evidence']['refinement']['added_atoms'])
            view=projection_view(task,extra);live=[(n,s) for n,s in belief if not task.goal.holds(s)]
            results={}
            # Fixed rotation mitigates always-first execution; one deterministic run.
            modes=['old','cold_core','shared_core'];k=index%3
            for mode in modes[k:]+modes[:k]:
                started=perf_counter()
                bound=DecisionCoverage(view) if mode=='old' else IncrementalCoverage(view,pool=pool if mode=='shared_core' else None)
                bound.deadline=started+1.
                key=bound.project(live[0][1]);mask=sum(bound.model_bits[n] for n,_ in live)
                try:
                    count=bound.capacity(key,q['budget']);identity=bound.relational_capacity(key,mask,q['budget'])
                    results[mode]=dict(status='complete',scalar=count,identity=identity,
                        separation=count>=len(live)>identity)
                except (InferenceStop,Unavailable):
                    results[mode]=dict(status='unknown')
                results[mode].update(seconds=perf_counter()-started,stats=bound.stats)
            vals={(v['scalar'],v['identity']) for v in results.values() if v['status']=='complete'}
            assert len(vals)<=1
            rows.append(dict(id=entry['config']['id'],query=index,budget=q['budget'],candidates=len(live),
                projection=q['selection_evidence']['refinement']['added_atoms'],results=results))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(dict(rows=rows,queries=len(rows),api_calls=0,
        scope='Previously saved post-hoc queries, identical projections, 1s per evaluation, one run; not a holdout.'),indent=2))
    print(json.dumps(dict(queries=len(rows),completed_values_consistent=True)))


if __name__=='__main__':main()
