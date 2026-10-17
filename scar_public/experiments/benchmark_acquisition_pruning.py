"""Paired no-API timing on chronological real game public states.

Query selection uses every recorded craft/resource-target, including easy and
unknown cases. Separate clones preserve discovery side effects between arms.
Measured time includes deep copy, compilation, relaxation and fallback search.
"""
import argparse,copy,json,tarfile,time,statistics
from pathlib import Path
from scar_public.obligations import ExecutionModel


def main():
    p=argparse.ArgumentParser();p.add_argument('archive',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--game',required=True);a=p.parse_args();rows=[];model=ExecutionModel();last=None
    with tarfile.open(a.archive) as t:
        names=sorted(n for n in t.getnames() if '/full_clock/' in n and '/'+a.game+'/trace/' in n)
        for n in names:
            trace=json.load(t.extractfile(n));parsed=json.loads(trace['response'])
            model.observe(trace['observation'],last);last=trace['action']
            target=last.split()[-1] if last.startswith('craft ') else parsed.get('resource_target')
            if not target:continue
            row=dict(game=a.game,step=trace['step'],target=target,arms={})
            for enabled in ([False,True] if trace['step']%2 else [True,False]):
                started=time.perf_counter();clone=copy.deepcopy(model)
                plan=clone.acquisition(target,prune_impossible=enabled)
                elapsed=time.perf_counter()-started
                row['arms']['pruned' if enabled else 'base']=dict(seconds=elapsed,plan=plan,
                    discovery_checks=clone.discovery_checks,pruning=clone.last_acquisition_pruning)
            rows.append(row)
    def total(arm):return dict(seconds=sum(r['arms'][arm]['seconds'] for r in rows),
        search_nodes=sum(r['arms'][arm]['plan'].get('search_nodes',0) for r in rows),
        candidates=sum(r['arms'][arm]['plan']['status']=='candidate' for r in rows))
    changed=[dict(step=r['step'],target=r['target'],base=r['arms']['base']['plan'],pruned=r['arms']['pruned']['plan'])
        for r in rows if {k:v for k,v in r['arms']['base']['plan'].items() if k!='search_nodes'}!={k:v for k,v in r['arms']['pruned']['plan'].items() if k!='search_nodes'}]
    out=dict(game=a.game,scope='No API; reused development trajectories, query-level computational comparison',
        queries=len(rows),base=total('base'),pruned=total('pruned'),changed_outputs=changed,rows=rows)
    a.output.write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k!='rows'}))


if __name__=='__main__':main()
