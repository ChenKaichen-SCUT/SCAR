"""Matched search-engine/heuristic study on the unchanged 34 configurations."""
import argparse,json,os,platform,signal,subprocess,sys,threading
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from scar_public.benchmark_suite import configurations,load_case,source_text
from scar_public.finite_planner import printable
from scar_public.relational_coverage import RelationalPlanner
from scar_public.threshold_search import ThresholdPlanner


MODES = ['legacy_counts','legacy_matching','threshold_single','threshold_counts',
         'threshold_lineage','threshold_matching']


def worker(args):
    import resource
    os.sched_setaffinity(0,{args.cpu})
    def emit(phase,**data):print(json.dumps(dict(phase=phase,**data)),flush=True)
    emit('ready');assert sys.stdin.readline().strip()=='go'
    resource.setrlimit(resource.RLIMIT_AS,(2048*1024**2,2048*1024**2))
    started=perf_counter();planner=task=None
    def partial():
        return dict(statistics=planner.statistics() if planner else None,
            transition_calls=task.transition_calls if task else None,
            peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    def terminate(signum,frame):
        emit('interrupted',elapsed_seconds=perf_counter()-started,**partial());raise SystemExit(124)
    signal.signal(signal.SIGTERM,terminate)
    try:
        config=json.loads(args.worker);task,origin=load_case(args.cache,config);parsed=perf_counter()
        emit('parsed',parse_seconds=parsed-started,metadata=task.metadata())
        engine,mode=args.mode.split('_',1)
        planner=(RelationalPlanner if engine=='legacy' else ThresholdPlanner)(task,mode,args.node_limit)
        constructed=perf_counter()
        root=planner.initial(task.belief,config['horizon']).lower;bounded=perf_counter()
        emit('root',root_lower=printable(root),construct_seconds=constructed-parsed,
             root_seconds=bounded-constructed,root_statistics=planner.statistics())
        answer=planner.solve(task.belief,config['horizon']);finished=perf_counter();assert answer.exact
        replay=None
        if answer.upper<float('inf'):
            replay=planner.verify(task.belief,config['horizon'],answer.policy)
            assert replay==answer.upper
        emit('done',status=answer.status,value=printable(answer.upper),verified_policy_depth=replay,
            search_seconds=finished-bounded,total_seconds=finished-started,**partial())
    except (MemoryError,RuntimeError,ValueError,RecursionError) as error:
        emit('error',error_type=type(error).__name__,message=str(error),**partial())


def main():
    p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,required=True)
    p.add_argument('--worker');p.add_argument('--mode');p.add_argument('--cpu',type=int)
    p.add_argument('--node-limit',type=int,default=5000);p.add_argument('--freeze',action='store_true')
    p.add_argument('--output',type=Path,default=Path('scar_public/results/2026-10-16-threshold-search'))
    a=p.parse_args()
    if a.worker:return worker(a)
    a.output.mkdir(parents=True,exist_ok=True);cases=configurations()
    names=['threshold_search.py','study_threshold_search.py','relational_coverage.py','invariant_coverage.py',
        'symbolic_coverage.py','symbolic_task.py','coverage_planner.py','information_bound.py',
        'finite_planner.py','benchmark_suite.py']
    spec=dict(version=1,cases=cases,modes=MODES,node_limit=a.node_limit,
        work_limit_seconds=15,termination_grace_seconds=2,memory_limit_mib=2048,repetitions=1,
        sources={n:sha256((Path(__file__).parent/n).read_text().encode()).hexdigest() for n in names},
        input_provenance={c['id']:source_text(a.cache,c['family'],c['instance'])[2] for c in cases},
        rationale='Unchanged 34 cases and projections. All modes share the True-invariant substitution shortcut. '
            'The two legacy-engine controls isolate this shared construction optimization from search changes. '
            'Four threshold modes share exact transition/edge caching, cross-horizon decision intervals, '
            'shortest singleton suffix policies and lazy child evaluation. These are infrastructure, not novelty claims. '
            'No reruns of external/game baselines, no random seeds or LLM calls. Doors was a development diagnostic; '
            'the unchanged suite is a paired regression study, not an independent holdout.')
    manifest=a.output/'manifest.json'
    if manifest.exists():assert json.loads(manifest.read_text())==json.loads(json.dumps(spec))
    else:manifest.write_text(json.dumps(spec,indent=2))
    if a.freeze:print('Frozen',len(cases),'cases',len(MODES),'modes');return
    cpus=sorted(os.sched_getaffinity(0))[::2][:8];jobs=[]
    for i,c in enumerate(cases):
        k=i%len(MODES);jobs.extend((c,m) for m in MODES[k:]+MODES[:k])
    runfile=a.output/'runs.jsonl';rows=[json.loads(l) for l in runfile.read_text().splitlines()] if runfile.exists() else []
    seen={(r['config']['id'],r['mode']) for r in rows};jobs=[j for j in jobs if (j[0]['id'],j[1]) not in seen]
    lock=threading.Lock()
    def lane(index):
        for config,mode in jobs[index::len(cpus)]:
            cmd=[sys.executable,'-u','-m','scar_public.study_threshold_search','--cache',str(a.cache),
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
