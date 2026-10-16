"""Cross-engine, cold-query, independent-oracle and stronger-control checks."""
import argparse,json,os,signal,subprocess,sys
from itertools import combinations
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
from scar_public.search_public_separations import load
from scar_public.certificate_refinement import projection_view
from scar_public.decision_coverage import DecisionCoverage,DecisionPlanner
from scar_public.incremental_channels import IncrementalCoverage
from scar_public.information_reference import independent_oracle
from scar_public.information_controls import InformationControls
from scar_public.budgeted_planner import InferenceStop
from scar_public.symbolic_coverage import Unavailable


def worker(a):
    import resource
    os.sched_setaffinity(0,{a.cpu});resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
    data=json.loads(a.worker);config=data['config'];q=data['query'];task,origin=load(a.cache,config)
    ids={tuple(n):i for i,n in enumerate(task.atom_names)}
    extra=sum(1<<ids[tuple(n)] for n in q['added_atoms']);view=projection_view(task,extra)
    result=dict(config=config,query=q,origin=origin,engines={})
    for label,cls in [('old',DecisionCoverage),('incremental',IncrementalCoverage)]:
        started=perf_counter();bound=cls(view);bound.deadline=started+5.
        key=bound.project(next(iter(task.belief))[1]);mask=(1<<len(task.models))-1
        try:
            scalar=bound.capacity(key,q['depth']);count_done=perf_counter()
            identity=bound.relational_capacity(key,mask,q['depth'])
            result['engines'][label]=dict(status='complete',scalar=scalar,identity=identity,
                count_seconds=count_done-started,relation_seconds=perf_counter()-count_done,
                fallbacks=bound.relation_stats['fallbacks'])
            assert scalar>=len(task.models)>identity
            assert (scalar,identity)==(q['scalar'],q['identity'])
        except (InferenceStop,Unavailable):result['engines'][label]=dict(status='unknown')
        result['engines'][label]['seconds']=perf_counter()-started
    controls=InformationControls(task,work_limit=150000)
    result['leaf_lower']=controls.leaf_lower(task.belief,q['depth'])
    instance=SimpleNamespace(models=task.models,goal=task.goal,allowed=task.allowed)
    oracle=independent_oracle(instance)
    def alarm(sig,frame):raise TimeoutError('independent oracle budget')
    signal.signal(signal.SIGALRM,alarm)
    signal.setitimer(signal.ITIMER_REAL,8)
    result['oracle']={};started=perf_counter()
    try:
        full=oracle(task.belief,q['depth']);result['oracle']['full']='infinity' if full==float('inf') else full
        assert full==float('inf')
        singles=[oracle(frozenset([w]),q['depth']) for w in task.belief]
        pairs=[oracle(frozenset(ws),q['depth']) for ws in combinations(task.belief,2)]
        result['oracle'].update(single_values=['infinity' if x==float('inf') else x for x in singles],
            pair_values=['infinity' if x==float('inf') else x for x in pairs],
            single_detects=any(x==float('inf') for x in singles),pair_detects=any(x==float('inf') for x in pairs),
            status='complete')
    except TimeoutError:result['oracle']['status']='unknown_timeout'
    finally:signal.setitimer(signal.ITIMER_REAL,0)
    result['oracle'].update(seconds=perf_counter()-started,cache=str(oracle.cache_info()))
    # Held fixed across methods; this is a diagnostic root-selected projection,
    # not a claim that the dynamic selector always chooses it at later beliefs.
    result['search']={}
    for mode in ('count_threshold','relation_threshold'):
        started=perf_counter();planner=DecisionPlanner(task,mode)
        planner.target_coverage=IncrementalCoverage(view)
        signal.setitimer(signal.ITIMER_REAL,5)
        try:
            answer=planner.solve(task.belief,16)
            result['search'][mode]=dict(status=answer.status,value=answer.upper,
                replay=planner.verify(task.belief,16,answer.policy) if answer.upper<float('inf') else None)
        except TimeoutError:result['search'][mode]=dict(status='unknown_timeout')
        finally:signal.setitimer(signal.ITIMER_REAL,0)
        result['search'][mode].update(seconds=perf_counter()-started,statistics=planner.statistics())
    print(json.dumps(result),flush=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,required=True);p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--worker');p.add_argument('--cpu',type=int);a=p.parse_args()
    if a.worker:return worker(a)
    source=json.loads(a.input.read_text());jobs=[]
    wanted={'rovers_pfile2_original','rovers_pfile4_original','rovers_pfile2_a8s0','rovers_pfile4_a16s1',
        'medical_pfile005_a16s1','doors_5_original'}
    for r in source['rows']:
        if r['config']['id'] not in wanted:continue
        q=next(q for q in r['queries'] if q['status']=='SEPARATION')
        jobs.append(dict(config=r['config'],query=q))
    cpus=sorted(os.sched_getaffinity(0))[::2][:8]
    def run(pair):
        i,data=pair
        command=[sys.executable,'-m','scar_public.validate_public_separations','--cache',str(a.cache),
            '--input',str(a.input),'--output',str(a.output),'--worker',json.dumps(data),'--cpu',str(cpus[i%len(cpus)])]
        proc=subprocess.run(command,capture_output=True,text=True,timeout=40,
            env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1'))
        if proc.returncode:raise RuntimeError(proc.stderr)
        return json.loads(proc.stdout)
    with ThreadPoolExecutor(max_workers=6) as pool:rows=list(pool.map(run,enumerate(jobs)))
    a.output.write_text(json.dumps(dict(rows=rows,scope='Post-discovery validation; 5s bound, 8s independent oracle, '
        'two 5s fixed-projection search diagnostics at H=16. Not independent validation or matched 15s full-study timing.'),indent=2))
    print(json.dumps(dict(cases=len(rows),oracle_complete=sum(r['oracle']['status']=='complete' for r in rows))))


if __name__=='__main__':main()
