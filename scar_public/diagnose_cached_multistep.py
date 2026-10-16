"""Bounded root replay of new cached-harvest algorithm on observed Rover failures."""
import argparse,json,os,signal,subprocess,sys
from pathlib import Path
from time import perf_counter
from concurrent.futures import ThreadPoolExecutor
from scar_public.fresh_resource_suite import configurations,load
from scar_public.cached_multistep_refinement import CachedMultistepCoverage
from scar_public.certificate_refinement import indices
from scar_public.budgeted_planner import InferenceStop
from scar_public.symbolic_coverage import Unavailable


def main():
    p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--worker');p.add_argument('--cpu',type=int)
    a=p.parse_args()
    if a.worker:
        import resource
        os.sched_setaffinity(0,{a.cpu});resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
        c=json.loads(a.worker);task,_=load(a.cache,c);b=CachedMultistepCoverage(task)
        started=perf_counter();rows=[];deadline=started+8
        for d in range(1,17):
            b.deadline=min(deadline,perf_counter()+.5);t=perf_counter()
            try:
                prune,e=b.decide(task.belief,d)
                row=dict(depth=d,prune=prune,evidence=e)
            except (InferenceStop,Unavailable):row=dict(depth=d,status='UNKNOWN')
            row['seconds']=perf_counter()-t;rows.append(row)
            if row.get('evidence',{}).get('reason')=='relation_pass' or perf_counter()>=deadline:break
        print(json.dumps(dict(config=c,queries=rows,seconds=perf_counter()-started,
            added_atoms=[task.atom_names[i] for i in indices(b.active_extra or 0)],statistics=b.stats)),flush=True)
        return
    cases=[c for c in configurations() if c['family']=='rovers']
    cpus=sorted(os.sched_getaffinity(0))[::2][:8]
    def run(pair):
        i,c=pair
        proc=subprocess.run([sys.executable,'-m','scar_public.diagnose_cached_multistep','--cache',str(a.cache),
            '--output',str(a.output),'--worker',json.dumps(c),'--cpu',str(cpus[i%len(cpus)])],
            text=True,capture_output=True,timeout=15,env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1'))
        if proc.returncode:raise RuntimeError(proc.stderr)
        return json.loads(proc.stdout)
    with ThreadPoolExecutor(max_workers=len(cpus)) as pool:rows=list(pool.map(run,enumerate(cases)))
    a.output.write_text(json.dumps(dict(rows=rows,scope='Observed Rover root diagnostics; cached harvesting only; 8s total/.5s per threshold; no baseline reruns.'),separators=(',',':')))


if __name__=='__main__':main()
