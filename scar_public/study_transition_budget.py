"""Small disclosed post-holdout diagnostic; never merged into holdout coverage."""
import argparse,json,os,platform,subprocess,sys
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
from scar_public import study_information_gaps as study
from scar_public.transition_budgeted_planner import TransitionBudgetedPlanner


def main():
    p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,required=True)
    p.add_argument('--worker');p.add_argument('--mode');p.add_argument('--cpu',type=int)
    p.add_argument('--output',type=Path,default=Path('scar_public/results/2026-10-17-information-gaps/transition_diagnostic'))
    a=p.parse_args()
    if a.worker:
        study.BudgetedPlanner=TransitionBudgetedPlanner;return study.worker(a)
    cases=[c for c in study.cases() if c['cohort']=='old_failure_diagnostic' or
        (c['family']=='unix' and c['instance']=='4' and c['cohort']=='new_public_original')]
    assert len(cases)==6
    modes=['leaf','leaf_lineage_scheduled'];a.output.mkdir(parents=True,exist_ok=True)
    names=['transition_budgeted_planner.py','study_transition_budget.py','budgeted_planner.py']
    spec=dict(cases=cases,modes=modes,limit_seconds=15,memory_mib=2048,
        source_hashes={n:sha256((Path(__file__).parent/n).read_text().encode()).hexdigest() for n in names},
        scope='Exploratory post-holdout engineering diagnostic after inspecting frozen main outcomes. '
            'No claim of independent validation, no tuning of the frozen method, no external baseline reruns.',
        changes='BFS transition lookups <=4096/query and <=65536/run; nominal singleton work '
            '<=0.05s/query and <=1s/run including hmax (one atomic operation may overrun). '
            'Stop new hmax allocation after global effect budget is exhausted; scheduled relation calls '
            'require >=0.025s credit and at most 32 attempts/run.')
    (a.output/'manifest.json').write_text(json.dumps(spec,indent=2))
    jobs=[(c,m) for c in cases for m in modes];cpus=sorted(os.sched_getaffinity(0))[::2][:8]
    def lane(index):
        rows=[]
        for c,m in jobs[index::len(cpus)]:
            cmd=[sys.executable,'-u','-m','scar_public.study_transition_budget','--cache',str(a.cache),
                '--worker',json.dumps(c),'--mode',m,'--cpu',str(cpus[index])]
            proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            assert json.loads(proc.stdout.readline())['phase']=='ready';timeout=False
            try:out,err=proc.communicate('go\n',timeout=15)
            except subprocess.TimeoutExpired:
                timeout=True;proc.terminate()
                try:out,err=proc.communicate(timeout=2)
                except subprocess.TimeoutExpired:proc.kill();out,err=proc.communicate()
            if proc.returncode and not timeout:raise RuntimeError(err)
            phases=[json.loads(l) for l in out.splitlines() if l.strip()]
            r=dict(config=c,mode=m,phases=phases)
            for x in phases:r.update({k:v for k,v in x.items() if k!='phase'})
            if timeout:r['status']='UNKNOWN_TIMEOUT'
            rows.append(r);print(json.dumps(dict(id=c['id'],mode=m,status=r['status'])),flush=True)
        return rows
    with ThreadPoolExecutor(max_workers=len(cpus)) as pool:
        rows=[r for group in pool.map(lane,range(len(cpus))) for r in group]
    (a.output/'analysis.json').write_text(json.dumps(dict(manifest=spec,rows=rows,
        environment=dict(python=platform.python_version(),cpus=cpus)),separators=(',',':')))


if __name__=='__main__':main()
