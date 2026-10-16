"""Run the fixed offline grid: python -m scar_public.study_information_bound.

Timings include cold planner construction, bound computation, and exact search;
shared domain compilation and independent oracle evaluation are reported apart.
Repeated timings are engineering measurements, not independent task runs.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from hashlib import sha256
import json
from math import inf, isfinite
from pathlib import Path
from statistics import median
import sys
from time import perf_counter

import numpy as np
import scipy

from scar_public.finite_planner import printable
from scar_public.information_bound import InformationBoundPlanner
from scar_public.information_instances import study_grid, workshop
from scar_public.information_reference import independent_oracle


def measure(case, mode):
    started = perf_counter()
    p = InformationBoundPlanner(case.models, case.goal, case.allowed, mode=mode)
    constructed = perf_counter()
    root = p.initial(case.belief, case.horizon).lower
    bounded = perf_counter()
    root_stats = p.statistics()
    answer = p.solve(case.belief, case.horizon)
    finished = perf_counter()
    assert answer.exact
    if isfinite(answer.upper):
        assert p.verify(case.belief, case.horizon, answer.policy) == answer.upper
    return {'mode': mode, 'root_lower': printable(root), 'optimum': printable(answer.upper),
            'seconds': finished - started, 'construct_seconds': constructed - started,
            'root_bound_seconds': bounded - constructed, 'search_seconds': finished - bounded,
            'root_statistics': root_stats, 'statistics': p.statistics()}


def numeric(value):
    if value == 'infinity':
        return inf
    from fractions import Fraction
    return Fraction(value)


def summarize(rows):
    modes = InformationBoundPlanner.MODES
    by_family = {}
    for family in sorted({r['family'] for r in rows}):
        subset = [r for r in rows if r['family'] == family]
        by_family[family] = {
            'instances': len(subset),
            'feasible': sum(r['optimum'] != 'infinity' for r in subset),
            'modes': {mode: {
                'total_seconds': sum(r['measurements'][mode]['median_seconds'] for r in subset),
                'search_expanded': sum(r['measurements'][mode]['statistics']['search_expanded'] for r in subset),
                'bound_dp_nodes': sum(r['measurements'][mode]['statistics']['single_nodes'] +
                                      r['measurements'][mode]['statistics']['pair_nodes'] for r in subset),
                'lp_calls': sum(r['measurements'][mode]['statistics']['lp_calls'] for r in subset),
                'root_exact': sum(r['measurements'][mode]['root_lower'] == r['optimum'] for r in subset),
            } for mode in modes}}
    return {
        'instances': len(rows),
        'feasible': sum(r['optimum'] != 'infinity' for r in rows),
        'pair_lp_strictly_above_lp': sum(numeric(r['measurements']['pair_lp']['root_lower']) >
                                        numeric(r['measurements']['lp']['root_lower']) for r in rows),
        'pair_exact_strictly_above_single': sum(numeric(r['measurements']['pair_exact']['root_lower']) >
                                               numeric(r['measurements']['single']['root_lower']) for r in rows),
        'pair_exact_finite_but_joint_infeasible': sum(
            r['optimum'] == 'infinity' and r['measurements']['pair_exact']['root_lower'] != 'infinity'
            for r in rows),
        'capacity_lp_strictly_above_lp': sum(numeric(r['measurements']['capacity_lp']['root_lower']) >
                                            numeric(r['measurements']['lp']['root_lower']) for r in rows),
        'capacity_resolves_pair_missed_infeasibility': sum(
            r['optimum'] == 'infinity' and r['measurements']['pair_exact']['root_lower'] != 'infinity'
            and r['measurements']['capacity_lp']['root_lower'] == 'infinity' for r in rows),
        'families': by_family,
        'modes': {mode: {
            'total_seconds': sum(r['measurements'][mode]['median_seconds'] for r in rows),
            'search_expanded': sum(r['measurements'][mode]['statistics']['search_expanded'] for r in rows),
            'bound_dp_nodes': sum(r['measurements'][mode]['statistics']['single_nodes'] +
                                  r['measurements'][mode]['statistics']['pair_nodes'] for r in rows),
            'lp_calls': sum(r['measurements'][mode]['statistics']['lp_calls'] for r in rows),
            'capacity_dp_nodes': sum((r['measurements'][mode]['statistics']['coverage'] or {}).get('dp_nodes', 0)
                                     for r in rows),
        } for mode in modes}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repetitions', type=int, default=3)
    parser.add_argument('--output', type=Path, default=Path(__file__).parent /
                        'results/2026-10-16-information-bound/analysis.json')
    args = parser.parse_args()
    assert args.repetitions > 0
    # Warm the library once, then use completely fresh planner caches per run.
    measure(workshop(scan_steps=1, horizon=2), 'lp')
    rows = []
    started = perf_counter()
    iterator = iter(study_grid())
    index = 0
    while True:
        t = perf_counter()
        try:
            case = next(iterator)
        except StopIteration:
            break
        compile_seconds = perf_counter() - t
        t = perf_counter()
        oracle = independent_oracle(case)
        truth = oracle(case.belief, case.horizon)
        oracle_seconds = perf_counter() - t
        samples = defaultdict(list)
        modes = list(InformationBoundPlanner.MODES)
        for repeat in range(args.repetitions):
            offset = (index + repeat) % len(modes)
            for mode in modes[offset:] + modes[:offset]:
                row = measure(case, mode)
                assert numeric(row['optimum']) == truth, (case.name, mode, row, truth)
                assert numeric(row['root_lower']) <= truth
                samples[mode].append(row)
        measurements = {}
        for mode, runs in samples.items():
            assert all(r['statistics'] == runs[0]['statistics'] for r in runs)
            measurements[mode] = dict(runs[0], median_seconds=median(r['seconds'] for r in runs),
                                      timing_samples_seconds=[r['seconds'] for r in runs])
        assert numeric(measurements['lp']['root_lower']) <= numeric(measurements['pair_lp']['root_lower'])
        assert numeric(measurements['single']['root_lower']) <= numeric(measurements['pair_exact']['root_lower'])
        assert numeric(measurements['lp']['root_lower']) <= numeric(measurements['capacity_lp']['root_lower'])
        assert numeric(measurements['single']['root_lower']) <= numeric(measurements['capacity_single']['root_lower'])
        rows.append(dict(name=case.name, family=case.family, config=case.metadata,
                         optimum=printable(truth), compile_seconds=compile_seconds,
                         oracle_seconds=oracle_seconds, oracle_subproblems=oracle.cache_info().currsize,
                         measurements=measurements))
        oracle.cache_clear()
        index += 1
        print(json.dumps({'completed': index, 'instance': case.name, 'optimum': printable(truth),
                          'root_bounds': {m: v['root_lower'] for m, v in measurements.items()}},
                         ensure_ascii=False), flush=True)
    source_paths = ('information_bound.py', 'observation_capacity.py', 'information_instances.py',
                    'information_reference.py', 'study_information_bound.py',
                    'test_information_bound.py', 'finite_planner.py')
    result = dict(date='2026-10-16', scope='Controlled finite offline instances; not TTCL scores or novelty evidence.',
                  api_calls=0, random_seeds_used=False, timing_repetitions=args.repetitions,
                  timing_protocol='One SciPy warmup; fresh per-run planner and DP/LP caches; rotated variant order; '
                                  'total includes bound work and exact search; common compilation/oracle separate.',
                  dependencies=dict(python=sys.version.split()[0], numpy=np.__version__, scipy=scipy.__version__),
                  source_sha256={p: sha256(Path(__file__).with_name(p).read_bytes()).hexdigest() for p in source_paths},
                  summary=summarize(rows), cases=rows, wall_seconds=perf_counter() - started)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(result['summary'], ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
