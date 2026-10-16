"""Observed failure diagnostics only; automatic selection, no hand-picked atoms."""
import argparse, json, os, signal, subprocess, sys
from pathlib import Path
from time import perf_counter
from concurrent.futures import ThreadPoolExecutor
from scar_public import fresh_resource_suite as suite
from scar_public.multistep_refinement import MultistepCoverage
from scar_public.incremental_channels import IncrementalCoverage
from scar_public.certificate_refinement import projection_view, indices
from scar_public.budgeted_planner import InferenceStop
from scar_public.symbolic_coverage import Unavailable


def worker(a):
    import resource
    os.sched_setaffinity(0, {a.cpu})
    resource.setrlimit(resource.RLIMIT_AS, (2*1024**3,2*1024**3))
    c = json.loads(a.worker); start = perf_counter()
    r = dict(config=c,status='UNKNOWN',queries=[])
    def emit():
        r['seconds'] = perf_counter()-start
        print(json.dumps(r),flush=True)
    def stop(sig,frame):
        r['status']='UNKNOWN_TIMEOUT';emit();raise SystemExit(124)
    signal.signal(signal.SIGTERM,stop)
    try:
        task,origin=suite.load(a.cache,c)
        r.update(metadata=task.metadata(),origin=origin)
        selector=MultistepCoverage(task);selector.query_budget=16
        selector.deadline=perf_counter()+.25
        live=[(n,s) for n,s in task.belief if not task.goal.holds(s)]
        if len(live)<2 or len({selector.project(s) for _,s in live})!=1:
            r['status']='INAPPLICABLE';emit();return
        t=perf_counter();extra,e=selector.select(live)
        r.update(selection=e,selection_seconds=perf_counter()-t,
            trace_stats=selector.multistep_stats,
            added_atoms=[task.atom_names[i] for i in indices(extra)])
        bound=IncrementalCoverage(projection_view(task,extra),pool=selector.channel_pool)
        key=bound.project(live[0][1]);mask=sum(bound.model_bits[n] for n,_ in live)
        deadline=perf_counter()+8
        for depth in range(1,17):
            bound.deadline=min(deadline,perf_counter()+.5);t=perf_counter()
            q=dict(depth=depth,candidates=len(live))
            try:
                q['scalar']=bound.capacity(key,depth)
                if q['scalar']<len(live):q['status']='SCALAR_PRUNE'
                else:
                    q['identity']=bound.relational_capacity(key,mask,depth)
                    q['status']='SEPARATION' if q['identity']<len(live) else 'BOTH_PASS'
            except (InferenceStop,Unavailable):q['status']='UNKNOWN_QUERY'
            q['seconds']=perf_counter()-t;r['queries'].append(q)
            if q['status'] in ('UNKNOWN_QUERY','BOTH_PASS') or perf_counter()>=deadline:break
        r.update(status='SCANNED',bound_stats=bound.stats)
    except (InferenceStop,Unavailable):r['status']='UNKNOWN_SELECTION'
    except (ValueError,MemoryError,RuntimeError,RecursionError) as e:
        r.update(status='UNSUPPORTED_OR_LIMIT',error=str(e))
    emit()


def main():
    p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--worker');p.add_argument('--cpu',type=int)
    a=p.parse_args()
    if a.worker:return worker(a)
    spec=json.loads((a.output/'manifest.json').read_text());cpus=sorted(os.sched_getaffinity(0))[::2][:8]
    def run(job):
        i,c=job
        proc=subprocess.Popen([sys.executable,'-u','-m','scar_public.query_multistep_refinement',
            '--cache',str(a.cache),'--output',str(a.output),'--worker',json.dumps(c),'--cpu',str(cpus[i%len(cpus)])],
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
            env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1'))
        try:out,err=proc.communicate(timeout=15)
        except subprocess.TimeoutExpired:
            proc.terminate()
            try:out,err=proc.communicate(timeout=2)
            except subprocess.TimeoutExpired:proc.kill();out,err=proc.communicate()
        if not out.strip():raise RuntimeError(err)
        r=json.loads(out.splitlines()[-1]);print(json.dumps(dict(id=c['id'],status=r['status'])),flush=True)
        return r
    # Lane assignment avoids sharing a physical core between simultaneous jobs.
    def lane(i):return [run((i,c)) for c in spec['cases'][i::len(cpus)]]
    with ThreadPoolExecutor(max_workers=len(cpus)) as pool:
        rows=[r for lane_rows in pool.map(lane,range(len(cpus))) for r in lane_rows]
    (a.output/'queries.json').write_text(json.dumps(dict(rows=rows,scope='Development diagnostics; .25s selection, .1s multi-step subsection, .5s/depth, 8s scan. No control reruns.'),separators=(',',':')))


if __name__=='__main__':main()
