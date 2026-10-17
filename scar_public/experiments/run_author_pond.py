"""Run author POND after the matched-engine experiment has finished.

Both configurations are external planner context, not matched-engine evidence
or optimality claims. The regular mutex flag is NOT Appendix-B cross-world LUG.
All raw native inputs/outputs are retained for independent policy replay.
"""
import json,os,subprocess,tarfile,time,resource
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
from scar_public.label_scale_suite import configurations,source_text,ARCHIVE

root=Path.cwd();out=root/'external';out.mkdir(exist_ok=True)
binary=root/'pond/src/pond'
cases=[c for c in configurations() if c['overlay']=='original']
methods={'pond_lugrp':['-h','lugrp'], 'pond_luglevel_mutex':['-h','luglevel','-mutex']}
spec=dict(cases=cases,methods=methods,seconds=30,memory_mib=2048,svn_revision=313,
    svn_url='https://svn.code.sf.net/p/pond/code',binary_sha256=sha256(binary.read_bytes()).hexdigest(),
    script_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),repetitions=1,
    scope='Native author dialect; A* for conformant, AO* for conditional. No particles, no fixed seed. '
    'Regular mutex flag only; no claim to reproduce Appendix-B cross-world implementation. '
    'No external solution is counted without independent replay. No optimality claim. '
    'Native budget-free originals only; overlays are not silently dropped in a paired comparison.')
mp=out/'manifest.json'
if mp.exists():assert json.loads(mp.read_text())==spec
else:mp.write_text(json.dumps(spec,indent=2))
while not (root/'results/environment.json').exists():time.sleep(2)
cpus=[];cores=set()
for cpu in sorted(os.sched_getaffinity(0)):
    t=Path(f'/sys/devices/system/cpu/cpu{cpu}/topology')
    core=((t/'physical_package_id').read_text(),(t/'core_id').read_text())
    if core not in cores:cores.add(core);cpus.append(cpu)
jobs=[(c,m) for c in cases for m in methods]
def lane(i):
    for c,m in jobs[i::len(cpus)]:
        folder=out/(c['id']+'_'+m);folder.mkdir(exist_ok=True)
        rp=folder/'result.json'
        if rp.exists():continue
        _,_,origin=source_text(root,c)
        with tarfile.open(root/ARCHIVE) as t:
            for name,key in [('d.pddl','domain_member'),('p.pddl','problem_member')]:
                (folder/name).write_bytes(t.extractfile(origin[key]).read())
        cmd=[str(binary),str(folder/'d.pddl'),str(folder/'p.pddl'),'-s',
            'aostar' if c['family']=='medicalPKS' else 'astar',*methods[m],'-v','1']
        # taskset does affinity in the child without unsafe threaded preexec_fn.
        cmd=['prlimit','--as='+str(2048*1024**2),'--','taskset','-c',str(cpus[i]),*cmd]
        started=time.perf_counter()
        with (folder/'stdout.txt').open('w') as f:
            p=subprocess.Popen(cmd,cwd=folder,stdout=f,stderr=subprocess.STDOUT)
            try:code=p.wait(timeout=30);timeout=False
            except subprocess.TimeoutExpired:p.kill();code=p.wait();timeout=True
        r=dict(config=c,method=m,command=cmd,seconds=time.perf_counter()-started,
            returncode=code,timed_out=timeout,cpu=cpus[i],source=origin,
            status='UNKNOWN_TIMEOUT' if timeout else 'UNVERIFIED_OUTPUT',optimality_claim=False)
        rp.write_text(json.dumps(r,indent=2));print(json.dumps(dict(id=c['id'],method=m,code=code,timeout=timeout)),flush=True)
with ThreadPoolExecutor(max_workers=len(cpus)) as pool:list(pool.map(lane,range(len(cpus))))
(out/'finished.json').write_text(json.dumps(dict(runs=len(jobs),cpus=cpus)))
