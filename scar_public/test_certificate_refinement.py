from itertools import combinations
from math import inf
from unittest.mock import patch
import pytest
from scar_public.compiled_task import CompiledTask
from scar_public.test_symbolic_coverage import DOMAIN, PROBLEM, case
from scar_public.information_reference import independent_oracle, reachable_contexts
from scar_public.certificate_refinement import (RefinementCoverage, RefinementPlanner,
    minimum_hitting_set, projection_view)
from scar_public.budgeted_planner import InferenceStop
from scar_public.direct_saturation import SaturationCoverage
from scar_public.coverage_separation import make


def test_minimum_hitting_set_and_interruption():
    for clauses in [(3, 6, 5), (1, 2, 4), (15, 6), (0,), ()]:
        answer = minimum_hitting_set(clauses)
        brute = [mask for mask in range(16) if mask.bit_count() <= 3 and
                 all(mask & clause for clause in clauses)]
        assert (answer is None) == (not brute)
        if answer is not None:
            assert all(answer & c for c in clauses)
            assert answer.bit_count() == min(x.bit_count() for x in brute)
    assert minimum_hitting_set((1, 2, 4, 8)) is None
    with pytest.raises(InferenceStop):
        minimum_hitting_set((3, 6, 5), node_limit=1)


def test_one_progress_atom_restores_joint_resource_obstruction():
    t = make(4)
    end = next(i for i, name in enumerate(t.atom_names) if name == ('end',))
    t.projection = tuple(i for i in t.projection if i != end)
    t.projection_mask &= ~(1 << end)
    old = SaturationCoverage(t)
    assert old.direct_saturation(t.belief, 3)
    b = RefinementCoverage(t)
    prune, evidence = b.decide(t.belief, 3)
    assert prune and evidence['reason'] == 'refined_relation_prune'
    assert evidence['scalar'] == 4 and evidence['identity_capacity'] == 3
    assert evidence['refinement']['added_atoms'] == [('end',)]
    assert not t.projection_mask & (1 << end)
    t3 = make(4, 3)
    t3.projection = tuple(i for i in t3.projection if i != end)
    t3.projection_mask &= ~(1 << end)
    assert not RefinementCoverage(t3).decide(t3.belief, 3)[0]


def validate():
    checks = prunes = replays = selections = 0
    for projection in ((), ('flag',), ('done', 'flag')):
        for resources, costs in [((), None), ((1, 0), {'make': (1, 0), 'sense': (0, 1), 'flag': (1, 0)}),
                ((3, 1), {'make': (1, 0), 'sense': (0, 1), 'flag': (1, 0)})]:
            t = CompiledTask(DOMAIN, PROBLEM, resources=resources,
                resource_costs=costs, projection_predicates=projection)
            original_projection = t.projection, t.projection_mask
            c = case(t); oracle = independent_oracle(c)
            bounds = [RefinementCoverage(t, s) for s in ('certificate', 'goal_first')]
            planners = [RefinementPlanner(t, m) for m in ('refine_certificate', 'refine_goal_first')]
            for belief, h in reachable_contexts(c):
                for size in range(1, len(belief)+1):
                    for ws in combinations(belief, size):
                        sub = frozenset(ws); truth = oracle(sub, h)
                        for bound, planner in zip(bounds, planners):
                            prune, evidence = bound.decide(sub, h)
                            if prune:
                                assert truth == inf
                                prunes += 1
                            selections += int('added_atoms' in evidence.get('refinement', {}))
                            r = planner.solve(sub, h)
                            assert r.exact and r.upper == truth
                            checks += 1
                            if truth < inf:
                                assert planner.verify(sub, h, r.policy) == truth
                                replays += 1
                            assert (t.projection, t.projection_mask) == original_projection
    return dict(oracle_checks=checks, policy_replays=replays, prunes_checked=prunes,
        selected_queries=selections, passed=True)


def test_oracle_safety():
    assert validate()['prunes_checked'] > 0


def test_unknown_atom_is_not_selected_and_negative_goal():
    d = '''(define (domain x) (:predicates (p) (q) (r))
    (:action fix :parameters () :precondition (r) :effect (and (not (p)) (q)))
    (:action prep :parameters () :effect (r)))'''
    p = '(define (problem x) (:domain x) (:init (unknown (p)) (unknown (q))) (:goal (and (not (p)) (q))))'
    t = CompiledTask(d, p); b = RefinementCoverage(t)
    live = [(n,s) for n,s in t.belief if not t.goal.holds(s)]
    extra, _ = b.select(live)
    assert [t.atom_names[i] for i in range(len(t.atom_names)) if extra & (1 << i)] == [('r',)]
    v = projection_view(t, extra)
    assert v.projection_mask != t.projection_mask
    with patch.object(b, 'check', side_effect=InferenceStop()):
        with pytest.raises(InferenceStop):
            b.certificate(live, 0, *b.known(live))


if __name__ == '__main__':
    import argparse, json
    from pathlib import Path
    p = argparse.ArgumentParser(); p.add_argument('--output', type=Path, required=True); a = p.parse_args()
    test_minimum_hitting_set_and_interruption()
    test_one_progress_atom_restores_joint_resource_obstruction()
    test_unknown_atom_is_not_selected_and_negative_goal()
    r = validate(); a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(r, indent=2)); print(json.dumps(r))
