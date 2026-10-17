"""Unused author Rover tasks after structural duplicate audit, before outcomes.

Author files 4 and 6 duplicate existing CFF tasks under the compiled transition
signature; file 1 is single-world. Keep 2,3,5 (2,3,16 candidates), both original
and declared a16s1 budgets. Same generator family, not statistical independence.
"""
import tarfile
from hashlib import sha256
from scar_public.benchmark_suite import PROJECTIONS
from scar_public.label_scale_suite import ARCHIVE, SHA, URL, normalize
from scar_public.compiled_task import CompiledTask
from scar_public.contingent_benchmarks import sexpr


def configurations():
    return [dict(id=f'author_rovers_{n}_{overlay}', family='rovers', instance=f'pfile{n}',
        horizon=32, overlay=overlay, source='lug_author_archive', cohort='unseen_filename_related_family')
        for n in (2, 3, 5) for overlay in ('original', 'a16s1')]


def source(cache, c):
    path = cache/ARCHIVE
    assert sha256(path.read_bytes()).hexdigest() == SHA
    base = 'BKS_jair_domains/pond/conditional/rovers/'
    members = [base+'domain.pddl', base+c['instance']]
    with tarfile.open(path) as t:
        blobs = [t.extractfile(n).read() for n in members]
    d, p, notes = normalize(*(b.decode() for b in blobs))
    dn = next(x[1] for x in sexpr(d) if isinstance(x, list) and x[0] == 'domain')
    pn = next(x[1] for x in sexpr(p) if isinstance(x, list) and x[0] == ':domain')
    return d, p, dict(url=URL, archive_sha256=SHA, members=members,
        content_sha256=[sha256(b).hexdigest() for b in blobs], conversions=notes,
        domain_declaration=dn, problem_domain_declaration=pn, domain_declarations_match=dn == pn)


def provenance(cache, c):
    return source(cache, c)[2]


def load(cache, c):
    d, p, origin = source(cache, c); costs = {}
    if c['overlay'] == 'a16s1':
        for a in sexpr(d):
            if isinstance(a, list) and a and a[0] == ':action':
                costs[a[1]] = (0, 1) if ':observe' in a else (1, 0)
    return CompiledTask(d, p, resources=(16, 1) if costs else (), resource_costs=costs,
        projection_predicates=PROJECTIONS['rovers'], model_limit=2048, ground_limit=20000), origin
