"""New public source instances selected without inspecting planner performance.

Original tasks, declared resource overlays, and out-of-fragment instances stay
separate. Schema/model limits are recorded as exclusions, never solved failures.
"""
from hashlib import sha256
from pathlib import Path
import json,tarfile,urllib.request
from scar_public.benchmark_suite import CPOR_COMMIT
from scar_public.contingent_benchmarks import SOURCE,ARCHIVE_SHA,sexpr
from scar_public.symbolic_task import SymbolicTask


PROJECTIONS={'blocks':('clear',),'unix':('is_cur_dir',),
    'logistics':('at_tl','at_ta','at_aa'),'medpks':(),
    'grid':('at-robot','holding','arm-empty'),
    'colorballs':(),'wumpus':(),'doors':('at',),'localize':('ok',)}


def configurations():
    cases=[]
    def add(family,instance,domain,problem,source='cff'):
        cases.append(dict(id=f'new_{source}_{family}_{instance}',family=family,instance=instance,
            domain=domain,problem=problem,source=source,horizon=60,sensor_budget=None,
            actuation_budget=None,cohort='new_public_original',projection_predicates=PROJECTIONS[family]))
    for n in (3,7,11,15):add('blocks',str(n),'blocks/domain.pddl',f'blocks/p{n}.pddl')
    for n in (1,2,3,4):add('unix',str(n),'unix/domain.pddl',f'unix/unix-p{n}.pddl')
    for n in (1,3,5,7):add('logistics',str(n),'logistics/domain.pddl',f'logistics/pfile{n}')
    for n in (10,30,50,70):add('medpks',str(n),f'medpks/d{n}.pddl',f'medpks/p{n}.pddl')
    for n in (2,3,4,5):add('grid',str(n),'grid/domain.pddl',f'grid/p{n}.pddl')
    for family,folder in [('blocks','blocks2'),('blocks','blocks3'),('colorballs','colorballs2-2'),
        ('wumpus','wumpus05'),('doors','doors15'),('localize','localize5noisy')]:
        add(family,folder,f'Tests/{folder}/d.pddl',f'Tests/{folder}/p.pddl','cpor')
    originals=list(cases)
    for c in originals:
        # Eight fixed overlays, not selected on solver success or model count.
        if c['source']=='cff' and (c['family'],c['instance']) in (
            ('blocks','3'),('unix','2'),('logistics','3'),('medpks','10')):
            for sensors in (0,2):
                cases.append(dict(c,id=c['id']+f'_sensor{sensors}',sensor_budget=sensors,
                    actuation_budget=60,cohort='new_declared_resource_extension'))
    return cases


def source_text(cache,config):
    cache=Path(cache);paths=[config['domain'],config['problem']]
    if config['source']=='cff':
        archive=cache/'contff-tests.tgz';assert sha256(archive.read_bytes()).hexdigest()==ARCHIVE_SHA
        with tarfile.open(archive) as t:blobs=[t.extractfile('contff-tests/'+p).read() for p in paths]
        origin=dict(url=SOURCE,archive_sha256=ARCHIVE_SHA,members=paths)
    else:
        blobs=[(cache/p.replace('/','_')).read_bytes() for p in paths]
        origin=dict(repository='https://github.com/aiplan4eu/up-cpor',commit=CPOR_COMMIT,paths=paths)
    origin['content_sha256']=[sha256(b).hexdigest() for b in blobs]
    return *(b.decode() for b in blobs),origin


def reject_unsupported(domain,problem):
    def visit(x):
        if not isinstance(x,list):return
        if x and isinstance(x[0],str) and x[0] in ('nondet','probabilistic','forall','exists','increase','decrease'):
            raise ValueError('unsupported source construct '+x[0])
        for y in x:visit(y)
    visit(sexpr(domain));visit(sexpr(problem))


def load_case(cache,c):
    d,p,origin=source_text(cache,c);reject_unsupported(d,p)
    resources=();costs={}
    if c['sensor_budget'] is not None:
        resources=(c['actuation_budget'],c['sensor_budget'])
        for s in sexpr(d):
            if isinstance(s,list) and s and s[0]==':action':
                fields=dict(zip(s[2::2],s[3::2]));costs[s[1]]=(0,1) if ':observe' in fields else (1,0)
    task=SymbolicTask(d,p,resources=resources,resource_costs=costs,
        projection_predicates=c['projection_predicates'],model_limit=256,ground_limit=20000)
    return task,origin


def fetch(cache):
    cache=Path(cache);cache.mkdir(parents=True,exist_ok=True);records=[]
    for c in configurations():
        if c['source']!='cpor':continue
        for p in (c['domain'],c['problem']):
            path=cache/p.replace('/','_')
            if not path.exists():path.write_bytes(urllib.request.urlopen(
                f'https://raw.githubusercontent.com/aiplan4eu/up-cpor/{CPOR_COMMIT}/{p}',timeout=30).read())
            records.append(dict(path=p,sha256=sha256(path.read_bytes()).hexdigest()))
    return records


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,required=True);a=p.parse_args()
    print(json.dumps(fetch(a.cache),indent=2))
