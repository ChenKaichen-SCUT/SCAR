"""Checked BTS/BTCS adapter; original files are fetched, never silently modified.

This is deliberately NOT a general PDDL translator. Only the pinned author
domains and the validated single-bomb problem schema below are accepted.
Bounded water and sensor uses are declared extensions, absent from the source.
"""
from hashlib import sha256
from itertools import product
from math import inf
from pathlib import Path
import re
import tarfile
import urllib.request

from scar_public.finite_planner import State, Goal
from scar_public.information_transfer import compile_reachable, TransferInstance

SOURCE='https://fai.cs.uni-saarland.de/hoffmann/ff/contff-tests.tgz'
ARCHIVE_SHA='e30a16ab8dbfb00e65e6d3dfca31820686d0a8289a718238e25417236ee31e49'
DOMAIN_SHA={'bts':'42672052fcc04721201350936e0f0fc7ab4ffce56abc62399a1b285034a6fdef',
            'btcs':'244ab2321b125c13b5accc19d90a2a23aa2e6423e06cee82ce41cb8bc39ece8d'}


def fetch_archive(path):
    path=Path(path)
    if not path.exists():
        with urllib.request.urlopen(SOURCE,timeout=45) as response:data=response.read()
        if sha256(data).hexdigest()!=ARCHIVE_SHA:raise ValueError('archive checksum changed')
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    if sha256(path.read_bytes()).hexdigest()!=ARCHIVE_SHA:raise ValueError('archive checksum mismatch')
    return path


def sexpr(text):
    tokens=iter(re.findall(r'\(|\)|[^\s()]+',re.sub(r';[^\n]*','',text).lower()))
    def read(token):
        if token!='(':return token
        result=[]
        for nxt in tokens:
            if nxt==')':return result
            result.append(read(nxt))
        raise ValueError('unterminated expression')
    result=read(next(tokens))
    if next(tokens,None) is not None:raise ValueError('trailing expression')
    return result


def typed(items):
    result={};pending=[];i=0
    while i<len(items):
        if items[i]=='-':
            for name in pending:result[name]=items[i+1]
            pending=[];i+=2
        else:pending.append(items[i]);i+=1
    if pending:raise ValueError('untyped objects')
    return result


def read_source(archive,family,count):
    if family not in DOMAIN_SHA or count not in (10,30,50,70):raise ValueError('not an original input')
    fetch_archive(archive)
    with tarfile.open(archive) as tar:
        # Read only named regular files; do not extract archive paths to disk.
        domain=tar.extractfile(f'contff-tests/{family}/domain.pddl').read()
        problem=tar.extractfile(f'contff-tests/{family}/pfile{count:03d}').read()
    if sha256(domain).hexdigest()!=DOMAIN_SHA[family]:raise ValueError('unrecognized domain')
    parsed=sexpr(problem.decode())
    objects=typed(next(p[1:] for p in parsed if isinstance(p,list) and p[0]==':objects'))
    packages=tuple(p for p,t in objects.items() if t=='package')
    assert len(packages)==count and {p for p,t in objects.items() if t=='bomb'}=={'b0'}
    assert {p for p,t in objects.items() if t=='toilet'}=={'t0'}
    assert len(objects)==count+2
    init=next(p[1:] for p in parsed if isinstance(p,list) and p[0]==':init')
    expected=[['unknown',['in',p,'b0']] for p in packages]+[['oneof']+[['in',p,'b0'] for p in packages]]
    assert init==expected
    assert [':goal',['defused','b0']] in parsed and [':domain',family] in parsed
    return dict(domain=sexpr(domain.decode()),packages=packages,objects=objects,
                provenance=dict(url=SOURCE,archive_sha256=ARCHIVE_SHA,domain_sha256=sha256(domain).hexdigest(),
                    problem_sha256=sha256(problem).hexdigest(),member=f'{family}/pfile{count:03d}'))


def pddl_step(source,hidden,state,action):
    """Independent tiny interpreter of the pinned PDDL, used for conformance."""
    verb,_,package=action.partition(':')
    schema=next(s for s in source['domain'] if isinstance(s,list) and s[:2]==[':action',verb])
    fields=dict(zip(schema[2::2],schema[3::2]))
    env={'?p':package,'?b':'b0','?t':'t0'}
    facts={('in',hidden,'b0')}
    if state.symbols[0]:facts.add(('clog','t0'))
    if state.symbols[1]:facts.add(('defused','b0'))
    def atom(x):return tuple(env.get(y,y) for y in x)
    def holds(x):
        if x[0]=='not':return not holds(x[1])
        if x[0]=='and':return all(holds(y) for y in x[1:])
        return atom(x) in facts
    if ':precondition' in fields and not holds(fields[':precondition']):return None
    successor=set(facts)
    def effect(x):
        if x[0]=='and':
            for y in x[1:]:effect(y)
        elif x[0]=='when':
            if holds(x[1]):effect(x[2])
        elif x[0]=='not':successor.discard(atom(x[1]))
        else:successor.add(atom(x))
    if ':effect' in fields:effect(fields[':effect'])
    obs=(holds(fields[':observe']),) if ':observe' in fields else ()
    return State((('clog','t0') in successor,('defused','b0') in successor,True),()),obs


def bomb_case(family='bts',count=4,water=None,sensors=None,horizon=None,archive=None):
    if family not in DOMAIN_SHA or count<1:raise ValueError('invalid family/size')
    if (water is None)!=(sensors is None):raise ValueError('specify both extension budgets')
    if water is not None and (water<0 or sensors<0):raise ValueError('negative budget')
    source=read_source(archive,family,count) if archive is not None else None
    packages=source['packages'] if source else tuple(f'p{i}' for i in range(count))
    actions=[f'dunk:{p}' for p in packages]+[f'sensep:{p}' for p in packages]
    if family=='btcs':actions.append('flush')
    costs=dict.fromkeys(actions,1)
    limited=water is not None
    initial=State((False,False,True),(water,sensors) if limited else ())
    dead=State((False,False,False),(0,0) if limited else ())
    def transition(hidden,state,action):
        clogged,defused,valid=state.symbols
        if not valid:return state,()
        verb,_,package=action.partition(':');resources=list(state.resources)
        if verb=='dunk':
            if (family=='btcs' and clogged) or (limited and resources[0]==0):return dead,()
            if limited:resources[0]-=1
            defused=defused or hidden==package
            clogged=family=='btcs';obs=()
        elif verb=='sensep':
            if limited and resources[1]==0:return dead,()
            if limited:resources[1]-=1
            obs=(hidden==package,)
        else:clogged=False;obs=()
        return State((clogged,defused,True),tuple(resources)),obs
    domains=((False,True),)*3
    models=[compile_reachable(p,initial,domains,costs,transition) for p in packages]
    goal=Goal(symbols=((1,True),));allowed=lambda s:s.symbols[2]
    horizon=(count if family=='bts' or not limited else 2*count-1) if horizon is None else horizon
    metadata=dict(count=count,water=water,sensors=sensors,projection=[0],
        source_kind='original' if source and not limited else ('resource_extension' if limited else 'generated_size'),
        source=source['provenance'] if source else None,
        observations='Only sensep observes in(package,bomb); dunk/flush have no observation.',
        goal='defused(b0); no requirement to unclog the toilet',
        resource_extension='dunk consumes one water, sensep one sensor use; flush consumes no resource' if limited else None)
    name=f'{family}_n{count}_w{water}_s{sensors}_h{horizon}'
    return TransferInstance(name,family,models,goal,frozenset((p,initial) for p in packages),horizon,allowed,metadata)


def closed_form_value(family,count,water,sensors,horizon):
    """Analytic reference for THIS family only; never used in search or bounds."""
    if water is None:value=count
    elif water<1 or water+sensors<count:value=inf
    else:value=count if family=='bts' else 2*count-min(sensors,count-1)-1
    return value if value<=horizon else inf


def check_source_conformance(archive):
    checks=0
    for family in DOMAIN_SHA:
        source=read_source(archive,family,10);case=bomb_case(family,10,archive=archive)
        for model in case.models:
            for (state,action),compiled in model.lookup.items():
                if not case.allowed(state):continue
                reference=pddl_step(source,model.name,state,action)
                actual=model.step(state,action)
                if reference is None:assert not case.allowed(actual[0])
                else:assert reference==actual,(family,model.name,state,action)
                checks+=1
    return checks
