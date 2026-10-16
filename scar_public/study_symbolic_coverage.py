"""Frozen heterogeneous study; one pinned process/core, bounded CPU and memory."""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from time import perf_counter

from scar_public.benchmark_suite import freeze,load_case
from scar_public.finite_planner import printable
from scar_public.symbolic_coverage import LazyCoveragePlanner


def source_hashes():
    return {name:sha256((Path(__file__).parent/name).read_text(encoding='utf-8').encode()).hexdigest()
            for name in ('symbolic_task.py','symbolic_coverage.py','benchmark_suite.py','published_planners.py',
                         'study_symbolic_coverage.py','coverage_planner.py','finite_planner.py','information_bound.py')}


def worker(args):
    config=json.loads(args.worker)
    if hasattr(os,'sched_setaffinity') and args.cpu is not None:os.sched_setaffinity(0,{args.cpu})
    def emit(phase,**data):print(json.dumps(dict(phase=phase,**data)),flush=True)
    emit('ready');assert sys.stdin.readline().strip()=='go'
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_AS,(2048*1024**2,2048*1024**2))
    except ImportError:resource=None
    started=perf_counter()
    try:
        task,origin=load_case(args.cache,config);parsed=perf_counter()
        emit('parsed',parse_seconds=parsed-started,metadata=task.metadata(),origin=origin)
        planner=LazyCoveragePlanner(task,args.mode);constructed=perf_counter()
        root=planner.initial(task.belief,config['horizon']).lower;bounded=perf_counter()
        emit('root',root_lower=printable(root),construct_seconds=constructed-parsed,
             root_seconds=bounded-constructed,root_statistics=planner.statistics())
        answer=planner.solve(task.belief,config['horizon']);finished=perf_counter()
        assert answer.exact
        if answer.upper<float('inf'):assert planner.verify(task.belief,config['horizon'],answer.policy)==answer.upper
        emit('done',value=printable(answer.upper),status=answer.status,search_seconds=finished-bounded,
            total_seconds=finished-started,statistics=planner.statistics(),transition_calls=task.transition_calls,
            peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss if resource else None)
    except (MemoryError,RuntimeError,ValueError,RecursionError) as error:
        emit('error',error_type=type(error).__name__,message=str(error))


def cell(config,mode,cache,cpu,limit):
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1')
    command=[sys.executable,'-u','-m','scar_public.study_symbolic_coverage','--worker',json.dumps(config),
             '--mode',mode,'--cache',str(cache),'--cpu',str(cpu)]
    start=perf_counter();p=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
    line=p.stdout.readline()
    if not line or json.loads(line).get('phase')!='ready':raise RuntimeError(p.stderr.read())
    startup=perf_counter()-start;timeout=False
    try:out,err=p.communicate(input='go\n',timeout=limit)
    except subprocess.TimeoutExpired:timeout=True;p.kill();out,err=p.communicate()
    phases=[json.loads(line) for line in out.splitlines() if line.strip()]
    if p.returncode and not timeout:raise RuntimeError(err)
    result=dict(config=config,mode=mode,cpu=cpu,startup_seconds=startup,wall_seconds=perf_counter()-start,
                work_limit_seconds=limit,timed_out=timeout,phases=phases,status='UNKNOWN')
    for phase in phases:result.update({k:v for k,v in phase.items() if k!='phase'})
    if timeout:result['status']='UNKNOWN_TIMEOUT'
    if any(p['phase']=='error' for p in phases):result['status']='UNKNOWN_LIMIT_OR_ERROR'
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,default=Path('../planning_sources'))
    p.add_argument('--output',type=Path,default=Path('scar_public/results/2026-10-16-symbolic-coverage'))
    p.add_argument('--worker');p.add_argument('--mode');p.add_argument('--cpu',type=int);p.add_argument('--freeze',action='store_true')
    p.add_argument('--workers',type=int,default=8);p.add_argument('--external',type=Path)
    args=p.parse_args()
    if args.worker:return worker(args)
    args.output.mkdir(parents=True,exist_ok=True)
    spec=freeze(args.cache,args.output/'manifest.json')
    if args.freeze:print('Manifest frozen.');return
    hashes=source_hashes();source_path=args.output/'source_hashes.json'
    if source_path.exists():assert json.loads(source_path.read_text())==hashes
    else:source_path.write_text(json.dumps(hashes,indent=2))
    cpus=sorted(os.sched_getaffinity(0))[::2] if hasattr(os,'sched_getaffinity') else list(range(args.workers))
    cpus=cpus[:args.workers]
    # Each lane has one physical core on the recorded 2-thread/core server.
    jobs=[]
    for i,c in enumerate(spec['cases']):
        modes=spec['modes'];offset=i%len(modes)
        jobs.extend((c,m) for m in modes[offset:]+modes[:offset])
    runfile=args.output/'runs.jsonl'
    rows=[json.loads(line) for line in runfile.read_text().splitlines()] if runfile.exists() else []
    seen={(r['config']['id'],r['mode']) for r in rows}
    jobs=[j for j in jobs if (j[0]['id'],j[1]) not in seen]
    lanes=[jobs[i::len(cpus)] for i in range(len(cpus))]
    def lane(index):
        results=[]
        for c,m in lanes[index]:
            row=cell(c,m,args.cache,cpus[index],spec['work_limit_seconds']);results.append(row)
            print(json.dumps(dict(id=c['id'],mode=m,status=row['status'],root=row.get('root_lower'),seconds=row.get('total_seconds'))),flush=True)
        return results
    with ThreadPoolExecutor(max_workers=len(cpus)) as pool:
        for future in as_completed([pool.submit(lane,i) for i in range(len(cpus))]):
            for row in future.result():
                rows.append(row)
                with runfile.open('a') as f:f.write(json.dumps(row)+'\n')
    external=[]
    if args.external:
        # Separate phase, no simultaneous timing of Python and external planners.
        from scar_public.published_planners import run_cff
        for c in spec['cases']:
            if c['cohort']!='original':continue
            for h in (2,3):
                out=args.output/'external'/f'{c["id"]}_h{h}'
                result_path=out/'result.json'
                if result_path.exists():r=json.loads(result_path.read_text())
                else:
                    r=dict(config=c,**run_cff(args.cache,c,args.external,out,h,spec['external_limit_seconds']))
                    result_path.write_text(json.dumps(r,indent=2))
                external.append(r);print(json.dumps(dict(external=c['id'],h=h,status=r['status'])),flush=True)
    result=dict(manifest=spec,source_sha256=hashes,environment=dict(python=platform.python_version(),platform=platform.platform(),cpus=cpus),
                rows=rows,external=external,api_calls=0,game_actions=0)
    (args.output/'analysis.json').write_text(json.dumps(result,indent=2))


if __name__=='__main__':main()
