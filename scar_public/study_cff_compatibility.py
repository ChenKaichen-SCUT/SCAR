"""Declared CFF syntax-only compatibility experiment, separate from raw inputs."""
import argparse,json,re
from hashlib import sha256
from pathlib import Path
from scar_public.benchmark_suite import configurations,source_text
from scar_public.contingent_benchmarks import sexpr
from scar_public.symbolic_task import flatten_and,SymbolicTask
from scar_public import published_planners as published

def compatible_source(cache,family,instance):
    d,p,origin=source_text(cache,family,instance)
    # Only remove the unsupported feature DECLARATION. Sensing actions stay intact.
    pattern=r'(\(:requirements[^)]*)\s:contingent(?=[\s)])'
    edited,count=re.subn(pattern,r'\1',d,flags=re.IGNORECASE)
    assert count==1
    tree=sexpr(p)
    initial=next(x for x in tree if isinstance(x,list) and x and x[0]==':init')
    initial[1:]=[clause for item in initial[1:] for clause in flatten_and(item)]
    uncertain=[]
    for clause in initial[1:]:
        if clause[0]=='oneof':
            for atom in clause[1:]:
                assert all(isinstance(x,str) for x in atom) and atom[0] not in ('and','or','not')
                if atom not in uncertain:uncertain.append(atom)
    for atom in uncertain:
        if ['unknown',atom] not in initial:initial.append(['unknown',atom])
    def serialize(x):return '('+' '.join(serialize(y) for y in x)+')' if isinstance(x,list) else x
    problem=serialize(tree)+'\n'
    # In our checked semantics, the added unknown declarations do not change the
    # initial belief. Compare named fact sets, not translator-specific bit IDs.
    original=SymbolicTask(d,p);normalized=SymbolicTask(edited,problem)
    def worlds(t):return {frozenset(atom for i,atom in enumerate(t.atom_names) if s&(1<<i)) for s in t.initial_bits}
    assert worlds(original)==worlds(normalized)
    origin=dict(origin,compatibility_edit='Remove :contingent requirement; flatten conjunctions inside :init. '
                'Add redundant explicit unknown declarations for positive oneof alternatives. Initial-world equality checked. '
                'No action, initial logical constraint, or goal semantics changed. Returned policies replay on originals.',
                compatibility_domain_sha256=sha256(edited.encode()).hexdigest(),
                compatibility_problem_sha256=sha256(problem.encode()).hexdigest())
    return edited,problem,origin

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,required=True);p.add_argument('--binary',type=Path,required=True)
    p.add_argument('--output',type=Path,default=Path('scar_public/results/2026-10-16-symbolic-coverage/compatibility_v3'))
    a=p.parse_args();published.source_text=compatible_source;rows=[]
    for c in configurations():
        if c['cohort']!='original' or c['family'] not in ('doors','localize'):continue
        for h in (2,3):
            folder=a.output/f'{c["id"]}_h{h}'
            r=dict(config=c,**published.run_cff(a.cache,c,a.binary,folder,h,15));rows.append(r)
            (folder/'result.json').write_text(json.dumps(r,indent=2));print(c['id'],h,r['status'],flush=True)
    (a.output/'analysis.json').write_text(json.dumps(rows,indent=2))
