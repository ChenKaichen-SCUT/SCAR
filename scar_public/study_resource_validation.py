"""Frozen new-source validation and separately labelled observed Rover scaling."""
import argparse,json,os,platform,subprocess,sys,threading
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from scar_public import fresh_resource_suite as suite, study_information_gaps as old
from scar_public.decision_coverage import DecisionPlanner
from scar_public.incremental_channels import IncrementalPlanner
from scar_public.amortized_refinement import AmortizedPlanner
from scar_public.resource_information import resource_planner

MODES = ['leaf','resource_tree','incremental_refinement','amortized_count','amortized_relation']


def planner(task,mode):
    if mode in ('forecast_shadow','forecast_observe','forecast_gate'):
        from scar_public.predictive_scheduler import PredictivePlanner
        return PredictivePlanner(task,{'forecast_shadow':'shadow','forecast_observe':'observe',
            'forecast_gate':'joint'}[mode])
    if mode in ('focus_root','focus_priority','focus_multistep'):
        from scar_public.focused_scheduler import FocusedPlanner
        return FocusedPlanner(task,{'focus_root':'root_only','focus_priority':'focused',
            'focus_multistep':'focused_multistep'}[mode])
    if mode in ('frontier_fifo','frontier_priority','frontier_multistep'):
        from scar_public.frontier_scheduler import FrontierPlanner
        return FrontierPlanner(task,{'frontier_fifo':'fifo','frontier_priority':'priority',
            'frontier_multistep':'priority_multistep'}[mode])
    if mode in ('final_work','persistent_multistep'):
        from scar_public.persistent_multistep_refinement import FinalWorkPlanner
        return FinalWorkPlanner(task,multistep=mode=='persistent_multistep')
    if mode=='cached_multistep':
        from scar_public.cached_multistep_refinement import CachedMultistepPlanner
        return CachedMultistepPlanner(task)
    if mode in ('batched_work','batched_multistep'):
        from scar_public.cached_multistep_refinement import BatchedWorkPlanner
        return BatchedWorkPlanner(task,multistep=mode=='batched_multistep')
    if mode=='multistep':
        from scar_public.multistep_refinement import MultistepPlanner
        return MultistepPlanner(task)
    if mode in ('work_scheduled','multistep_scheduled'):
        from scar_public.work_scheduled_refinement import WorkScheduledPlanner
        return WorkScheduledPlanner(task, multistep=mode=='multistep_scheduled')
    if mode=='witness_amortized':
        from scar_public.witness_refinement import WitnessPlanner
        return WitnessPlanner(task)
    if mode=='leaf': return DecisionPlanner(task,'leaf')
    if mode=='resource_tree': return resource_planner(task)
    if mode=='incremental_refinement': return IncrementalPlanner(task)
    return AmortizedPlanner(task,mode)


def manifest(cache):
    configs=suite.configurations()
    paths=sorted(Path(__file__).parent.glob('*.py'))
    return dict(cases=configs,modes=MODES,work_limit_seconds=15,memory_mib=2048,repetitions=1,
        sources={p.name:sha256(p.read_bytes()).hexdigest() for p in paths},
        input_provenance={c['id']:suite.source_text(cache,c)[2] for c in configs if c['source']=='fresh'},
        scope='First outcome inspection on 21 previously untested public source tasks, five families, '
            'each original and a declared a16s1 extension; 8 previously observed Rover scale configurations '
            'are development diagnostics. Strong finite goal policy, not deadend recognition as success. '
            'Do not read source plans, result files or dead.pddl. No filtering based on solver outcomes.',
        limits='H60 fresh; H16 Rover diagnostics. 256 initial models, 20000 grounded actions; '
            'reject rather than truncate. Same indexed exact engine, all initialization/selection included. '
            'Optional work <=3s/run, <=.25s/query, <=64 attempts; atomic calls may overrun. '
            'Amortized variants reuse selected atom identities with current values/effects and reselect '
            'only on loss of common values, <=4 attempts. Resource-tree control work<=300000/run.',
        queries='Separate diagnostic: automatic root selection only, thresholds1..16, up to8s total/.5s '
            'per bound query; first C0-pass/C1-reject query gets a fresh resource-aware Kraft control '
            '(4s/300000 work), exact all 2- and 3-world projections (8s per level), and independent '
            'full oracle (8s). Incomplete checks are UNKNOWN, never reported as passes.',api_calls=0)


def main():
    p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--worker');p.add_argument('--mode')
    p.add_argument('--cpu',type=int);p.add_argument('--freeze',action='store_true');a=p.parse_args()
    if a.worker:
        old.load=suite.load;old.BudgetedPlanner=planner
        return old.worker(a)
    a.output.mkdir(parents=True,exist_ok=True);path=a.output/'manifest.json'
    spec=manifest(a.cache)
    if path.exists():
        assert json.loads(path.read_text())==json.loads(json.dumps(spec)), 'Frozen source/config mismatch'
    else:path.write_text(json.dumps(spec,indent=2))
    if a.freeze:
        print(json.dumps(dict(frozen_cases=len(spec['cases']),methods=len(MODES),sha256=sha256(path.read_bytes()).hexdigest())))
        return
    cpus=sorted(os.sched_getaffinity(0))[::2][:8];jobs=[]
    for i,c in enumerate(spec['cases']):
        k=i%len(MODES);jobs.extend((c,m) for m in MODES[k:]+MODES[:k])
    log=a.output/'runs.jsonl';rows=[json.loads(l) for l in log.read_text().splitlines()] if log.exists() else []
    seen={(r['config']['id'],r['mode']) for r in rows};jobs=[j for j in jobs if (j[0]['id'],j[1]) not in seen]
    lock=threading.Lock()
    def lane(i):
        for c,m in jobs[i::len(cpus)]:
            cmd=[sys.executable,'-u','-m','scar_public.study_resource_validation','--cache',str(a.cache),
                '--output',str(a.output),'--worker',json.dumps(c),'--mode',m,'--cpu',str(cpus[i])]
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
            r=dict(config=c,mode=m,cpu=cpus[i],startup_seconds=startup,wall_seconds=perf_counter()-start,
                timed_out=timeout,hard_killed=killed,phases=phases,status='UNKNOWN')
            for x in phases:r.update({k:v for k,v in x.items() if k!='phase'})
            if timeout:r['status']='UNKNOWN_TIMEOUT'
            with lock:
                rows.append(r)
                with log.open('a') as f:f.write(json.dumps(r)+'\n')
            print(json.dumps(dict(id=c['id'],mode=m,status=r['status'],value=r.get('value'),
                seconds=r.get('total_seconds'))),flush=True)
    with ThreadPoolExecutor(max_workers=len(cpus)) as pool:list(pool.map(lane,range(len(cpus))))
    (a.output/'analysis.json').write_text(json.dumps(dict(manifest=spec,rows=rows,
        environment=dict(python=platform.python_version(),platform=platform.platform(),cpus=cpus),api_calls=0),separators=(',',':')))


if __name__=='__main__':main()
