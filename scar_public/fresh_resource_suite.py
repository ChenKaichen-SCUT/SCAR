"""Public files selected by family and size before running the frozen study.

No published plans, results or deadend annotations are used. The strong-goal
objective is explicit: it differs from planners that permit terminating in a
recognized dead end. Declared action/sensor overlays are not source constraints.
"""
from pathlib import Path
from hashlib import sha256
import zipfile
from scar_public.compiled_task import CompiledTask
from scar_public.contingent_benchmarks import sexpr
from scar_public.holdout_suite import reject_unsupported
from scar_public.search_public_separations import load as old_load
from scar_public.benchmark_suite import PROJECTIONS

URL = 'https://raw.githubusercontent.com/shanigu/ContingentPlanning/9ce9a55dc74d021cb10bed73681ee4eb3f9d101a/DeadendDomains.zip'
ARCHIVE_SHA = '3afa4923397f97714ccc7ee2fe6f95aaa49341bce780e520004cb088d036fc5c'


def configurations():
    sources = []
    for f in ('Sokoban-4-2-1-1-0','Sokoban-4-2-1-1-2','Sokoban-5-2-1-1-6','Sokoban-5-2-1-1-8',
              'Sokoban-6-2-1-1-10','Sokoban-6-2-1-1-12','Sokoban-7-2-1-1-16','Sokoban-7-2-1-1-18'):
        sources.append((f,'sokoban',('at',)))
    for n in (5,7,9,11):
        sources.append((f'Doors&{n}&3','doors',('at',)))
    for n in (4,5,6):
        sources.append((f'Boxes{n}_2','boxes',()))
    for n in (1,2,3):
        sources.append((f'Cavediving-4-3-2-{n}-0','cavediving',('at','quantity')))
    for n in (1,2,3):
        sources.append((f'woodworking{n:02d}','woodworking',('available','boardsize')))
    result = [dict(id=f+'_'+label,folder=f,family=fam,projection_predicates=proj,
        source='fresh',cohort='fresh_public_original' if a is None else 'fresh_resource_extension',
        actuation=a,sensors=s,horizon=60)
        for f,fam,proj in sources for label,a,s in [('original',None,None),('a16s1',16,1)]]
    for n in (2,4,6,8):
        for label,a,s in [('original',None,None),('a16s1',16,1)]:
            result.append(dict(id=f'rover{n}_{label}',family='rovers',instance=f'pfile{n}',
                projection_predicates=PROJECTIONS['rovers'],source='development',source_kind='benchmark',
                cohort='observed_rover_scale',overlay=label,actuation=a,sensors=s,horizon=16))
    return result


def source_text(cache, config):
    archive = Path(cache)/'DeadendDomains.zip'
    assert sha256(archive.read_bytes()).hexdigest() == ARCHIVE_SHA
    members = [config['folder']+'/'+n+'.pddl' for n in ('d','p')]
    with zipfile.ZipFile(archive) as z:
        blobs = [z.read(n) for n in members]
    return *(b.decode('utf-8-sig') for b in blobs),dict(url=URL,archive_sha256=ARCHIVE_SHA,
        members=members,content_sha256=[sha256(b).hexdigest() for b in blobs])


def load(cache,config):
    if config['source']=='development':
        return old_load(cache,config)
    domain,problem,origin = source_text(cache,config)
    reject_unsupported(domain,problem)
    resources,costs = (),{}
    if config['actuation'] is not None:
        resources = (config['actuation'],config['sensors'])
        for a in sexpr(domain):
            if isinstance(a,list) and a and a[0]==':action':
                fields = dict(zip(a[2::2],a[3::2]))
                costs[a[1]] = (0,1) if ':observe' in fields else (1,0)
    task = CompiledTask(domain,problem,resources=resources,resource_costs=costs,
        projection_predicates=config['projection_predicates'],model_limit=256,ground_limit=20000)
    return task,origin
