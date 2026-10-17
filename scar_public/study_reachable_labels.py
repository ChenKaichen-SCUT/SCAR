"""Development evaluation of labelled dynamic reachability; not a holdout."""
import argparse, json, os, platform, subprocess, sys, threading
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from scar_public import study_information_gaps as worker_api, label_scale_suite, benchmark_suite
from scar_public.compiled_task import CompiledTask
from scar_public.contingent_benchmarks import sexpr
from scar_public.decision_coverage import DecisionPlanner
from scar_public.incremental_channels import IncrementalCoverage
from scar_public.reachable_labels import ReachablePlanner
from scar_public.progress_carrier import CarrierPlanner
from scar_public.amortized_refinement import AmortizedPlanner
from scar_public.resource_information import resource_planner

MODES = ('fixed_count', 'fixed_relation', 'reachable_count', 'reachable_relation', 'resource_tree')


def configurations():
    rows = []
    for family, n in (('ring', 4), ('cubecenter', 3), ('btc', 8), ('medicalPKS', 4)):
        rows.append(dict(id=f'lug_{family}_{n}_a16s1', family=family, n=n, overlay='a16s1',
            horizon=60, source='lug', cohort='development'))
    for n in (4, 6, 8):
        rows.append(dict(id=f'rovers_{n}_a16s1', family='rovers', instance=f'pfile{n}',
            horizon=32, resources=[16, 1], source='cff', cohort='development'))
    for s in (2, 4):
        rows.append(dict(id=f'localize_5_a16s{s}', family='localize', instance='5',
            horizon=60, resources=[16, s], source='cpor', cohort='development'))
    return rows


def load(cache, c):
    if c['source'] == 'lug':
        return label_scale_suite.load(cache, c)
    d, p, origin = benchmark_suite.source_text(cache, c['family'], c['instance'])
    costs = {}
    for a in sexpr(d):
        if isinstance(a, list) and a and a[0] == ':action':
            costs[a[1]] = (0, 1) if ':observe' in a else (1, 0)
    return CompiledTask(d, p, resources=tuple(c['resources']), resource_costs=costs,
        projection_predicates=benchmark_suite.PROJECTIONS[c['family']], model_limit=2048, ground_limit=20000), origin


def planner(task, mode):
    if mode.startswith('sparse_'):
        from scar_public.sparse_policy import SparsePolicyPlanner
        return SparsePolicyPlanner(task, mode)
    if mode.startswith('factored_'):
        from scar_public.factored_progress import FactoredPlanner
        return FactoredPlanner(task, mode)
    if mode.startswith('compact_'):
        from scar_public.compact_progress import CompactPlanner
        return CompactPlanner(task, mode)
    if mode.startswith('amortized_'):
        return AmortizedPlanner(task, mode)
    if mode.startswith('carrier_'):
        return CarrierPlanner(task, mode)
    if mode.startswith('reachable_'):
        return ReachablePlanner(task, mode)
    if mode == 'resource_tree':
        return resource_planner(task)
    if mode == 'leaf':
        return DecisionPlanner(task, 'leaf')
    p = DecisionPlanner(task, 'count_threshold' if mode == 'fixed_count' else 'relation_threshold')
    p.target_coverage = IncrementalCoverage(task)
    return p


def main():
    p = argparse.ArgumentParser(); p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True); p.add_argument('--worker')
    p.add_argument('--mode'); p.add_argument('--cpu', type=int); p.add_argument('--freeze', action='store_true')
    p.add_argument('--seconds', type=int, default=30); p.add_argument('--suite', default='development')
    p.add_argument('--modes', nargs='+', default=MODES)
    a = p.parse_args()
    provenance = None
    if a.suite in ('compact_scale', 'reused_scale'):
        from scar_public.compact_scale_suite import configurations as scale_cases, load as scale_load, provenance as scale_provenance
        configs, loader = scale_cases(), scale_load
        if a.suite == 'reused_scale':
            configs = [dict(c, cohort='reused_scale_development') for c in configs]
        if not a.worker:
            provenance = {c['id']: scale_provenance(a.cache, c) for c in configs}
    elif a.suite in ('holdout', 'reused_author'):
        from scar_public.reachable_holdout import configurations as heldout_cases, load as heldout_load
        from scar_public.reachable_holdout import provenance as source_provenance
        configs, loader = heldout_cases(), heldout_load
        if a.suite == 'reused_author':
            configs = [dict(c, cohort='reused_validation_now_development') for c in configs]
        if not a.worker:
            provenance = {c['id']: source_provenance(a.cache, c) for c in configs}
    else:
        configs, loader = configurations(), load
    if a.worker:
        worker_api.load = loader; worker_api.BudgetedPlanner = planner
        return worker_api.worker(a)
    a.output.mkdir(parents=True, exist_ok=True)
    sources = {x.name: sha256(x.read_bytes()).hexdigest() for x in sorted(Path(__file__).parent.glob('*.py'))}
    modes = tuple(a.modes)
    spec = dict(cases=configs, modes=modes, seconds=a.seconds, memory_mib=2048,
        repetitions=1, api_calls=0, sources=sources, suite=a.suite, provenance=provenance,
        protocol='Identical exact search and common projection. Auxiliary reachability patterns add no observations. '
        'Both capacity variants have identical channel definitions. Optional work has a soft 3s/run budget. '
        'Default queries have .25s; *_continue modes may extend a completed-scalar, deficient-witness relation query '
        'to the remaining run budget. An atomic SAT call can overrun. '
        'All preprocessing included; unfinished pattern discarded; completed patterns reported. '
        'Compare relation-specific gains only when completed pattern sets agree. All finite policies replayed. '
        'Development inputs have been inspected previously; no independence claim. '
        'Holdout inputs are selected by unused author filenames after structural duplicate audit and before outcomes; related generator family, '
        'not independent statistical draws. All returned plans replayed; bounded NO only, not global impossibility.')
    mp = a.output/'manifest.json'
    if mp.exists():
        assert json.loads(mp.read_text()) == json.loads(json.dumps(spec)), 'Frozen source/config mismatch'
    else:
        mp.write_text(json.dumps(spec, indent=2))
    if a.freeze:
        print(json.dumps(dict(cases=len(configs), modes=len(modes), manifest_sha256=sha256(mp.read_bytes()).hexdigest())))
        return
    cpus = []; cores = set()
    for cpu in sorted(os.sched_getaffinity(0)):
        path = Path(f'/sys/devices/system/cpu/cpu{cpu}/topology')
        core = ((path/'physical_package_id').read_text(), (path/'core_id').read_text())
        if core not in cores:
            cores.add(core); cpus.append(cpu)
    cpus = cpus[:8]; log = a.output/'runs.jsonl'
    rows = [json.loads(x) for x in log.read_text().splitlines()] if log.exists() else []
    seen = {(r['config']['id'], r['mode']) for r in rows}; jobs = []
    for i, c in enumerate(configs):
        k = i % len(modes)
        jobs.extend((c, m) for m in modes[k:]+modes[:k] if (c['id'], m) not in seen)
    lock = threading.Lock()
    def lane(i):
        for c, m in jobs[i::len(cpus)]:
            cmd = [sys.executable, '-u', '-m', 'scar_public.study_reachable_labels', '--cache', str(a.cache),
                '--output', str(a.output), '--worker', json.dumps(c), '--mode', m, '--cpu', str(cpus[i]), '--suite', a.suite]
            start = perf_counter()
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, env=dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1'))
            ready = proc.stdout.readline(); startup = perf_counter()-start
            if not ready:
                raise RuntimeError(proc.stderr.read())
            assert json.loads(ready)['phase'] == 'ready'
            timeout = killed = False
            try:
                out, err = proc.communicate('go\n', timeout=a.seconds)
            except subprocess.TimeoutExpired:
                timeout = True; proc.terminate()
                try:
                    out, err = proc.communicate(timeout=2)
                except subprocess.TimeoutExpired:
                    killed = True; proc.kill(); out, err = proc.communicate()
            phases = [json.loads(x) for x in out.splitlines() if x.strip()]
            row = dict(config=c, mode=m, cpu=cpus[i], startup_seconds=startup,
                wall_seconds=perf_counter()-start, timed_out=timeout, hard_killed=killed,
                phases=phases, status='UNKNOWN_PROCESS_ERROR')
            for x in phases:
                row.update({k: v for k, v in x.items() if k != 'phase'})
            if timeout:
                row['status'] = 'UNKNOWN_TIMEOUT'
            elif proc.returncode:
                row.update(status='UNKNOWN_PROCESS_ERROR', error=err[-3000:])
            with lock:
                with log.open('a') as f:
                    f.write(json.dumps(row)+'\n')
            print(json.dumps(dict(id=c['id'], mode=m, status=row['status'], seconds=row.get('total_seconds'))), flush=True)
    with ThreadPoolExecutor(max_workers=len(cpus)) as pool:
        list(pool.map(lane, range(len(cpus))))
    (a.output/'environment.json').write_text(json.dumps(dict(python=platform.python_version(),
        platform=platform.platform(), cpus=cpus, api_calls=0), indent=2))


if __name__ == '__main__':
    main()
