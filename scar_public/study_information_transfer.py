"""Extension study with frozen heuristics, exact solutions and negative results."""
import argparse
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
from statistics import median
from time import perf_counter

from scar_public.finite_planner import printable
from scar_public.information_bound import InformationBoundPlanner
from scar_public.information_instances import workshop
from scar_public.information_reference import independent_oracle
from scar_public.information_transfer import production_grid, bridge_grid
from scar_public.study_information_bound import measure, numeric, summarize


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repetitions', type=int, default=3)
    parser.add_argument('--output', type=Path, default=Path(__file__).parent /
                        'results/2026-10-16-information-transfer/analysis.json')
    args = parser.parse_args()
    assert args.repetitions > 0
    measure(workshop(scan_steps=1, horizon=2), 'lp')
    rows, started = [], perf_counter()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    for generator in (production_grid, bridge_grid):
        iterator = iter(generator())
        while True:
            t = perf_counter()
            try:
                instance = next(iterator)
            except StopIteration:
                break
            compile_seconds = perf_counter() - t
            t = perf_counter()
            oracle = independent_oracle(instance)
            truth = oracle(instance.belief, instance.horizon)
            oracle_seconds = perf_counter() - t
            samples, modes = defaultdict(list), list(InformationBoundPlanner.MODES)
            for repeat in range(args.repetitions):
                offset = (len(rows) + repeat) % len(modes)
                for mode in modes[offset:] + modes[:offset]:
                    result = measure(instance, mode)
                    assert numeric(result['root_lower']) <= truth, (instance.name, mode, result, truth)
                    assert numeric(result['optimum']) == truth, (instance.name, mode, result, truth)
                    samples[mode].append(result)
            measurements = {}
            for mode, runs in samples.items():
                assert all(r['statistics'] == runs[0]['statistics'] for r in runs)
                med = median(r['seconds'] for r in runs)
                measurements[mode] = dict(runs[0], median_seconds=med,
                    end_to_end_seconds=compile_seconds + med,
                    timing_samples_seconds=[r['seconds'] for r in runs])
            for base, variant in (('lp','capacity_lp'),('single','capacity_single'),
                                  ('lp','pair_lp'),('single','pair_exact')):
                assert numeric(measurements[base]['root_lower']) <= numeric(measurements[variant]['root_lower'])
            rows.append(dict(name=instance.name, family=instance.family, config=instance.metadata,
                             optimum=printable(truth), compile_seconds=compile_seconds,
                             oracle_seconds=oracle_seconds, oracle_subproblems=oracle.cache_info().currsize,
                             measurements=measurements))
            oracle.cache_clear()
            args.output.with_suffix('.partial.json').write_text(json.dumps(rows, ensure_ascii=False), encoding='utf-8')
            print(json.dumps({'completed':len(rows), 'name':instance.name, 'optimum':printable(truth),
                  'root':{m:x['root_lower'] for m,x in measurements.items()},
                  'lp_seconds':measurements['lp']['median_seconds'],
                  'capacity_lp_seconds':measurements['capacity_lp']['median_seconds']}, ensure_ascii=False), flush=True)
    result = dict(date='2026-10-16', api_calls=0, game_actions=0, timing_repetitions=args.repetitions,
        scope='Finite extended production instances and synthetic specs in the unchanged V8 resource model; '
              'not full-game or real-workflow performance.',
        method_changes='None: finite_planner, information_bound, observation_capacity unchanged.',
        protocol='Fresh planner caches, rotated variant order, three engineering timing repetitions; '
                 'construction and bound work included; common model compilation separately reported and '
                 'also added to end_to_end_seconds; reference enumeration and replay excluded equally.',
        summary=summarize(rows), cases=rows, wall_seconds=perf_counter()-started)
    for family, summary in result['summary']['families'].items():
        cases = [r for r in rows if r['family'] == family]
        summary['compile_seconds'] = sum(r['compile_seconds'] for r in cases)
        for mode, stats in summary['modes'].items():
            stats['end_to_end_seconds'] = stats['total_seconds'] + summary['compile_seconds']
            stats['capacity_disabled'] = sum(bool((r['measurements'][mode]['statistics']['coverage'] or {})
                                                   .get('disabled_reason')) for r in cases)
            stats['root_stricter_than_lp'] = sum(numeric(r['measurements'][mode]['root_lower']) >
                                                  numeric(r['measurements']['lp']['root_lower']) for r in cases)
    source_names = ('information_transfer.py', 'study_information_transfer.py', 'study_information_bound.py',
                    'information_bound.py', 'observation_capacity.py', 'information_reference.py',
                    'finite_planner.py', 'resource_competition.py')
    result['source_sha256'] = {n:sha256(Path(__file__).with_name(n).read_bytes()).hexdigest() for n in source_names}
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result['summary'], ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
