"""Development-only probes of relation queries interrupted after scalar success.

Run the real bounded planner once, save up to eight such queries in encounter
order, then resume them outside search with a separate shared 10 second budget.
Probe costs never contribute to reported production speedups. No real plan is
inferred from an optimistic abstract support witness.
"""
import argparse
import json
from pathlib import Path
from time import perf_counter
from scar_public.compact_progress import CompactPlanner, names
from scar_public.budgeted_planner import InferenceStop
from scar_public.symbolic_coverage import Unavailable
from scar_public.study_reachable_labels import configurations, load


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('cache', type=Path)
    parser.add_argument('output', type=Path); args = parser.parse_args()
    config = next(c for c in configurations() if c['id'] == 'lug_ring_4_a16s1')
    task, origin = load(args.cache, config)
    planner = CompactPlanner(task); coverage = planner.target_coverage
    decide = coverage.decide; pending = []
    def capture(belief, budget, mode):
        try:
            return decide(belief, budget, mode)
        except (InferenceStop, Unavailable):
            key = coverage.carrier(belief)
            if key is not None:
                memo = coverage.canonical(key, budget), budget, 'counts'
                count = coverage.compact_cache.get(memo)
                if count is not None and count >= names(key[1]).bit_count() and len(pending) < 8:
                    pending.append((key, budget, count))
            raise
    coverage.decide = capture
    started = perf_counter(); result = planner.solve(task.belief, config['horizon'])
    runtime = perf_counter()-started; production = planner.statistics()
    if result.upper < float('inf'):
        assert planner.verify(task.belief, config['horizon'], result.policy) == result.upper
    end = perf_counter()+10.; records = []
    for key, budget, count in pending:
        start = perf_counter()
        if start >= end:
            records.append(dict(status='not_started_total_budget', budget=budget)); continue
        coverage.deadline = min(end, start+2.)
        row = dict(budget=budget, candidates=names(key[1]).bit_count(), scalar=count,
            resources=key[0], groups=key[1])
        try:
            row['lineage'] = coverage.value(key, budget, True)
            row['matching'] = coverage.value(key, budget, 'matching')
            row['status'] = 'completed'
        except (InferenceStop, Unavailable):
            row['status'] = 'interrupted'
        row['seconds'] = perf_counter()-start; records.append(row)
    args.output.write_text(json.dumps(dict(config=config, origin=origin,
        production_seconds=runtime, production_statistics=production, probes=records,
        scope='Development diagnostic, not a benchmark timing or held-out result.'), indent=2))
    print(json.dumps([dict(status=r['status'], budget=r['budget'], scalar=r.get('scalar'),
        lineage=r.get('lineage'), matching=r.get('matching'), seconds=r.get('seconds')) for r in records]))


if __name__ == '__main__':
    main()
