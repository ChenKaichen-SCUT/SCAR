"""Dependency-keyed channel reuse: frozen development performance check.

Reuses the already-observed 39 configurations. No independent holdout claim.
No published external planner or LLM baseline is rerun.
"""
import argparse,json,os,platform,subprocess,sys,threading
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
from scar_public import study_information_gaps as old,holdout_suite,benchmark_suite
from scar_public.compiled_task import CompiledTask
from scar_public.incremental_channels import IncrementalPlanner as DecisionPlanner

class MeasuredTask(CompiledTask):
    def metadata(self):
        return dict(super().metadata(), static_model_groups=len(set(self.static_bits)))


def install():
    holdout_suite.SymbolicTask=benchmark_suite.SymbolicTask=MeasuredTask
    old.BudgetedPlanner=DecisionPlanner


def main():
    p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,required=True)
    p.add_argument('--worker');p.add_argument('--mode');p.add_argument('--cpu',type=int)
    p.add_argument('--output',type=Path,default=Path('scar_public/results/2026-10-16-incremental-channels'))
    a=p.parse_args()
    if a.worker:install();return old.worker(a)
    configs=old.cases();modes=['incremental_refinement'];a.output.mkdir(parents=True,exist_ok=True)
    names=['static_grounding.py','compiled_task.py','indexed_planner.py','decision_coverage.py',
        'study_decision_coverage.py','study_direct_saturation.py','direct_saturation.py','certificate_refinement.py','test_certificate_refinement.py','study_certificate_refinement.py','incremental_channels.py','test_incremental_channels.py','study_incremental_channels.py','test_direct_saturation.py','test_decision_coverage.py','study_information_gaps.py',
        'budgeted_planner.py','threshold_search.py','symbolic_task.py','relational_coverage.py',
        'bounded_resource_coverage.py','demand_coverage.py']
    spec=dict(cases=configs,modes=modes,work_limit_seconds=15,memory_mib=2048,repetitions=1,
        sources={n:sha256((Path(__file__).parent/n).read_text().encode()).hexdigest() for n in names},
        scope='Follow-up AFTER inspecting certificate-refinement results. New channel engine preserves the exact C0/C1 semantics with dependency-keyed shared cores and pass-through unwritten outputs; omit only actions with zero contribution. Refine only currently known dynamic atoms using minimum hitting sets of collected one-step saturation witnesses; at most 3 added atoms, 32 witness rounds, 4096 hitting-set nodes, 16 cached projections. Goal-first control uses the same selected cardinality and selection work, replacing the chosen atoms by known goal atoms then other known atoms in index order. Development ablation on the previous 39 already-observed configurations, not independent validation. '
            'All methods share static-join grounding and indexed exact search. Only optional threshold inference differs. '
            'No external baselines or LLM experiments rerun.',
        budget='Each optional variant: <=3 nominal seconds/run, <=0.25s/query, >=0.025s remaining to start, '
            '<=64 attempts/run. Atomic SAT query can overrun. Singleton BFS: <=64 states/query, '
            '<=4096 states/run, <=4096 transitions/query, <=65536 transitions/run, nominal <=0.05s/query '
            'and <=1s/run excluding hmax. Global hmax budget 2000000 effect checks (last check can exceed by one).',
        gate='Selection alone never prunes. All selected predicates are propagated through the same optimistic transition construction, with separate caches. Completed scalar or identity capacity below the live model count is required. First seek a concrete existential one-step goal witness for every surviving static-model group under one common action, with retained variables fixed. Success certifies abstract saturation only. Query only current decision threshold d. If scalar C0<N, prune. Otherwise evaluate its chosen '
            'abstract witness under candidate identities. If witness>=N, skip with a certificate that the lineage '
            'recurrence cannot prune. Else evaluate lineage only if resource pressure>0 or C0(d-1)<N. '
            'The latter pressure filter schedules work and has no infeasibility force.')
    manifest=a.output/'manifest.json'
    if manifest.exists():assert json.loads(manifest.read_text())==json.loads(json.dumps(spec))
    else:manifest.write_text(json.dumps(spec,indent=2))
    cpus=sorted(os.sched_getaffinity(0))[::2][:8]
    jobs=[]
    for i,c in enumerate(configs):
        k=i%len(modes);jobs.extend((c,m) for m in modes[k:]+modes[:k])
    path=a.output/'runs.jsonl';rows=[json.loads(l) for l in path.read_text().splitlines()] if path.exists() else []
    seen={(r['config']['id'],r['mode']) for r in rows};jobs=[j for j in jobs if (j[0]['id'],j[1]) not in seen]
    lock=threading.Lock()
    def lane(index):
        for c,m in jobs[index::len(cpus)]:
            command=[sys.executable,'-u','-m','scar_public.study_incremental_channels','--cache',str(a.cache),
                '--worker',json.dumps(c),'--mode',m,'--cpu',str(cpus[index])]
            env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
            proc=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
            assert json.loads(proc.stdout.readline())['phase']=='ready';timeout=False
            try:out,err=proc.communicate('go\n',timeout=15)
            except subprocess.TimeoutExpired:
                timeout=True;proc.terminate()
                try:out,err=proc.communicate(timeout=2)
                except subprocess.TimeoutExpired:proc.kill();out,err=proc.communicate()
            if proc.returncode and not timeout:raise RuntimeError(err)
            phases=[json.loads(l) for l in out.splitlines() if l.strip()]
            r=dict(config=c,mode=m,cpu=cpus[index],phases=phases)
            for x in phases:r.update({k:v for k,v in x.items() if k!='phase'})
            if timeout:r['status']='UNKNOWN_TIMEOUT'
            with lock:
                rows.append(r)
                with path.open('a') as f:f.write(json.dumps(r)+'\n')
            print(json.dumps(dict(id=c['id'],mode=m,status=r['status'],value=r.get('value'),
                seconds=r.get('total_seconds'))),flush=True)
    with ThreadPoolExecutor(max_workers=len(cpus)) as pool:list(pool.map(lane,range(len(cpus))))
    (a.output/'analysis.json').write_text(json.dumps(dict(manifest=spec,rows=rows,
        environment=dict(python=platform.python_version(),cpus=cpus),api_calls=0),separators=(',',':')))


if __name__=='__main__':main()
