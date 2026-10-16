"""Frozen source/extension scaling pilot, isolated per-method time limits.

One timing sample: no significance or stable speedup claims. Timeout means
UNKNOWN, not an infeasibility proof. Includes compilation and all preprocessing.
"""
import argparse
from hashlib import sha256
import json
from math import inf
from pathlib import Path
import subprocess
import sys
from time import perf_counter

from scar_public.contingent_benchmarks import bomb_case, closed_form_value, check_source_conformance, ARCHIVE_SHA
from scar_public.coverage_planner import CoveragePlanner
from scar_public.finite_planner import printable

MODES=CoveragePlanner.MODES


def manifest():
    cases=[]
    for f in ('bts','btcs'):
        for n in (10,30,50,70):
            for h in (n,n-1):
                cases.append(dict(family=f,count=n,water=None,sensors=None,horizon=h,original=True))
        for n in (4,8,12,16):
            for r,s in ((3,0),(n-2,2)):
                cases.append(dict(family=f,count=n,water=r,sensors=s,horizon=2*n-1,original=False))
    return dict(protocol_version=1,modes=MODES,cases=cases,repetitions=1,limit_seconds=3,
        objective='minimum worst-case unit action count, strong finite-horizon policies',
        original_archive_sha256=ARCHIVE_SHA,
        timing='Fresh subprocess per cell. Compilation, planner construction, root bound and search timed. '
               'Interpreter/module startup and policy replay reported separately, excluded equally. '
               'Timeout retains completed phase results; never interpreted as infeasible.',
        selection='All four published sizes in BTS/BTCS, at H=n and H=n-1; declared resource extensions '
                  'at n=4,8,12,16 with fixed-k failure (3,0) and boundary-feasible (n-2,2).',
        caveat='Two closely related domains: first scaling pilot, not a representative suite or published-planner comparison.')


def worker(config,mode,archive):
    def emit(phase,**data):print(json.dumps(dict(phase=phase,**data)),flush=True)
    emit('ready')
    assert sys.stdin.readline().strip()=='go'
    t=perf_counter();args=dict(config);original=args.pop('original')
    case=bomb_case(**args,archive=archive if original else None)
    compiled=perf_counter()
    emit('compiled',compile_seconds=compiled-t,transitions=sum(len(m.cases) for m in case.models),metadata=case.metadata)
    p=CoveragePlanner(case.models,case.goal,case.allowed,mode=mode,indices=(0,))
    constructed=perf_counter();root=p.initial(case.belief,case.horizon).lower;bounded=perf_counter()
    emit('root',root_lower=printable(root),construct_seconds=constructed-compiled,
         root_seconds=bounded-constructed,root_statistics=p.statistics())
    result=p.solve(case.belief,case.horizon);finished=perf_counter()
    assert result.exact
    truth=closed_form_value(config['family'],config['count'],config['water'],config['sensors'],config['horizon'])
    assert root<=truth and result.upper==truth,(config,mode,root,result.upper,truth)
    replay_start=perf_counter()
    if result.upper<inf:assert p.verify(case.belief,case.horizon,result.policy)==result.upper
    emit('done',value=printable(result.upper),status=result.status,search_seconds=finished-bounded,
         total_seconds=finished-t,statistics=p.statistics(),replay_seconds=perf_counter()-replay_start)


def run_cell(config,mode,archive,limit):
    # Ready handshake removes module startup from the strict work budget.
    start=perf_counter()
    command=[sys.executable,'-u','-m','scar_public.study_policy_coverage','--worker',json.dumps(config),
             '--mode',mode,'--archive',str(archive)]
    p=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    ready=p.stdout.readline()
    if not ready or json.loads(ready).get('phase')!='ready':raise RuntimeError(p.stderr.read())
    startup=perf_counter()-start;timed_out=False
    try:out,err=p.communicate(input='go\n',timeout=limit)
    except subprocess.TimeoutExpired:
        timed_out=True;p.kill();out,err=p.communicate()
    if p.returncode and not timed_out:raise RuntimeError(err)
    phases=[json.loads(line) for line in out.splitlines() if line.strip()]
    result=dict(mode=mode,startup_seconds=startup,watchdog_seconds=limit,timed_out=timed_out,
                status='UNKNOWN_TIMEOUT' if timed_out else 'COMPLETED',phases=phases)
    for phase in phases:result.update({k:v for k,v in phase.items() if k not in ('phase','status')})
    if timed_out:result['status']='UNKNOWN_TIMEOUT'
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--archive',type=Path,default=Path('../planning_sources/contff-tests.tgz'))
    parser.add_argument('--output',type=Path,default=Path('scar_public/results/2026-10-16-policy-coverage'))
    parser.add_argument('--worker');parser.add_argument('--mode');parser.add_argument('--freeze',action='store_true')
    args=parser.parse_args()
    if args.worker:return worker(json.loads(args.worker),args.mode,args.archive)
    args.output.mkdir(parents=True,exist_ok=True);path=args.output/'manifest.json'
    spec=manifest()
    if args.freeze:
        if path.exists():assert json.loads(path.read_text())==json.loads(json.dumps(spec))
        else:path.write_text(json.dumps(spec,indent=2),encoding='utf-8')
        print('Manifest frozen before measurement.');return
    assert path.exists(),'Freeze manifest first'
    assert json.loads(path.read_text())==json.loads(json.dumps(spec))
    conformance=check_source_conformance(args.archive)
    rows=[];t=perf_counter();runs=args.output/'runs.jsonl'
    # Resume only cells with the same manifest and source hashes.
    hashes={name:sha256((Path(__file__).parent/name).read_bytes()).hexdigest() for name in
            ('coverage_planner.py','contingent_benchmarks.py','study_policy_coverage.py','finite_planner.py','information_bound.py')}
    record=args.output/'source_hashes.json'
    if record.exists():assert json.loads(record.read_text())==hashes
    else:record.write_text(json.dumps(hashes,indent=2),encoding='utf-8')
    if runs.exists():rows=[json.loads(line) for line in runs.read_text().splitlines()]
    seen={(json.dumps(row['config'],sort_keys=True),row['mode']) for row in rows}
    for index,config in enumerate(spec['cases']):
        offset=index%len(MODES)
        for mode in MODES[offset:]+MODES[:offset]:
            if (json.dumps(config,sort_keys=True),mode) in seen:continue
            row=dict(config=config,**run_cell(config,mode,args.archive,spec['limit_seconds']))
            rows.append(row)
            with runs.open('a',encoding='utf-8') as handle:handle.write(json.dumps(row)+'\n')
            print(json.dumps(dict(completed=len(rows),family=config['family'],n=config['count'],mode=mode,
                timeout=row['timed_out'],root=row.get('root_lower'),seconds=row.get('total_seconds'))),flush=True)
    result=dict(manifest=spec,source_sha256=hashes,conformance_transition_checks=conformance,
                api_calls=0,game_actions=0,random_seeds_used=False,rows=rows,wall_seconds_this_invocation=perf_counter()-t)
    (args.output/'analysis.json').write_text(json.dumps(result,indent=2),encoding='utf-8')


if __name__=='__main__':main()
