"""Mechanism checks, public transition equivalence, and cached CFF policy replay."""
import argparse,json
from pathlib import Path
from time import perf_counter
from scar_public.coverage_separation import make
from scar_public.direct_saturation import SaturationCoverage
from scar_public.decision_coverage import DecisionCoverage
from scar_public.test_decision_coverage import equivalence
from scar_public import holdout_suite
from scar_public.compiled_task import CompiledTask
from scar_public.indexed_planner import IndexedPlanner
from scar_public.published_planners import parse_cff


def main():
    p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    rows=[]
    for n in (3,4,8,16):
        for resources in (2,3):
            t=make(n,resources)
            for mode in ('count_threshold','relation_threshold','relation_gate','direct_gate'):
                b=SaturationCoverage(t) if mode=='direct_gate' else DecisionCoverage(t)
                started=perf_counter();prune,e=b.decide(t.belief,3,'relation_gate' if mode=='direct_gate' else mode)
                assert prune==(resources==2 and mode!='count_threshold')
                rows.append(dict(models=n,resources=resources,mode=mode,prune=prune,
                    seconds=perf_counter()-started,evidence=e,decisions=b.decision_stats,stats=b.stats))
    cases=holdout_suite.configurations();checks=[]
    for name in ('new_cff_unix_1','new_cff_logistics_3','new_cff_blocks_3'):
        c=next(c for c in cases if c['id']==name);d,p,_=holdout_suite.source_text(a.cache,c)
        n=equivalence(d,p,depth=2);checks.append(dict(id=name,transition_checks=n))
    c=next(c for c in cases if c['id']=='new_cff_grid_2')
    holdout_suite.SymbolicTask=CompiledTask;t,_=holdout_suite.load_case(a.cache,c)
    path=Path(__file__).parent/'results/2026-10-17-information-gaps/external_process/new_cff_grid_2/stdout.txt'
    policy=parse_cff(path.read_text());depth=IndexedPlanner(t).verify(t.belief,10000,policy)
    result=dict(separation=rows,public_transition_checks=checks,
        cached_cff_grid2_replay=dict(verified=True,depth=depth,binary_rerun=False),
        scope='Constructed mechanism examples and development consistency checks, not independent performance data.')
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2))
    print(json.dumps(dict(public_checks=checks,cff_grid2_depth=depth,separation_rows=len(rows))))


if __name__=='__main__':main()
