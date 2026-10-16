"""Frozen automatic root queries and independent stronger controls."""
import argparse,json,os,signal,subprocess,sys,threading
from pathlib import Path
from itertools import combinations
from time import perf_counter
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
from scar_public import fresh_resource_suite as suite
from scar_public.certificate_refinement import RefinementCoverage, projection_view, indices
from scar_public.incremental_channels import IncrementalCoverage
from scar_public.decision_coverage import DecisionPlanner
from scar_public.resource_information import ResourceInformation
from scar_public.information_reference import independent_oracle
from scar_public.budgeted_planner import InferenceStop
from scar_public.symbolic_coverage import Unavailable


def finite(x):
    if isinstance(x,float) and x==float('inf'):return 'infinity'
    if isinstance(x,dict):return {k:finite(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):return [finite(v) for v in x]
    return x


def worker(a):
    import resource
    os.sched_setaffinity(0,{a.cpu});resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
    c=json.loads(a.worker);result=dict(config=c,status='UNKNOWN',queries=[]);start=perf_counter()
    def emit():
        result['seconds']=perf_counter()-start
        print(json.dumps(finite(result)),flush=True)
    def term(sig,frame):
        result['status']='UNKNOWN_PROCESS_TIMEOUT';emit();raise SystemExit(124)
    def alarm(sig,frame):raise TimeoutError('control budget')
    signal.signal(signal.SIGTERM,term);signal.signal(signal.SIGALRM,alarm)
    try:
        task,origin=suite.load(a.cache,c);result.update(origin=origin,metadata=task.metadata(),
            static_groups=len(set(task.static_bits)))
        if result['static_groups']==1:
            result['status']='CERTIFIED_IDENTITY_COLLAPSE';emit();return
        selector=RefinementCoverage(task);selector.deadline=perf_counter()+.25
        live=[(n,s) for n,s in task.belief if not task.goal.holds(s)]
        if len(live)<2 or len({selector.project(s) for _,s in live})!=1:
            result['status']='INAPPLICABLE';emit();return
        t=perf_counter()
        try:extra,e=selector.select(live)
        except (InferenceStop,Unavailable):
            result['status']='UNKNOWN_SELECTION';emit();return
        result.update(selection=e,selection_seconds=perf_counter()-t,
            added_atoms=[task.atom_names[i] for i in indices(extra)])
        bound=IncrementalCoverage(projection_view(task,extra));key=bound.project(live[0][1])
        mask=sum(bound.model_bits[n] for n,_ in live);n=mask.bit_count();separation=None
        deadline=perf_counter()+8
        for depth in range(1,17):
            bound.deadline=min(deadline,perf_counter()+.5);t=perf_counter()
            row=dict(depth=depth,candidates=n)
            try:
                count=bound.capacity(key,depth);row['scalar']=count
                if count<n:row['status']='SCALAR_PRUNE'
                else:
                    identity=bound.relational_capacity(key,mask,depth);row['identity']=identity
                    row['status']='SEPARATION' if identity<n else 'BOTH_PASS'
                    if identity<n:separation=depth
            except (InferenceStop,Unavailable):row['status']='UNKNOWN_QUERY'
            row['seconds']=perf_counter()-t;result['queries'].append(row)
            if row['status'] in ('SEPARATION','BOTH_PASS','UNKNOWN_QUERY') or perf_counter()>=deadline:break
        result['bound_stats']=bound.stats
        if separation is None:
            result['status']='NO_SEPARATION_WITHIN_SCAN';emit();return
        depth=separation;result['status']='SEPARATION';result['controls']={}
        control=ResourceInformation(task);control.deadline=perf_counter()+4;t=perf_counter()
        reject,e=control.decide(task.belief,depth)
        result['controls']['resource_kraft']=dict(status='REJECT' if reject else ('PASS' if e['complete'] else 'UNKNOWN'),
            evidence=e,seconds=perf_counter()-t,statistics=control.stats)
        for k in (2,3):
            t=perf_counter();pl=DecisionPlanner(task,'leaf');checked=0;status='PASS';values=[]
            signal.setitimer(signal.ITIMER_REAL,8)
            try:
                for subset in combinations(sorted(task.belief,key=lambda w:w[0]),min(k,len(task.belief))):
                    ans=pl.solve(frozenset(subset),depth);assert ans.exact;checked+=1
                    values.append(ans.upper)
                    if ans.upper==float('inf'):
                        status='REJECT';break
            except TimeoutError:status='UNKNOWN'
            finally:signal.setitimer(signal.ITIMER_REAL,0)
            result['controls'][f'exact_{k}']=dict(status=status,subsets_checked=checked,
                values=values,seconds=perf_counter()-t,statistics=pl.statistics())
        t=perf_counter();oracle=independent_oracle(SimpleNamespace(models=task.models,goal=task.goal,allowed=task.allowed))
        signal.setitimer(signal.ITIMER_REAL,8)
        try:
            value=oracle(task.belief,depth)
            assert value==float('inf'),'UNSOUND CAPACITY REJECTION'
            result['controls']['full_oracle']=dict(status='REJECT',value=value)
        except TimeoutError:result['controls']['full_oracle']=dict(status='UNKNOWN')
        finally:signal.setitimer(signal.ITIMER_REAL,0)
        result['controls']['full_oracle'].update(seconds=perf_counter()-t,cache=str(oracle.cache_info()))
    except (ValueError,MemoryError,RuntimeError,RecursionError) as e:
        result.update(status='UNSUPPORTED_OR_LIMIT',error_type=type(e).__name__,error=str(e))
    emit()


def main():
    p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--worker');p.add_argument('--cpu',type=int)
    a=p.parse_args()
    if a.worker:return worker(a)
    spec=json.loads((a.output/'manifest.json').read_text());configs=spec['cases']
    cpus=sorted(os.sched_getaffinity(0))[::2][:8];rows=[];lock=threading.Lock()
    def lane(i):
        for c in configs[i::len(cpus)]:
            cmd=[sys.executable,'-u','-m','scar_public.query_resource_validation','--cache',str(a.cache),
                '--output',str(a.output),'--worker',json.dumps(c),'--cpu',str(cpus[i])]
            proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
                env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1'))
            timeout=False
            try:out,err=proc.communicate(timeout=45)
            except subprocess.TimeoutExpired:
                timeout=True;proc.terminate()
                try:out,err=proc.communicate(timeout=2)
                except subprocess.TimeoutExpired:proc.kill();out,err=proc.communicate()
            if proc.returncode and not timeout:raise RuntimeError(err)
            r=json.loads(out.splitlines()[-1]) if out.strip() else dict(config=c,status='UNKNOWN_KILLED')
            with lock:
                rows.append(r)
                with (a.output/'query_runs.jsonl').open('a') as f:f.write(json.dumps(r)+'\n')
            print(json.dumps(dict(id=c['id'],status=r['status'],controls={k:v['status'] for k,v in r.get('controls',{}).items()})),flush=True)
    with ThreadPoolExecutor(max_workers=len(cpus)) as pool:list(pool.map(lane,range(len(cpus))))
    (a.output/'queries.json').write_text(json.dumps(dict(rows=rows,scope=spec['queries']),separators=(',',':')))


if __name__=='__main__':main()
