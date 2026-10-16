from itertools import combinations
from math import inf
from scar_public.test_symbolic_coverage import task, case
from scar_public.information_reference import independent_oracle, reachable_contexts
from scar_public.threshold_search import ThresholdPlanner


def exhaustive_validation():
    values = replays = repeated_horizons = 0
    for resources, costs in [((), None),
            ((0, 0), {'make': (1, 0), 'sense': (0, 1), 'flag': (1, 0)}),
            ((1, 0), {'make': (1, 0), 'sense': (0, 1), 'flag': (1, 0)}),
            ((2, 1), {'make': (1, 0), 'sense': (0, 1), 'flag': (1, 0)}),
            ((3, 1), {'make': (1, 0), 'sense': (0, 1), 'flag': (1, 0)})]:
        t = task(resources, costs, ('flag',))
        c = case(t)
        oracle = independent_oracle(c)
        planners = [ThresholdPlanner(t, m) for m in ThresholdPlanner.MODES]
        # Reuse across unrelated beliefs and both increasing/decreasing budgets:
        # catches accidental global-infinity and ancestor-dependent memoization.
        for belief, h in reachable_contexts(c):
            for size in range(1, len(belief) + 1):
                for ws in combinations(belief, size):
                    b = frozenset(ws)
                    for budget in (h, 3, 0, 1):
                        truth = oracle(b, budget)
                        for p in planners:
                            r = p.solve(b, budget)
                            assert r.exact and r.upper == truth
                            values += 1
                            if truth < inf:
                                assert p.verify(b, budget, r.policy) == truth
                                replays += 1
                        repeated_horizons += 1
    return dict(values=values, replays=replays, repeated_horizons=repeated_horizons)


def test_exact_values_and_reusable_decision_cache():
    assert exhaustive_validation()['values'] > 0


def test_interrupted_search_never_claims_infeasibility():
    t = task()
    for mode in ThresholdPlanner.MODES:
        p = ThresholdPlanner(t, mode)
        r = p.solve(t.belief, 3, expansion_budget=0)
        assert r.lower <= 2 and r.upper == inf and r.status == 'UNKNOWN'
        r = p.solve(t.belief, 3)
        assert r.exact and r.upper == 2
        assert p.verify(t.belief, 3, r.policy) == 2


if __name__ == '__main__':
    import argparse,json
    from pathlib import Path
    p = argparse.ArgumentParser()
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    test_interrupted_search_never_claims_infeasibility()
    result = dict(exhaustive_validation(), all_passed=True)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2))
    print(json.dumps(result))
