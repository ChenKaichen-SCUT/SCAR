"""Frozen unseen-public suite plus separately labelled old failure diagnostics."""
import argparse,json,os,platform,signal,subprocess,sys,threading
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from scar_public import holdout_suite
from scar_public.benchmark_suite import configurations as old_cases,load_case as old_load
from scar_public.budgeted_planner import BudgetedPlanner
from scar_public.finite_planner import printable


def cases():
    result=holdout_suite.configurations()
    for c in old_cases():
        if c['id'] in ('rovers_pfile6_sNone','rovers_pfile8_sNone','localize_5_s2','localize_5_s4','doors_5_s4'):
            result.append(dict(c,cohort='old_failure_diagnostic',source='old'))
    return result


def load(cache,c):return old_load(cache,c) if c['source']=='old' else holdout_suite.load_case(cache,c)


def worker(a):
    import resource
    os.sched_setaffinity(0,{a.cpu})
    def emit(phase,**data):print(json.dumps(dict(phase=phase,**data)),flush=True)
    emit('ready');assert sys.stdin.readline().strip()=='go'
    resource.setrlimit(resource.RLIMIT_AS,(2048*1024**2,2048*1024**2))
    start=perf_counter();planner=task=None;phase='parse'
    def partial():return dict(statistics=planner.statistics() if planner else None,
        transition_calls=task.transition_calls if task else None,
        peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    def stop(sig,frame):
        emit('interrupted',active_phase=phase,elapsed_seconds=perf_counter()-start,**partial())
        raise SystemExit(124)
    signal.signal(signal.SIGTERM,stop)
    try:
        c=json.loads(a.worker);task,origin=load(a.cache,c);parsed=perf_counter()
        emit('parsed',parse_seconds=parsed-start,metadata=task.metadata(),origin=origin)
        phase='construct';planner=BudgetedPlanner(task,a.mode);constructed=perf_counter()
        phase='root';r=planner.initial(task.belief,c['horizon']);bounded=perf_counter()
        emit('root',root_lower=printable(r.lower),construct_seconds=constructed-parsed,
            root_seconds=bounded-constructed,root_statistics=planner.statistics())
        phase='search';answer=planner.solve(task.belief,c['horizon']);finished=perf_counter()
        assert answer.exact;depth=None
        if answer.upper<float('inf'):
            phase='replay';depth=planner.verify(task.belief,c['horizon'],answer.policy);assert depth==answer.upper
        emit('done',status=answer.status,value=printable(answer.upper),verified_policy_depth=depth,
            search_seconds=finished-bounded,total_seconds=finished-start,**partial())
    except (MemoryError,RuntimeError,ValueError,RecursionError,TypeError) as e:
        emit('error',status='UNSUPPORTED_INPUT' if phase=='parse' else 'UNKNOWN_LIMIT_OR_ERROR',
            error_type=type(e).__name__,message=str(e),active_phase=phase,**partial())


def main():
    p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,required=True)
    p.add_argument('--worker');p.add_argument('--mode');p.add_argument('--cpu',type=int)
    p.add_argument('--freeze',action='store_true');p.add_argument('--output',type=Path,
        default=Path('scar_public/results/2026-10-17-information-gaps'))
    a=p.parse_args()
    if a.worker:return worker(a)
    a.output.mkdir(parents=True,exist_ok=True);configs=cases();modes=list(BudgetedPlanner.MODES)
    names=['information_controls.py','budgeted_planner.py','holdout_suite.py','study_information_gaps.py',
        'threshold_search.py','bounded_resource_coverage.py','demand_coverage.py','relational_coverage.py',
        'invariant_coverage.py','symbolic_coverage.py','symbolic_task.py','coverage_planner.py',
        'information_bound.py','finite_planner.py','benchmark_suite.py']
    provenance={c['id']:holdout_suite.source_text(a.cache,c)[2] for c in configs if c['source']!='old'}
    spec=dict(version=1,cases=configs,modes=modes,work_limit_seconds=15,termination_grace_seconds=2,
        memory_limit_mib=2048,repetitions=1,model_limit=256,ground_action_limit=20000,
        sources={n:sha256((Path(__file__).parent/n).read_text().encode()).hexdigest() for n in names},
        input_provenance=provenance,
        controls='All methods use identical threshold search, signed-literal hmax, BFS <=64 nodes/query and '
            '<=4096 nodes/run. leaf is certified resource-blind pair incompatibility plus a valid clique and '
            'binary leaf count. pair is completed exact 1/2-world policy projections; interrupted queries '
            'are omitted. Information control allows 150000 work charges/run. Counts/lineage retain same '
            'projection and resource keys; relation cap 100000. Unconditional capacity budget 3 seconds/run, '
            '<=1 second/query. Scheduled capacity uses min(3s,0.25s+0.25*noncapacity elapsed) credit, '
            '<=0.25s/query; skips singleton queries. Checkpoint deadlines can overrun by one atomic SAT query.',
        scope='26 new public originals, 8 explicit resource overlays, 5 separately labelled old failures. '
            'No new-instance planner outcomes inspected before freezing implementation and this manifest. '
            'All unsupported syntax/enumeration/grounding cases remain in the denominator and are reported '
            'separately. 60-step bound is declared, not a claim of unrestricted infeasibility. No LLM calls.')
    manifest=a.output/'manifest.json'
    if manifest.exists():assert json.loads(manifest.read_text())==json.loads(json.dumps(spec))
    else:manifest.write_text(json.dumps(spec,indent=2))
    if a.freeze:print('Frozen',len(configs),'cases',len(modes),'methods');return
    cpus=sorted(os.sched_getaffinity(0))[::2][:8];jobs=[]
    for i,c in enumerate(configs):
        k=i%len(modes);jobs.extend((c,m) for m in modes[k:]+modes[:k])
    path=a.output/'runs.jsonl';rows=[json.loads(l) for l in path.read_text().splitlines()] if path.exists() else []
    seen={(r['config']['id'],r['mode']) for r in rows};jobs=[j for j in jobs if (j[0]['id'],j[1]) not in seen]
    lock=threading.Lock()
    def lane(index):
        for c,m in jobs[index::len(cpus)]:
            cmd=[sys.executable,'-u','-m','scar_public.study_information_gaps','--cache',str(a.cache),
                '--worker',json.dumps(c),'--mode',m,'--cpu',str(cpus[index])]
            env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
            start=perf_counter();proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,text=True,env=env)
            line=proc.stdout.readline()
            if not line:raise RuntimeError(proc.stderr.read())
            assert json.loads(line)['phase']=='ready';startup=perf_counter()-start;timeout=killed=False
            try:out,err=proc.communicate('go\n',timeout=15)
            except subprocess.TimeoutExpired:
                timeout=True;proc.terminate()
                try:out,err=proc.communicate(timeout=2)
                except subprocess.TimeoutExpired:killed=True;proc.kill();out,err=proc.communicate()
            if proc.returncode and not timeout:raise RuntimeError(err)
            phases=[json.loads(l) for l in out.splitlines() if l.strip()]
            r=dict(config=c,mode=m,cpu=cpus[index],startup_seconds=startup,wall_seconds=perf_counter()-start,
                timed_out=timeout,hard_killed=killed,phases=phases,status='UNKNOWN')
            for x in phases:r.update({k:v for k,v in x.items() if k!='phase'})
            if timeout:r['status']='UNKNOWN_TIMEOUT'
            with lock:
                rows.append(r)
                with path.open('a') as f:f.write(json.dumps(r)+'\n')
            print(json.dumps(dict(id=c['id'],mode=m,status=r['status'],root=r.get('root_lower'),
                value=r.get('value'),seconds=r.get('total_seconds'))),flush=True)
    with ThreadPoolExecutor(max_workers=len(cpus)) as pool:list(pool.map(lane,range(len(cpus))))
    (a.output/'analysis.json').write_text(json.dumps(dict(manifest=spec,rows=rows,
        environment=dict(python=platform.python_version(),platform=platform.platform(),cpus=cpus),api_calls=0),
        separators=(',',':')))


if __name__=='__main__':main()
