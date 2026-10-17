"""Frozen public scaling validation, including failed/unsupported cases."""
import argparse,json,os,platform,subprocess,sys,threading
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from scar_public import label_scale_suite as suite,study_information_gaps as worker_api
from scar_public.decision_coverage import DecisionPlanner
from scar_public.amortized_refinement import AmortizedPlanner
from scar_public.label_pair_control import PairControlPlanner
from scar_public.resource_information import resource_planner

MODES=('leaf','resource_pair','resource_tree','amortized_count','amortized_relation')

def planner(task,mode):
    if mode=='leaf':return DecisionPlanner(task,'leaf')
    if mode=='resource_pair':return PairControlPlanner(task)
    if mode=='resource_tree':return resource_planner(task)
    return AmortizedPlanner(task,mode)

def main():
    p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--worker')
    p.add_argument('--mode');p.add_argument('--cpu',type=int);p.add_argument('--freeze',action='store_true')
    a=p.parse_args()
    if a.worker:
        worker_api.load=suite.load;worker_api.BudgetedPlanner=planner
        return worker_api.worker(a)
    a.output.mkdir(parents=True,exist_ok=True)
    spec=dict(cases=suite.configurations(),modes=MODES,seconds=30,memory_mib=2048,
        repetitions=1,horizon=60,model_limit=2048,ground_limit=20000,api_calls=0,
        sources={x.name:sha256(x.read_bytes()).hexdigest() for x in sorted(Path(__file__).parent.glob('*.py'))},
        provenance={c['id']:suite.source_text(a.cache,c)[2] for c in suite.configurations()},
        protocol='Frozen before outcomes. Five public families, original and declared a16s1 overlay. '
        'Same exact indexed threshold engine and shared leaf baseline. C0/C1 use identical projection '
        'selection. Timed-out/unsupported cases retained; no NO from incomplete inference. '
        'Exact pair optional budget 3s/run, .25s/query, 300000 work. Existing C0/C1 limits unchanged. '
        'Timing includes parsing, model enumeration, initialization and all optional inference; '
        'process startup separately reported. Public-family instances related to earlier domains '
        'are not claimed to be statistically independent draws. No cross-world LUG pruning on sensing tasks.')
    mp=a.output/'manifest.json';spec=json.loads(json.dumps(spec))
    if mp.exists():assert json.loads(mp.read_text())==spec,'Frozen source/config mismatch'
    else:mp.write_text(json.dumps(spec,indent=2))
    if a.freeze:print(json.dumps(dict(cases=len(spec['cases']),modes=len(MODES),sha256=sha256(mp.read_bytes()).hexdigest())));return
    # Read physical core identities rather than assuming adjacent SMT siblings.
    cpus=[];cores=set()
    for cpu in sorted(os.sched_getaffinity(0)):
        t=Path(f'/sys/devices/system/cpu/cpu{cpu}/topology')
        core=((t/'physical_package_id').read_text(),(t/'core_id').read_text())
        if core not in cores:cores.add(core);cpus.append(cpu)
    cpus=cpus[:8];log=a.output/'runs.jsonl'
    rows=[json.loads(x) for x in log.read_text().splitlines()] if log.exists() else []
    seen={(x['config']['id'],x['mode']) for x in rows};jobs=[]
    for i,c in enumerate(spec['cases']):
        k=i%len(MODES)
        jobs.extend((c,m) for m in MODES[k:]+MODES[:k] if (c['id'],m) not in seen)
    lock=threading.Lock()
    def lane(i):
        for c,m in jobs[i::len(cpus)]:
            cmd=[sys.executable,'-u','-m','scar_public.study_label_scale','--cache',str(a.cache),
                '--output',str(a.output),'--worker',json.dumps(c),'--mode',m,'--cpu',str(cpus[i])]
            start=perf_counter();proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,text=True,env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1'))
            ready=proc.stdout.readline();startup=perf_counter()-start
            if not ready:raise RuntimeError(proc.stderr.read())
            assert json.loads(ready)['phase']=='ready';timeout=killed=False
            try:out,err=proc.communicate('go\n',timeout=spec['seconds'])
            except subprocess.TimeoutExpired:
                timeout=True;proc.terminate()
                try:out,err=proc.communicate(timeout=2)
                except subprocess.TimeoutExpired:killed=True;proc.kill();out,err=proc.communicate()
            phases=[json.loads(x) for x in out.splitlines() if x.strip()]
            row=dict(config=c,mode=m,cpu=cpus[i],startup_seconds=startup,
                wall_seconds=perf_counter()-start,timed_out=timeout,hard_killed=killed,
                phases=phases,status='UNKNOWN_PROCESS_ERROR')
            for x in phases:row.update({k:v for k,v in x.items() if k!='phase'})
            if timeout:row['status']='UNKNOWN_TIMEOUT'
            if proc.returncode and not timeout:row.update(status='UNKNOWN_PROCESS_ERROR',error=err[-3000:])
            with lock:
                rows.append(row)
                with log.open('a') as f:f.write(json.dumps(row)+'\n')
            print(json.dumps(dict(id=c['id'],mode=m,status=row['status'],seconds=row.get('total_seconds'))),flush=True)
    with ThreadPoolExecutor(max_workers=len(cpus)) as pool:list(pool.map(lane,range(len(cpus))))
    (a.output/'environment.json').write_text(json.dumps(dict(python=platform.python_version(),
        platform=platform.platform(),cpus=cpus,api_calls=0),indent=2))

if __name__=='__main__':main()
