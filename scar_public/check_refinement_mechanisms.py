"""Post-hoc mechanism checks, explicitly NOT a second performance sample."""
import argparse, json
from pathlib import Path
from time import perf_counter
from scar_public.coverage_separation import make
from scar_public.certificate_refinement import RefinementCoverage, RefinementPlanner
from scar_public.direct_saturation import SaturationCoverage
from scar_public.budgeted_planner import InferenceStop
from scar_public.symbolic_coverage import Unavailable
from scar_public.information_controls import InformationControls
from scar_public.decision_coverage import DecisionCoverage
from scar_public.compiled_task import CompiledTask
from scar_public import holdout_suite


def synthetic():
    rows = []
    for n in (3, 4, 8, 16):
        for budget in (2, 3):
            task = make(n, budget)
            end = next(i for i, a in enumerate(task.atom_names) if a == ('end',))
            task.projection = tuple(i for i in task.projection if i != end)
            task.projection_mask &= ~(1 << end)
            old = SaturationCoverage(task)
            assert old.direct_saturation(task.belief, 3)
            bound = RefinementCoverage(task)
            started = perf_counter(); prune, e = bound.decide(task.belief, 3)
            seconds = perf_counter()-started
            assert prune == (budget == 2)
            assert e['scalar'] == n
            assert e['identity_capacity'] == n-(budget == 2)
            assert e['refinement']['added_atoms'] == [('end',)]
            control = InformationControls(task, work_limit=1000000)
            leaf = control.leaf_lower(task.belief, 3)
            pair = control.pair_lower(task.belief, 3)
            assert leaf == 0 and pair <= 3
            rows.append(dict(models=n, resources=budget, old_identity_capacity=n,
                prune=prune, evidence=e, seconds=seconds, leaf=leaf, pair=pair,
                stats=bound.stats))
    return rows


def public(cache, ids):
    holdout_suite.SymbolicTask = CompiledTask
    rows = []
    for config in holdout_suite.configurations():
        if config['id'] not in ids:
            continue
        task, origin = holdout_suite.load_case(cache, config)
        planner = RefinementPlanner(task); captured = []
        original = planner.target_coverage.decide
        def capture(belief, budget, mode):
            prune, evidence = original(belief, budget, mode)
            if 'added_atoms' in evidence.get('refinement', {}):
                captured.append((belief, budget, evidence))
            return prune, evidence
        planner.target_coverage.decide = capture
        answer = planner.solve(task.belief, config['horizon'])
        assert answer.exact and answer.upper < float('inf')
        assert planner.verify(task.belief, config['horizon'], answer.policy) == answer.upper
        # One representative per reason, selected projection, threshold and
        # live count. Select prunes before passes, at most 8 fixed queries/task.
        seen = set(); queries = []
        for belief, d, e in sorted(captured, key=lambda x: ('prune' not in x[2]['reason'])):
            key = e['reason'], repr(e['refinement']['added_atoms']), d, e['candidates']
            if key in seen or len(queries) >= 8:
                continue
            seen.add(key)
            old = SaturationCoverage(task)
            assert old.direct_saturation(belief, d)
            values = {}
            for selection in ('certificate', 'goal_first'):
                b = RefinementCoverage(task, selection)
                started = perf_counter(); b.deadline = started+1.
                try:
                    prune, result = b.decide(belief, d)
                    values[selection] = dict(status='completed', prune=prune, result=result)
                except (InferenceStop, Unavailable):
                    values[selection] = dict(status='unknown')
                values[selection].update(seconds=perf_counter()-started, stats=b.stats)
            queries.append(dict(budget=d, original_saturation=True,
                original_identity_capacity=e['candidates'], selection_evidence=e,
                belief=[dict(name=n, bits=s.symbols[0], valid=s.symbols[1],
                    resources=s.resources) for n,s in sorted(belief, key=lambda x:x[0])],
                methods=values))
        rows.append(dict(config=config, origin=origin, query_count=len(queries), queries=queries,
            diagnostic_policy_depth=answer.upper))
    return rows


def main():
    p = argparse.ArgumentParser(); p.add_argument('--cache', type=Path)
    p.add_argument('--output', type=Path, required=True); a = p.parse_args()
    result = dict(synthetic=synthetic(), public=public(a.cache,
        {'new_cff_grid_2', 'new_cff_logistics_3'}) if a.cache else [],
        scope='Synthetic structure check plus post-hoc fixed-query diagnostics from two observed pruning cases. '
            'Not independent validation or an additional timing repetition. Fresh bound objects, 1s/query; '
            'goal-first uses equal atom count and pays the same selection work. No external baseline reruns.',
        api_calls=0)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2))
    print(json.dumps(dict(synthetic=len(result['synthetic']),
        public_queries=sum(x['query_count'] for x in result['public']))))


if __name__ == '__main__':
    main()
