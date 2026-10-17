"""Finite falsification checks for written proofs; not proof or performance data."""
from itertools import combinations, product
from math import inf

from scar_public.coverage_certificates import (
    ActionUpper, exhaustive_hall_cut, hall_cut_upper, node_upper, submasks)
from scar_public.coverage_separation import make
from scar_public.information_reference import independent_oracle
from scar_public.relational_coverage import RelationalCoverage, matching_size
from scar_public.resource_information import ResourceInformation
from scar_public.symbolic_task import SymbolicTask
from scar_public.test_relational_coverage import brute_match, toy


def hall_validation():
    checks = cuts = 0
    for n in range(1, 4):
        full = (1 << n) - 1
        options = [(m, c) for m in range(1 << n)
                   for c in range(m.bit_count() + 1)]
        for buckets in product(options, repeat=3):
            truth = brute_match(buckets, n)
            bound, _ = exhaustive_hall_cut(full, buckets)
            assert bound == truth == matching_size(buckets)
            for witness in submasks(full):
                assert truth <= hall_cut_upper(full, buckets, witness)
                cuts += 1
            checks += 1
    return dict(allocation_cases=checks, checked_cut_upper_bounds=cuts)


def test_hall_characterization_against_independent_assignments():
    assert hall_validation()['allocation_cases'] == 8539


def separation_validation():
    subsets = pairs = 0
    rows = []
    for n in range(3, 8):
        task = make(n)
        oracle = independent_oracle(task)
        worlds = tuple(task.belief)
        for size in range(1, n):
            for group in combinations(worlds, size):
                assert oracle(frozenset(group), 2) <= 2
                subsets += 1
        assert oracle(task.belief, 2) == inf
        control = ResourceInformation(task, work_limit=10_000_000)
        reject, evidence = control.decide(task.belief, 2)
        assert evidence['complete'] and not reject
        assert evidence['conflict_pairs'] == 0
        assert set(evidence['observation_caps'].values()) == {1}
        pairs += n * (n - 1) // 2
        lineage = RelationalCoverage(task, 'lineage', None)
        matching = RelationalCoverage(task, 'matching', None)
        q = lineage.project(worlds[0][1]); full = (1 << n) - 1
        assert lineage.capacity(q, 2) == n
        assert lineage.relational_capacity(q, full, 2) == n - 1
        assert matching.relational_capacity(q, full, 2) == n - 1
        rows.append(dict(models=n, counts=n, lineage=n-1, matching=n-1,
                         resource_kraft='complete_pass', exact='infeasible'))
    return dict(proper_subsets=subsets, resource_pairs=pairs, rows=rows)


def test_strict_separation_from_combined_complete_controls():
    assert separation_validation()['proper_subsets'] == 238


def projection_counterexample(refined):
    domain = '''(define (domain reveal)
      (:predicates (h) (start) (stage) (b) (done))
      (:action prepare :parameters () :precondition (start)
        :effect (and (not (start)) (stage) (when (h) (b))))
      (:action finish-true :parameters () :precondition (stage)
        :effect (and (not (stage)) (when (h) (done))))
      (:action finish-false :parameters () :precondition (stage)
        :effect (and (not (stage)) (when (not (h)) (done)))))'''
    problem = '''(define (problem reveal) (:domain reveal)
       (:init (start) (unknown (h))) (:goal (done)))'''
    return SymbolicTask(domain, problem,
                        projection_predicates=('start', 'stage', 'b') if refined
                        else ('start', 'stage'))


def test_projection_can_weaken_both_relational_bounds():
    for refined, expected in ((False, 1), (True, 2)):
        task = projection_counterexample(refined)
        assert independent_oracle(task)(task.belief, 3) == inf
        assert all(independent_oracle(task)(frozenset((w,)), 2) == 2
                   for w in task.belief)
        for mode in ('lineage', 'matching'):
            bound = RelationalCoverage(task, mode, None)
            keys = {bound.project(s) for _, s in task.belief}
            assert len(keys) == 1
            assert bound.relational_capacity(keys.pop(), 3, 2) == expected


def test_sound_partial_cut_and_incomplete_enumeration():
    # Only the third child's upper=1 needs a nontrivial recursive certificate.
    # The first two capacities need not have finished; their mask ceilings are 1.
    action = ActionUpper(0, ((1, 1), (1, 1), (6, 1)), witness=6)
    assert node_upper(7, (action,), complete=True, mode='lineage') == 3
    assert node_upper(7, (action,), complete=True, mode='matching') == 2
    assert node_upper(7, (action,), complete=False, mode='matching') == 3
    # A missing action could finish everybody. Closing only the seen action is unsafe.
    finish_all = ActionUpper(7, (), witness=0)
    assert node_upper(7, (action, finish_all), complete=True, mode='matching') == 3
    import pytest
    with pytest.raises(ValueError):
        hall_cut_upper(3, ((3, 1),), 4)


def monotonicity_validation():
    checks = 0
    # Complete enumeration of two-bucket, two-model channel systems over three
    # levels. Terminal alternative actions force a shared-action bottleneck.
    for goals, left, right in product(range(4), repeat=3):
        table = {0: (('a', goals, ((left, 1), (right, 2))),),
                 1: (('x', 1, ()), ('y', 2, ())),
                 2: (('x', 1, ()), ('y', 2, ()))}
        for mode in ('lineage', 'matching'):
            bound = toy(mode, table, 2)
            for depth in range(3):
                for small in range(4):
                    value = bound.relational_capacity(0, small, depth)
                    assert value <= bound.capacity(0, depth)
                    assert value <= bound.relational_capacity(0, small, depth + 1)
                    for large in range(4):
                        if small & ~large == 0:
                            assert value <= bound.relational_capacity(0, large, depth)
                            checks += 1
    return checks


def test_candidate_and_horizon_monotonicity():
    assert monotonicity_validation() == 3456


def simulation_validation():
    # Complete small-table check of the qualified refinement theorem. Shrink
    # eligibility without splitting buckets or changing immediate absorption.
    checks = 0
    for goals, left, right in product(range(4), repeat=3):
        tails = {1: (('x', 1, ()), ('y', 2, ())),
                 2: (('x', 1, ()), ('y', 2, ()))}
        coarse_table = dict(tails)
        coarse_table[0] = (('a', goals, ((left, 1), (right, 2))),)
        for mode in ('lineage', 'matching'):
            coarse = toy(mode, coarse_table, 2)
            for fine_left, fine_right in product(submasks(left), submasks(right)):
                fine_table = dict(tails)
                fine_table[0] = (('a', goals, ((fine_left, 1), (fine_right, 2))),)
                fine = toy(mode, fine_table, 2)
                for mask in range(4):
                    assert fine.relational_capacity(0, mask, 2) <= coarse.relational_capacity(0, mask, 2)
                    checks += 1
    return checks


def test_injective_channel_simulation_with_equal_goal_masks():
    assert simulation_validation() == 2592


if __name__ == '__main__':
    import argparse, json, platform, z3
    from pathlib import Path
    p = argparse.ArgumentParser(); p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    test_projection_can_weaken_both_relational_bounds()
    test_sound_partial_cut_and_incomplete_enumeration()
    result = dict(hall=hall_validation(), separation=separation_validation(),
                  monotonicity_checks=monotonicity_validation(),
                  simulation_checks=simulation_validation(), all_passed=True,
                  python=platform.python_version(), z3=z3.get_version_string(),
                  scope='Finite proof-regression checks, not formal verification or held-out performance.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))
