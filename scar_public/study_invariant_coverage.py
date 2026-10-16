"""Post-main-study diagnostic: invariants versus identical channel optimizations.

All medical-5, doors-5, rover-2 original/overlay configurations are retained.
The previous main experiment is frozen; no baseline reruns are needed.
"""
import argparse,json,os,subprocess,sys
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from scar_public.benchmark_suite import configurations
from scar_public.invariant_coverage import InvariantCoveragePlanner
from scar_public import study_symbolic_coverage as study

def main():
    p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,required=True);p.add_argument('--worker');p.add_argument('--mode');p.add_argument('--cpu',type=int)
    p.add_argument('--output',type=Path,default=Path('scar_public/results/2026-10-16-symbolic-coverage/diagnostic.json'))
    args=p.parse_args()
    if args.worker:
        study.LazyCoveragePlanner=InvariantCoveragePlanner;return study.worker(args)
    cases=[c for c in configurations() if (c['family'],c['instance']) in [('doors','5'),('medical','pfile005'),('rovers','pfile2')]]
    spec=dict(cases=cases,modes=['symbolic_filtered','symbolic_invariants'],limit_seconds=15,memory_limit_mib=2048,
        motivation='Post-main-study diagnosis of unreachable dynamic/static combinations; paired no-invariant optimization control.',
        sources={n:sha256((Path(__file__).parent/n).read_text().encode()).hexdigest() for n in ('invariant_coverage.py','study_invariant_coverage.py')})
    manifest=args.output.with_suffix('.manifest.json')
    if manifest.exists():assert json.loads(manifest.read_text())==json.loads(json.dumps(spec))
    else:manifest.write_text(json.dumps(spec,indent=2))
    cpus=sorted(os.sched_getaffinity(0))[::2][:8];jobs=[(c,m) for c in cases for m in spec['modes']]
    def lane(index):
        result=[]
        for c,m in jobs[index::len(cpus)]:
            command=[sys.executable,'-u','-m','scar_public.study_invariant_coverage','--cache',str(args.cache),
                '--worker',json.dumps(c),'--mode',m,'--cpu',str(cpus[index])]
            start=perf_counter();p=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            assert json.loads(p.stdout.readline())['phase']=='ready';startup=perf_counter()-start;timeout=False
            try:out,err=p.communicate('go\n',timeout=15)
            except subprocess.TimeoutExpired:timeout=True;p.kill();out,err=p.communicate()
            if p.returncode and not timeout:raise RuntimeError(err)
            phases=[json.loads(l) for l in out.splitlines() if l.strip()]
            r=dict(config=c,mode=m,cpu=cpus[index],phases=phases,status='UNKNOWN',startup_seconds=startup,wall_seconds=perf_counter()-start)
            for phase in phases:r.update({k:v for k,v in phase.items() if k!='phase'})
            if timeout:r['status']='UNKNOWN_TIMEOUT'
            if any(x['phase']=='error' for x in phases):r['status']='UNKNOWN_LIMIT_OR_ERROR'
            result.append(r);print(json.dumps(dict(id=c['id'],mode=m,status=r['status'],root=r.get('root_lower'))),flush=True)
        return result
    with ThreadPoolExecutor(max_workers=len(cpus)) as pool:rows=[r for results in pool.map(lane,range(len(cpus))) for r in results]
    args.output.write_text(json.dumps(dict(manifest=spec,rows=rows),indent=2))

if __name__=='__main__':main()
