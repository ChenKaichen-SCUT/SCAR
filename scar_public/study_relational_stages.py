"""Post-primary Rover diagnosis: one-hop goal-support projection, paired modes.

The 8 Rover configurations are all retained; earlier projection results are
reused. This is a disclosed diagnostic factorial, not a held-out evaluation.
"""
import argparse,json,os,subprocess,sys
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from scar_public.benchmark_suite import configurations,load_case
from scar_public.symbolic_task import atoms
from scar_public import study_relational_coverage as study


def load_stage_case(cache,config):
    task,origin=load_case(cache,config);goal=atoms(task.goal_expr);selected=set(task.projection)
    for a in task.actions.values():
        for guard,lit in a.effects:
            if abs(lit)-1 in goal:selected|=(atoms(a.pre)|atoms(guard))&task.dynamic
    task.projection=tuple(sorted(selected));task.projection_mask=sum(1<<i for i in selected)
    return task,origin


def main():
    p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,required=True);p.add_argument('--worker');p.add_argument('--mode');p.add_argument('--cpu',type=int)
    p.add_argument('--node-limit',type=int,default=5000);p.add_argument('--freeze',action='store_true')
    p.add_argument('--output',type=Path,default=Path('scar_public/results/2026-10-16-relational-coverage/stages'))
    a=p.parse_args()
    if a.worker:
        study.load_case=load_stage_case;return study.worker(a)
    a.output.mkdir(parents=True,exist_ok=True)
    cases=[c for c in configurations() if c['family']=='rovers']
    spec=dict(cases=cases,modes=['counts','matching'],limit_seconds=15,node_limit=5000,
        timing='Same worker, memory limit and SIGTERM grace as primary; no LLM or external baseline rerun.',
        motivation='Post-primary diagnostic: retain dynamic preconditions/guards of actions affecting goal atoms; no solution feedback used for selecting atoms.',
        sources={n:sha256((Path(__file__).parent/n).read_text().encode()).hexdigest() for n in
                 ('study_relational_stages.py','study_relational_coverage.py','relational_coverage.py')},
        projections={c['id']:load_stage_case(a.cache,c)[0].metadata()['projection_atoms'] for c in cases})
    manifest=a.output/'manifest.json'
    if manifest.exists():assert json.loads(manifest.read_text())==json.loads(json.dumps(spec))
    else:manifest.write_text(json.dumps(spec,indent=2))
    if a.freeze:print('Frozen',len(cases),'Rover cases, paired modes');return
    cpus=sorted(os.sched_getaffinity(0))[::2][:8];jobs=[(c,m) for c in cases for m in spec['modes']]
    def lane(index):
        rows=[]
        for c,m in jobs[index::len(cpus)]:
            cmd=[sys.executable,'-u','-m','scar_public.study_relational_stages','--cache',str(a.cache),
                 '--worker',json.dumps(c),'--mode',m,'--cpu',str(cpus[index]),'--node-limit',str(a.node_limit)]
            start=perf_counter();proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            assert json.loads(proc.stdout.readline())['phase']=='ready';startup=perf_counter()-start;timeout=False;killed=False
            try:out,err=proc.communicate('go\n',timeout=15)
            except subprocess.TimeoutExpired:
                timeout=True;proc.terminate()
                try:out,err=proc.communicate(timeout=2)
                except subprocess.TimeoutExpired:killed=True;proc.kill();out,err=proc.communicate()
            if proc.returncode and not timeout:raise RuntimeError(err)
            phases=[json.loads(l) for l in out.splitlines() if l.strip()]
            r=dict(config=c,mode=m,phases=phases,status='UNKNOWN',timed_out=timeout,hard_killed=killed,
                   startup_seconds=startup,wall_seconds=perf_counter()-start,cpu=cpus[index])
            for phase in phases:r.update({k:v for k,v in phase.items() if k!='phase'})
            if timeout:r['status']='UNKNOWN_TIMEOUT'
            if any(x['phase']=='error' for x in phases):r['status']='UNKNOWN_LIMIT_OR_ERROR'
            rows.append(r);print(json.dumps(dict(id=c['id'],mode=m,status=r['status'],root=r.get('root_lower'),seconds=r.get('total_seconds'))),flush=True)
        return rows
    with ThreadPoolExecutor(max_workers=len(cpus)) as pool:rows=[r for lane_rows in pool.map(lane,range(len(cpus))) for r in lane_rows]
    (a.output/'analysis.json').write_text(json.dumps(dict(manifest=spec,rows=rows),separators=(',',':')))

if __name__=='__main__':main()
