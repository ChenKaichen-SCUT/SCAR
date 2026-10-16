"""Targeted, explicitly exploratory relation-budget sweep on failed Doors/s4."""
import argparse,json,os,platform,subprocess,sys
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from scar_public.benchmark_suite import configurations,source_text


def main():
    p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,required=True)
    p.add_argument('--output',type=Path,default=Path('scar_public/results/2026-10-16-threshold-search/budget_sweep'))
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    c=next(c for c in configurations() if c['id']=='doors_5_s4')
    jobs=[(m,n) for n in (100000,200000,500000) for m in ('threshold_lineage','threshold_matching')]
    names=['study_relation_budget.py','bounded_resource_coverage.py','study_resource_keys.py',
        'demand_coverage.py','threshold_search.py','study_threshold_search.py','relational_coverage.py',
        'invariant_coverage.py','symbolic_coverage.py','symbolic_task.py','coverage_planner.py',
        'information_bound.py','finite_planner.py','benchmark_suite.py']
    spec=dict(version=1,cases=[c],variants=jobs,work_limit_seconds=15,termination_grace_seconds=2,
        memory_limit_mib=2048,repetitions=1,input_provenance=source_text(a.cache,'doors','5')[2],
        sources={n:sha256((Path(__file__).parent/n).read_text().encode()).hexdigest() for n in names},
        rationale='Target selected after 5000/50000-node diagnostic exhausted the relation budget and '
            'returned root 14/29. This is an exploratory cost-sensitivity sweep on ONE failed instance, '
            'not a holdout or new aggregate main method. Both identity and matching variants are included. '
            'Every worker retains a 15-second total work limit; no unlimited runs.')
    manifest=a.output/'manifest.json'
    if manifest.exists():assert json.loads(manifest.read_text())==json.loads(json.dumps(spec))
    else:manifest.write_text(json.dumps(spec,indent=2))
    cpus=sorted(os.sched_getaffinity(0))[::2][:len(jobs)]
    def run(index):
        mode,limit=jobs[index]
        cmd=[sys.executable,'-u','-m','scar_public.study_resource_keys','--cache',str(a.cache),
            '--worker',json.dumps(c),'--mode',mode,'--cpu',str(cpus[index]),'--node-limit',str(limit)]
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
        r=dict(config=c,mode=mode,node_limit=limit,cpu=cpus[index],startup_seconds=startup,
            wall_seconds=perf_counter()-start,timed_out=timeout,hard_killed=killed,phases=phases,status='UNKNOWN')
        for phase in phases:r.update({k:v for k,v in phase.items() if k!='phase'})
        if timeout:r['status']='UNKNOWN_TIMEOUT'
        if any(x['phase']=='error' for x in phases):r['status']='UNKNOWN_LIMIT_OR_ERROR'
        print(json.dumps(dict(mode=mode,node_limit=limit,status=r['status'],root=r.get('root_lower'),
            seconds=r.get('total_seconds'))),flush=True)
        return r
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:rows=list(pool.map(run,range(len(jobs))))
    result=dict(manifest=spec,rows=rows,environment=dict(python=platform.python_version(),
        platform=platform.platform(),cpus=cpus),api_calls=0)
    (a.output/'analysis.json').write_text(json.dumps(result,separators=(',',':')))


if __name__=='__main__':main()
