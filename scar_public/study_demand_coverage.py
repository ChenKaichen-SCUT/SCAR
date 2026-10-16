"""Disclosed follow-up: identical channels, demand-driven formula construction."""
import argparse,json,os,platform,subprocess,sys,threading
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from scar_public.benchmark_suite import configurations,source_text
from scar_public.demand_coverage import DemandPlanner
import scar_public.study_threshold_search as shared


def main():
    p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,required=True)
    p.add_argument('--worker');p.add_argument('--mode');p.add_argument('--cpu',type=int)
    p.add_argument('--node-limit',type=int,default=5000);p.add_argument('--freeze',action='store_true')
    p.add_argument('--output',type=Path,default=Path('scar_public/results/2026-10-16-threshold-search/demand'))
    a=p.parse_args()
    if a.worker:
        shared.ThresholdPlanner=DemandPlanner
        return shared.worker(a)
    a.output.mkdir(parents=True,exist_ok=True);cases=configurations()
    names=['demand_coverage.py','study_demand_coverage.py','threshold_search.py','study_threshold_search.py',
        'relational_coverage.py','invariant_coverage.py','symbolic_coverage.py','symbolic_task.py',
        'coverage_planner.py','information_bound.py','finite_planner.py','benchmark_suite.py']
    modes=['threshold_counts','threshold_lineage','threshold_matching']
    spec=dict(version=1,cases=cases,modes=modes,node_limit=a.node_limit,
        work_limit_seconds=15,termination_grace_seconds=2,memory_limit_mib=2048,repetitions=1,
        sources={n:sha256((Path(__file__).parent/n).read_text().encode()).hexdigest() for n in names},
        input_provenance={c['id']:source_text(a.cache,c['family'],c['instance'])[2] for c in cases},
        rationale='Post-primary diagnostic, frozen before follow-up runs. The same exact search, projections, '
            'recurrences and 5000-node relational budget; only constant propagation and successor formula '
            'construction are evaluated on demand. All 34 configurations retained. Unchanged single-world '
            'control is reused from the primary study. No external/game reruns or API calls.')
    manifest=a.output/'manifest.json'
    if manifest.exists():assert json.loads(manifest.read_text())==json.loads(json.dumps(spec))
    else:manifest.write_text(json.dumps(spec,indent=2))
    if a.freeze:print('Frozen',len(cases),'cases',len(modes),'modes');return
    cpus=sorted(os.sched_getaffinity(0))[::2][:8];jobs=[]
    for i,c in enumerate(cases):
        k=i%len(modes);jobs.extend((c,m) for m in modes[k:]+modes[:k])
    runfile=a.output/'runs.jsonl';rows=[json.loads(l) for l in runfile.read_text().splitlines()] if runfile.exists() else []
    seen={(r['config']['id'],r['mode']) for r in rows};jobs=[j for j in jobs if (j[0]['id'],j[1]) not in seen]
    lock=threading.Lock()
    def lane(index):
        for config,mode in jobs[index::len(cpus)]:
            cmd=[sys.executable,'-u','-m','scar_public.study_demand_coverage','--cache',str(a.cache),
                '--worker',json.dumps(config),'--mode',mode,'--cpu',str(cpus[index]),'--node-limit',str(a.node_limit)]
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
            r=dict(config=config,mode=mode,cpu=cpus[index],startup_seconds=startup,wall_seconds=perf_counter()-start,
                timed_out=timeout,hard_killed=killed,phases=phases,status='UNKNOWN')
            for phase in phases:r.update({k:v for k,v in phase.items() if k!='phase'})
            if timeout:r['status']='UNKNOWN_TIMEOUT'
            if any(x['phase']=='error' for x in phases):r['status']='UNKNOWN_LIMIT_OR_ERROR'
            with lock:
                rows.append(r)
                with runfile.open('a') as f:f.write(json.dumps(r)+'\n')
            print(json.dumps(dict(id=config['id'],mode=mode,status=r['status'],root=r.get('root_lower'),
                value=r.get('value'),seconds=r.get('total_seconds'))),flush=True)
    with ThreadPoolExecutor(max_workers=len(cpus)) as pool:list(pool.map(lane,range(len(cpus))))
    result=dict(manifest=spec,rows=rows,environment=dict(python=platform.python_version(),
        platform=platform.platform(),cpus=cpus),api_calls=0)
    (a.output/'analysis.json').write_text(json.dumps(result,separators=(',',':')))


if __name__=='__main__':main()
