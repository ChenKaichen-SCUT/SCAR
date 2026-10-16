"""One frozen published CFF configuration on new public ORIGINAL tasks only.

Raw source dialect is retained; no claim that unverified failure is infeasibility.
No runs of old frozen baselines. Returned policies are replayed when the checked
finite frontend can load the task. Outside-fragment policies remain unverified.
"""
import argparse,json,os,platform,subprocess,sys
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
from scar_public import holdout_suite,published_planners


def main():
    p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,required=True)
    p.add_argument('--binary',type=Path,required=True)
    p.add_argument('--worker');p.add_argument('--cpu',type=int)
    p.add_argument('--output',type=Path,default=Path('scar_public/results/2026-10-17-information-gaps/external_process'))
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    cases=[c for c in holdout_suite.configurations() if c['cohort']=='new_public_original']
    if a.worker:
        os.sched_setaffinity(0,{a.cpu});c=next(c for c in cases if c['id']==a.worker)
        published_planners.source_text=lambda cache,family,instance:holdout_suite.source_text(cache,c)
        published_planners.load_case=holdout_suite.load_case
        output=a.output/c['id'];output.mkdir(parents=True,exist_ok=True)
        r=dict(config=c,**published_planners.run_cff(a.cache,c,a.binary,output,2,15))
        (output/'result.json').write_text(json.dumps(r,indent=2));return
    names=['study_holdout_external.py','published_planners.py','holdout_suite.py','symbolic_task.py']
    spec=dict(cases=cases,method='Contingent-FF author binary -a 0 -m 1 -h 2',limit_seconds=15,
        memory_mib=2048,repetitions=1,binary_sha256=sha256(a.binary.read_bytes()).hexdigest(),
        sources={n:sha256((Path(__file__).parent/n).read_text().encode()).hexdigest() for n in names},
        infrastructure='One Python process per case; Z3 replay contexts must not share threads. '
            'The initial threaded replay attempt crashed in Z3 before saving any result; '
            'that attempt is retained separately as external, and is not a planner outcome.',
        scope='Only 26 new source-original tasks. Raw dialect, no resource overlays or old reruns. '
            'Satisficing planner: policy depth verified, no optimality claim; compare feasible coverage separately.')
    (a.output/'manifest.json').write_text(json.dumps(spec,indent=2))
    cpus=sorted(os.sched_getaffinity(0))[::2][:8]
    def lane(index):
        rows=[]
        for c in cases[index::len(cpus)]:
            output=a.output/c['id'];target=output/'result.json'
            if target.exists():r=json.loads(target.read_text())
            else:
                proc=subprocess.run([sys.executable,'-u','-m','scar_public.study_holdout_external',
                    '--cache',str(a.cache),'--binary',str(a.binary),'--output',str(a.output),
                    '--worker',c['id'],'--cpu',str(cpus[index])],capture_output=True,text=True,timeout=90)
                if proc.returncode:raise RuntimeError(proc.stderr)
                r=json.loads(target.read_text())
            rows.append(r);print(json.dumps(dict(id=c['id'],status=r['status'],depth=r.get('worst_case_depth'))),flush=True)
        return rows
    with ThreadPoolExecutor(max_workers=len(cpus)) as pool:
        rows=[r for group in pool.map(lane,range(len(cpus))) for r in group]
    (a.output/'analysis.json').write_text(json.dumps(dict(manifest=spec,rows=rows,
        environment=dict(python=platform.python_version(),cpus=cpus)),separators=(',',':')))


if __name__=='__main__':main()
