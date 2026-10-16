"""Author Contingent-FF runner/parser. No claim of admissible/optimal hFF."""
from hashlib import sha256
from pathlib import Path
import os
import re
import subprocess
from time import perf_counter

from scar_public.benchmark_suite import source_text,load_case
from scar_public.symbolic_coverage import LazyCoveragePlanner


def parse_cff(text):
    nodes={}
    for line in text.splitlines():
        m=re.match(r'\s*(\d+)\|\|(-?\d+)\s+---\s+(.*?)\s+---\s+(.*)',line)
        if not m:continue
        layer,index,action,links=m.groups();edges={}
        for kind,l,i in re.findall(r'(TRUESON|FALSESON|SON):\s*(\d+)\|\|(-?\d+)',links):
            obs=() if kind=='SON' else (kind=='TRUESON',)
            edges[obs]=(int(l),int(i))
        if not edges:raise ValueError('unparsed plan edges')
        nodes[int(layer),int(index)]=(' '.join(action.lower().split()),edges)
    def build(key,ancestors=frozenset()):
        if key[1]==-1:return {'stop':True}
        if key in ancestors:raise ValueError('cyclic output not a finite policy')
        action,edges=nodes[key]
        return dict(action=action,branches={o:build(child,ancestors|{key}) for o,child in edges.items()})
    if not nodes:raise ValueError('no parsed policy')
    return build((0,0))


def run_cff(cache,config,binary,output,heuristic=2,limit=15):
    folder=Path(output).resolve();folder.mkdir(parents=True,exist_ok=True)
    d,p,origin=source_text(cache,config['family'],config['instance'])
    domain=folder/'domain.pddl';problem=folder/'problem.pddl'
    domain.write_text(d);problem.write_text(p)
    binary=Path(binary).resolve()
    command=[str(binary),'-o',str(domain),'-f',str(problem),'-a','0','-m','1','-h',str(heuristic)]
    cpu=min(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else None
    def limits():
        import resource
        resource.setrlimit(resource.RLIMIT_AS,(2048*1024**2,2048*1024**2))
        if cpu is not None:os.sched_setaffinity(0,{cpu})
    start=perf_counter()
    try:
        proc=subprocess.run(command,capture_output=True,text=True,cwd=folder,timeout=limit,
                            preexec_fn=limits if os.name=='posix' else None)
        text=proc.stdout+'\n'+proc.stderr;code=proc.returncode;timed_out=False
    except subprocess.TimeoutExpired as error:
        def decoded(s):return s.decode(errors='replace') if isinstance(s,bytes) else (s or '')
        text=decoded(error.stdout)+'\n'+decoded(error.stderr)
        code=None;timed_out=True
    elapsed=perf_counter()-start
    (folder/'stdout.txt').write_text(text,encoding='utf-8')
    result=dict(method=f'cff_h{heuristic}',binary_sha256=sha256(binary.read_bytes()).hexdigest(),
        options=command[5:],seconds=elapsed,returncode=code,timed_out=timed_out,cpu=cpu,memory_limit_mib=2048,
        status='UNKNOWN_TIMEOUT' if timed_out else 'NO_VERIFIED_POLICY',source=origin,
        stdout_sha256=sha256(text.encode()).hexdigest(),policy_verified=False,optimality_claim=False)
    if 'ff: found plan as follows' in text:
        try:
            policy=parse_cff(text);task,_=load_case(cache,dict(config,sensor_budget=None,actuation_budget=None))
            planner=LazyCoveragePlanner(task,'single')
            # Replay with a generous finite guard; bounded success is checked separately.
            depth=planner.verify(task.belief,10000,policy)
            result.update(status='VERIFIED_POLICY' if depth<=config['horizon'] else 'VERIFIED_POLICY_OUTSIDE_H',
                policy_verified=True,worst_case_depth=depth,within_horizon=depth<=config['horizon'])
        except (AssertionError,KeyError,ValueError,RecursionError) as error:
            result.update(status='POLICY_VALIDATION_FAILED',validation_error=type(error).__name__+': '+str(error))
    return result
