"""Author-published LUG tasks, selected by filename before any solver outcome.

Original semantics and the declared a16s1 overlay are separate configurations.
Only explicit dialect conversions are accepted; no arbitrary observe/uncertain
predicate can silently become an ordinary state variable.
"""
import tarfile
from hashlib import sha256
from scar_public.contingent_benchmarks import sexpr
from scar_public.compiled_task import CompiledTask

ARCHIVE='BKS_jair_domains.tgz'
URL='https://rakaposhi.eas.asu.edu/belief-search/'+ARCHIVE
SHA='3b6db211b4eaedab6dc86a5811039f8f440f285283ae6e7ccefccc0ed4bee12d'

def render(x):
    return '('+' '.join(map(render,x))+')' if isinstance(x,list) else str(x)

def normalize(domain,problem):
    d,p=sexpr(domain),sexpr(problem);notes=[]
    init=next(x for x in p if isinstance(x,list) and x[0]==':init')
    for x in init[1:]:
        if x[0]=='uncertain':
            if len(x)!=2:raise ValueError('unsupported uncertain declaration')
            x[0]='unknown';notes.append('uncertain atom -> unknown atom')
    for a in d:
        if not isinstance(a,list) or not a or a[0]!=':action':continue
        if ':effect' not in a:continue
        i=a.index(':effect')+1;e=a[i]
        terms=e[1:] if e and e[0]=='and' else [e]
        observations=[x for x in terms if x and x[0]=='observe']
        if observations:
            if len(observations)!=2:raise ValueError('unsupported effect observation')
            forms=[x[1] for x in observations]
            positive=[x for x in forms if x[0]!='not']
            if len(positive)!=1 or ['not',positive[0]] not in forms or ':observe' in a:
                raise ValueError('observations are not a Boolean complementary pair')
            a[i]=['and']+[x for x in terms if x not in observations]
            a+=[':observe',positive[0]];notes.append('complementary effect observations -> Boolean observe')
    return render(d),render(p),sorted(set(notes))

def configurations():
    out=[]
    sizes={'ring':(2,3,4,5,6),'cubecenter':(3,5,7,9),'bt':(4,6,8,20),
           'btc':(4,6,8,20),'medicalPKS':(4,6,8,12)}
    for family,ns in sizes.items():
        for n in ns:
            for overlay in ('original','a16s1'):
                out.append(dict(id=f'lug_{family}_{n}_{overlay}',family=family,n=n,
                    overlay=overlay,horizon=60,source='lug_author_archive'))
    return out

def source_text(cache,c):
    path=cache/ARCHIVE;raw=path.read_bytes();assert sha256(raw).hexdigest()==SHA
    f,n=c['family'],c['n'];base='BKS_jair_domains/pond/conformant'
    if f=='medicalPKS':base='BKS_jair_domains/pond/conditional'
    if f=='cubecenter' and n==3:base='BKS_jair_domains/cff'
    prefix=f'{base}/{f}/'
    dp=prefix+(f'd{n}.pddl' if f in ('ring','cubecenter','medicalPKS') else 'domain.pddl')
    pp=prefix+(f'p{n}.pddl' if f in ('ring','cubecenter','medicalPKS') else f'pfile{n:03}')
    with tarfile.open(path) as t:d=t.extractfile(dp).read();p=t.extractfile(pp).read()
    error=None
    try:nd,np,notes=normalize(d.decode(),p.decode())
    except ValueError as exc:nd,np,notes=d.decode(),p.decode(),[];error=str(exc)
    return nd,np,dict(url=URL,archive_sha256=SHA,domain_member=dp,problem_member=pp,
        domain_sha256=sha256(d).hexdigest(),problem_sha256=sha256(p).hexdigest(),
        normalized_sha256=sha256((nd+'\n'+np).encode()).hexdigest(),conversions=notes,syntax_error=error)

def load(cache,c):
    d,p,origin=source_text(cache,c);costs={}
    if origin['syntax_error']:raise ValueError('source syntax: '+origin['syntax_error'])
    if c['overlay']=='a16s1':
        for a in sexpr(d):
            if isinstance(a,list) and a and a[0]==':action':
                costs[a[1]]=(0,1) if ':observe' in a else (1,0)
    projections={'ring':('locked','closed','open'),'cubecenter':(),
                 'bt':(),'btc':('clog',),'medicalPKS':('ndead',)}
    t=CompiledTask(d,p,resources=(16,1) if costs else (),resource_costs=costs,
        projection_predicates=projections[c['family']],model_limit=2048,ground_limit=20000)
    return t,origin
