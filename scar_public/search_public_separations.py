"""Bounded discovery sweep, not a held-out evaluation or modified source task.

Original source queries and explicitly declared budget overlays are separated.
Every comparison uses one identical projection and one identical channel engine.
"""
import argparse,json,os,signal,subprocess,sys,threading
from pathlib import Path
from time import perf_counter
from hashlib import sha256
from concurrent.futures import ThreadPoolExecutor
from scar_public import benchmark_suite,holdout_suite
from scar_public.compiled_task import CompiledTask
from scar_public.contingent_benchmarks import sexpr
from scar_public.symbolic_task import atoms
from scar_public.certificate_refinement import RefinementCoverage,projection_view,indices
from scar_public.incremental_channels import IncrementalCoverage,ChannelPool
from scar_public.direct_saturation import SaturationCoverage
from scar_public.budgeted_planner import InferenceStop
from scar_public.symbolic_coverage import Unavailable


def configurations():
    sources=[]
    for family,instances in [('medical',('pfile004','pfile005')),('rovers',('pfile2','pfile4','pfile6','pfile8')),
            ('erovers',('pfile2','pfile4','pfile6','pfile8')),('elogistics',('pfile1','pfile3')),('doors',('5',))]:
        base=family[1:] if family.startswith('e') else family
        for instance in instances:
            sources.append(dict(id=family+'_'+instance,family=family,instance=instance,
                projection_predicates=benchmark_suite.PROJECTIONS[base] if base in benchmark_suite.PROJECTIONS else holdout_suite.PROJECTIONS[base],
                source_kind='benchmark',domain=family+'/domain.pddl',problem=family+'/'+instance))
    for c in holdout_suite.configurations():
        if c['id'] in ('new_cff_grid_2','new_cff_grid_3','new_cff_medpks_10','new_cpor_wumpus_wumpus05'):
            sources.append(dict(c,source_kind='holdout'))
    return [dict(c,id=c['id']+'_'+label,overlay=label,actuation=act,sensors=sensor)
        for c in sources for label,act,sensor in [('original',None,None),('a8s0',8,0),('a16s1',16,1)]]


def load(cache,c):
    if c['source_kind']=='holdout':d,p,origin=holdout_suite.source_text(cache,c)
    else:d,p,origin=benchmark_suite.source_text(cache,c['family'],c['instance'])
    holdout_suite.reject_unsupported(d,p)
    resources=();costs={}
    if c['overlay']!='original':
        resources=(c['actuation'],c['sensors'])
        for schema in sexpr(d):
            if isinstance(schema,list) and schema and schema[0]==':action':
                fields=dict(zip(schema[2::2],schema[3::2]));costs[schema[1]]=(0,1) if ':observe' in fields else (1,0)
    task=CompiledTask(d,p,resources=resources,resource_costs=costs,
        projection_predicates=c['projection_predicates'],model_limit=256,ground_limit=20000)
    return task,origin


def worker(a):
    import resource
    os.sched_setaffinity(0,{a.cpu});resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
    c=json.loads(a.worker);rows=[];started=perf_counter();result=dict(config=c,queries=rows)
    def emit():
        result['seconds']=perf_counter()-started
        print(json.dumps(result),flush=True)
    def stop(sig,frame):
        result['status']='UNKNOWN_PROCESS_TIMEOUT';emit();raise SystemExit(124)
    signal.signal(signal.SIGTERM,stop)
    try:
        task,origin=load(a.cache,c);result.update(origin=origin,metadata=task.metadata(),
            static_model_groups=len(set(task.static_bits)))
        if len(set(task.static_bits))==1:
            result['status']='CERTIFIED_NO_IDENTITY_SEPARATION';emit();return
        selector=RefinementCoverage(task);selector.deadline=perf_counter()+.25
        live=[(n,s) for n,s in task.belief if not task.goal.holds(s)]
        if len({selector.project(s) for _,s in live})!=1:
            result['status']='INAPPLICABLE_INITIAL_PROJECTION';emit();return
        try:automatic,evidence=selector.select(live)
        except (InferenceStop,Unavailable):automatic=0;evidence=dict(reason='selection_unknown')
        result['selection']=evidence
        first,known=selector.known(live)
        observed=set().union(*(atoms(x.observation) for x in task.actions.values() if x.observation is not None))
        goal=atoms(task.goal_expr)
        upstream=set()
        for action in task.actions.values():
            if any(abs(lit)-1 in goal for _,lit in action.effects):
                upstream|=atoms(action.pre)
                for guard,lit in action.effects:
                    if abs(lit)-1 in goal:upstream|=atoms(guard)
        candidates=sorted(indices(known),key=lambda i:(i not in observed,i not in upstream,i not in goal,i))[:4]
        specs=[('automatic',automatic),('base',0)]+[('known_single',1<<i) for i in candidates]
        specs += [('known_prefix3',sum(1<<i for i in candidates[:3]))]
        seen=set();pool=ChannelPool(task);deadline=perf_counter()+8.
        for label,extra in specs:
            if extra in seen:continue
            seen.add(extra)
            if perf_counter()>=deadline:break
            view=projection_view(task,extra);bound=IncrementalCoverage(view,pool=pool)
            key=bound.project(live[0][1]);mask=sum(bound.model_bits[n] for n,_ in live);n=mask.bit_count()
            cert=SaturationCoverage(view);cert.deadline=min(deadline,perf_counter()+.1)
            try:saturated=cert.direct_saturation(task.belief,1)
            except (InferenceStop,Unavailable):saturated=False
            added=[task.atom_names[i] for i in indices(extra)]
            if saturated:
                rows.append(dict(projection=label,added_atoms=added,status='SATURATION_CERTIFICATE',
                    scalar_at_least=n,identity=n,applies_to_depths='1..16'));continue
            for depth in range(1,17):
                if perf_counter()>=deadline:break
                bound.deadline=min(deadline,perf_counter()+.5);start=perf_counter()
                row=dict(projection=label,added_atoms=added,depth=depth,candidates=n)
                try:
                    count=bound.capacity(key,depth);row['scalar']=count
                    if count<n:row['status']='SCALAR_PRUNE'
                    else:
                        value=bound.relational_capacity(key,mask,depth);row['identity']=value
                        row['status']='SEPARATION' if value<n else 'BOTH_PASS'
                except (InferenceStop,Unavailable):row['status']='UNKNOWN_QUERY_LIMIT'
                row['seconds']=perf_counter()-start;rows.append(row)
                if row['status'] in ('SEPARATION','BOTH_PASS','UNKNOWN_QUERY_LIMIT'):break
        result.update(status='COMPLETE_DISCOVERY',pool=pool.stats)
    except (ValueError,MemoryError,RuntimeError,RecursionError) as e:
        result.update(status='UNSUPPORTED_OR_LIMIT',error=str(e),error_type=type(e).__name__)
    emit()


def main():
    p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,required=True);p.add_argument('--worker')
    p.add_argument('--cpu',type=int);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.worker:return worker(a)
    configs=configurations();a.output.mkdir(parents=True,exist_ok=True)
    manifest=dict(configs=configs,thresholds='1..16; stop after first both-pass, separation or unknown per projection',
        case_seconds=8,query_seconds=.5,process_seconds=12,projection_limit=7,api_calls=0,
        source_sha256=sha256(Path(__file__).read_text().encode()).hexdigest(),
        scope='Exploratory root-query discovery. Existing sources plus previously untested erovers/elogistics variants. '
        'Original and explicit actuation/sensor overlays kept separate. Source formulas unchanged. '
        'Known-single/prefix projections are diagnostic, not selected by the deployed certificate selector.')
    (a.output/'manifest.json').write_text(json.dumps(manifest,indent=2))
    cpus=sorted(os.sched_getaffinity(0))[::2][:8];lock=threading.Lock();rows=[]
    def lane(i):
        for c in configs[i::len(cpus)]:
            command=[sys.executable,'-m','scar_public.search_public_separations','--cache',str(a.cache),
                '--output',str(a.output),'--worker',json.dumps(c),'--cpu',str(cpus[i])]
            proc=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
                env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1'))
            try:out,err=proc.communicate(timeout=12)
            except subprocess.TimeoutExpired:
                proc.terminate()
                try:out,err=proc.communicate(timeout=2)
                except subprocess.TimeoutExpired:proc.kill();out,err=proc.communicate()
            if not out.strip():raise RuntimeError(err)
            r=json.loads(out.splitlines()[-1])
            with lock:
                rows.append(r)
                with (a.output/'runs.jsonl').open('a') as f:f.write(json.dumps(r)+'\n')
            print(json.dumps(dict(id=c['id'],status=r['status'],
                separations=sum(q['status']=='SEPARATION' for q in r['queries']))),flush=True)
    with ThreadPoolExecutor(max_workers=len(cpus)) as pool:list(pool.map(lane,range(len(cpus))))
    (a.output/'analysis.json').write_text(json.dumps(dict(manifest=manifest,rows=rows),separators=(',',':')))


if __name__=='__main__':main()
