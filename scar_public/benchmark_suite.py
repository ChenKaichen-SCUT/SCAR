"""Pinned heterogeneous source tasks; resource overlays are explicitly separate."""
from hashlib import sha256
import json
from pathlib import Path
import tarfile

from scar_public.contingent_benchmarks import SOURCE,ARCHIVE_SHA,sexpr
from scar_public.symbolic_task import SymbolicTask

CPOR_COMMIT='4776479597e33610f68dcc20613850f414eb6688'
PROJECTIONS={'bts':(), 'btcs':('clog',), 'medical':('dead',), 'doors':('at',), 'localize':('ok',),
    'rovers':('at','calibrated','communicated_soil_data','communicated_rock_data','communicated_image_data')}


def source_text(cache,family,instance):
    cache=Path(cache)
    if family in ('doors','localize'):
        paths=[cache/f'Tests_{family}5_{suffix}.pddl' for suffix in ('d','p')]
        blobs=[p.read_bytes() for p in paths]
        origin=dict(repository='https://github.com/aiplan4eu/up-cpor',commit=CPOR_COMMIT,
            paths=[f'Tests/{family}5/{suffix}.pddl' for suffix in ('d','p')])
    else:
        archive=cache/'contff-tests.tgz'
        assert sha256(archive.read_bytes()).hexdigest()==ARCHIVE_SHA
        members=[f'contff-tests/{family}/{name}' for name in ('domain.pddl',instance)]
        with tarfile.open(archive) as t:blobs=[t.extractfile(name).read() for name in members]
        origin=dict(url=SOURCE,archive_sha256=ARCHIVE_SHA,members=members)
    origin['content_sha256']=[sha256(b).hexdigest() for b in blobs]
    return *(b.decode() for b in blobs),origin


def configurations():
    cases=[]
    def add(family,instance,horizon,sensors=None):
        cases.append(dict(id=f'{family}_{instance}_s{sensors}',family=family,instance=instance,
            horizon=horizon,sensor_budget=sensors,actuation_budget=horizon if sensors is not None else None,
            cohort='original' if sensors is None else 'declared_resource_extension',
            projection_predicates=PROJECTIONS[family]))
    for f in ('bts','btcs'):
        for n in (10,30,50,70):add(f,f'pfile{n:03d}',n)
    for n in (2,3,4,5):add('medical',f'pfile{n:03d}',10)
    add('doors','5',40);add('localize','5',60)
    for n in (2,4,6,8):add('rovers',f'pfile{n}',32)
    for f,i,h in [('medical','pfile005',10),('doors','5',40),('localize','5',60),('rovers','pfile2',32)]:
        for s in (0,1,2,4):add(f,i,h,s)
    return cases


def load_case(cache,config):
    domain,problem,origin=source_text(cache,config['family'],config['instance'])
    costs={};resources=()
    if config['sensor_budget'] is not None:
        resources=(config['actuation_budget'],config['sensor_budget'])
        for schema in sexpr(domain):
            if isinstance(schema,list) and schema and schema[0]==':action':
                fields=dict(zip(schema[2::2],schema[3::2]))
                costs[schema[1]]=(0,1) if ':observe' in fields else (1,0)
    task=SymbolicTask(domain,problem,resources=resources,resource_costs=costs,
        projection_predicates=config['projection_predicates'])
    return task,origin


def freeze(cache,output):
    cases=configurations()
    result=dict(version=1,cases=cases,modes=['single','pair_exact','symbolic','resource_blind','explicit_channels'],
        published_planners=['Contingent-FF author binary, -a 0 -m 1 -h 2',
                            'Contingent-FF author binary, -a 0 -m 1 -h 3'],
        external_scope='Unmodified original source tasks only. Replay all returned finite policies. '
            'Report verified worst-case depth and bounded feasibility, without assuming optimality.',
        work_limit_seconds=15,external_limit_seconds=15,memory_limit_mib=2048,repetitions=1,
        original_configurations=18,resource_extensions=16,
        overlay='Every non-observing action consumes one actuation unit; each Boolean observation '
                'consumes one sensor unit. These budget overlays are NOT original benchmark constraints.',
        projection_selection='Fixed schema predicates, no solution or performance feedback. Common current '
                'projection is checked at query time. Static facts remain model-specific constraints.',
        source_provenance={c['id']:source_text(cache,c['family'],c['instance'])[2] for c in cases},
        timing='Isolated processes, fixed CPU affinity when available; all construction/search timed. '
               'Worker module import separately reported. One run, no significance claims.')
    path=Path(output);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():assert json.loads(path.read_text())==json.loads(json.dumps(result))
    else:path.write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result
