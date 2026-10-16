"""Post-primary resource-cache diagnostic on all 16 budget overlays."""
import argparse,json,os,platform,subprocess,sys,threading
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from scar_public.benchmark_suite import configurations,source_text
from scar_public.bounded_resource_coverage import BoundedResourcePlanner
import scar_public.study_threshold_search as shared


def main():
    p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,required=True)
    p.add_argument('--worker');p.add_argument('--mode');p.add_argument('--cpu',type=int)
    p.add_argument('--node-limit',type=int,default=5000)
    p.add_argument('--output',type=Path,default=Path('scar_public/results/2026-10-16-threshold-search/resource_keys'))
    a=p.parse_args()
    if a.worker:
        shared.ThresholdPlanner=BoundedResourcePlanner
        return shared.worker(a)
    a.output.mkdir(parents=True,exist_ok=True)
    cases=[c for c in configurations() if c['cohort']=='declared_resource_extension']
    variants=[('threshold_counts',5000),('threshold_matching',5000),('threshold_matching',50000)]
    names=['bounded_resource_coverage.py','study_resource_keys.py','demand_coverage.py','threshold_search.py',
        'study_threshold_search.py','relational_coverage.py','invariant_coverage.py','symbolic_coverage.py',
        'symbolic_task.py','coverage_planner.py','information_bound.py','finite_planner.py','benchmark_suite.py']
    spec=dict(version=1,cases=cases,variants=variants,
        work_limit_seconds=15,termination_grace_seconds=2,memory_limit_mib=2048,repetitions=1,
        sources={n:sha256((Path(__file__).parent/n).read_text().encode()).hexdigest() for n in names},
        input_provenance={c['id']:source_text(a.cache,c['family'],c['instance'])[2] for c in cases},
        rationale='Disclosed diagnostic after demand-construction runs. All 16 resource overlays retained. '
            'Canonicalize each abstract resource to min(r_i,t*max_action_consumption_i). '
            'This preserves finite-horizon feasibility for fixed nonnegative consumption and Boolean goals. '
            'Counts and matching share canonicalization. 50000-node matching is a separately labelled '
            'cost sensitivity run, not substituted into the 5000-node main results. No external/API reruns.')
    manifest=a.output/'manifest.json'
    if manifest.exists():assert json.loads(manifest.read_text())==json.loads(json.dumps(spec))
    else:manifest.write_text(json.dumps(spec,indent=2))
    cpus=sorted(os.sched_getaffinity(0))[::2][:8];jobs=[]
    for i,c in enumerate(cases):
        k=i%len(variants);jobs.extend((c,m,n) for m,n in variants[k:]+variants[:k])
    runfile=a.output/'runs.jsonl';rows=[json.loads(l) for l in runfile.read_text().splitlines()] if runfile.exists() else []
    seen={(r['config']['id'],r['mode'],r['node_limit']) for r in rows}
    jobs=[j for j in jobs if (j[0]['id'],j[1],j[2]) not in seen];lock=threading.Lock()
    def lane(index):
        for config,mode,node_limit in jobs[index::len(cpus)]:
            cmd=[sys.executable,'-u','-m','scar_public.study_resource_keys','--cache',str(a.cache),
                '--worker',json.dumps(config),'--mode',mode,'--cpu',str(cpus[index]),'--node-limit',str(node_limit)]
            env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
            start=perf_counter();proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,text=True,env=env)
            assert json.loads(proc.stdout.readline())['phase']=='ready';startup=perf_counter()-start;timeout=killed=False
            try:out,err=proc.communicate('go\n',timeout=15)
            except subprocess.TimeoutExpired:
                timeout=True;proc.terminate()
                try:out,err=proc.communicate(timeout=2)
                except subprocess.TimeoutExpired:killed=True;proc.kill();out,err=proc.communicate()
            if proc.returncode and not timeout:raise RuntimeError(err)
            phases=[json.loads(l) for l in out.splitlines() if l.strip()]
            r=dict(config=config,mode=mode,node_limit=node_limit,cpu=cpus[index],startup_seconds=startup,
                wall_seconds=perf_counter()-start,timed_out=timeout,hard_killed=killed,phases=phases,status='UNKNOWN')
            for phase in phases:r.update({k:v for k,v in phase.items() if k!='phase'})
            if timeout:r['status']='UNKNOWN_TIMEOUT'
            if any(x['phase']=='error' for x in phases):r['status']='UNKNOWN_LIMIT_OR_ERROR'
            with lock:
                rows.append(r)
                with runfile.open('a') as f:f.write(json.dumps(r)+'\n')
            print(json.dumps(dict(id=config['id'],mode=mode,node_limit=node_limit,status=r['status'],
                root=r.get('root_lower'),value=r.get('value'),seconds=r.get('total_seconds'))),flush=True)
    with ThreadPoolExecutor(max_workers=len(cpus)) as pool:list(pool.map(lane,range(len(cpus))))
    result=dict(manifest=spec,rows=rows,environment=dict(python=platform.python_version(),
        platform=platform.platform(),cpus=cpus),api_calls=0)
    (a.output/'analysis.json').write_text(json.dumps(result,separators=(',',':')))


if __name__=='__main__':main()
