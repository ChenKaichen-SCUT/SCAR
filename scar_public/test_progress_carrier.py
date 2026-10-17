from collections import defaultdict
from itertools import combinations
from math import inf
from scar_public.progress_carrier import ProgressCarrier, CarrierPlanner
from scar_public.compiled_task import CompiledTask
from scar_public.information_reference import independent_oracle
from scar_public.coverage_separation import make
from scar_public.test_reachable_labels import dynamic_identity


def test_same_hidden_projection_count_passes_relation_rejects():
    # Static separation remains a regression test of the stronger carrier. The
    # dynamic version below removes all immutable identity distinctions.
    for ambiguous in (False, True):
        t = dynamic_identity(3, consume_at_finish=True, ambiguous_ready=ambiguous)
        hidden = tuple(sorted(set(t.projection) | {i for i, n in enumerate(t.atom_names) if n[0].startswith('h')}))
        c = ProgressCarrier(t, pattern=hidden)
        key = c.carrier(t.belief)
        assert c.value(key, 2) == (3 if ambiguous else 2)
        assert c.value(key, 2, True) == 2
    t = make(3)
    c = ProgressCarrier(t, pattern=t.projection)
    key = c.carrier(t.belief)
    # Prefix support already excludes the first credited ID from the only
    # non-goal child; stronger C0 therefore closes the old separation by itself.
    assert c.value(key, 2) == 2
    assert c.value(key, 2, True) == 2


def microtask(resources, variant):
    d = '''(define (domain d) (:predicates (h) (p) (q) (g))
      (:action advance :parameters () :effect (and (p) (when (h) (q))))
      (:action toggle :parameters () :effect (and (when (h) (not (h))) (when (not (h)) (h))))
      (:action inspect :parameters () :observe (q))
      (:action finish :parameters () :precondition (p) :effect (when (q) (g)))
      (:action lose :parameters () :precondition (g) :effect (and (not (g)) (not (p))))
      (:action repair :parameters () :precondition (not (p)) :effect (q)))'''
    p = '(define (problem p) (:domain d) (:init (unknown (h))) (:goal (g)))'
    costs = {a: ((0, 1) if a == 'inspect' else (1, 0)) for a in ('advance', 'toggle', 'inspect', 'finish', 'lose', 'repair')}
    t = CompiledTask(d, p, resources=resources, resource_costs=costs)
    chosen = {'h', 'p', 'q', 'g'} if variant == 0 else ({'p', 'q'} if variant == 1 else {'h', 'p'})
    return t, tuple(i for i, n in enumerate(t.atom_names) if n[0] in chosen)


def test_all_reachable_small_queries_against_independent_oracle():
    for resources in ((2, 0), (2, 1), (3, 1)):
        for variant in range(3):
            t, pattern = microtask(resources, variant)
            c = ProgressCarrier(t, pattern=pattern)
            oracle = independent_oracle(t)
            frontier = {t.belief}; beliefs = set(frontier)
            for _ in range(2):
                later = set()
                for belief in frontier:
                    for a in t.actions:
                        branches = defaultdict(set); valid = True
                        for name, state in belief:
                            nxt, obs = t.step(state, a)
                            valid &= t.allowed(nxt); branches[obs].add((name, nxt))
                        if valid:
                            later.update(frozenset(b) for b in branches.values())
                beliefs |= later; frontier = later
            for belief in beliefs:
                worlds = sorted(belief, key=lambda w: w[0])
                for size in range(1, len(worlds)+1):
                    for subset in combinations(worlds, size):
                        b = frozenset(subset); key = c.carrier(b)
                        if key is None:
                            continue
                        live = len(key[1])
                        for h in range(4):
                            if oracle(b, h) < inf:
                                assert c.value(key, h) >= live
                                assert c.value(key, h, True) >= live


def test_full_deterministic_pattern_has_no_identity_bonus():
    t, _ = microtask((3, 1), 0)
    c = ProgressCarrier(t, pattern=tuple(sorted(t.dynamic)))
    key = c.carrier(t.belief)
    for h in range(5):
        assert c.value(key, h) == c.value(key, h, True)
    assert c.carrier_stats['goals_with_live_successors'] == 0


def test_node_limit_is_safe_upper_fallback():
    t, pattern = microtask((3, 1), 0)
    c = ProgressCarrier(t, pattern=pattern, node_limit=0)
    key = c.carrier(t.belief)
    assert c.value(key, 3) == len(key[1])
    assert c.value(key, 3, True) == len(key[1])


def test_search_replay_and_optimum():
    for resources in ((2, 0), (3, 1)):
        t, _ = microtask(resources, 0)
        exact = independent_oracle(t)(t.belief, 4)
        for mode in ('carrier_count', 'carrier_relation'):
            p = CarrierPlanner(t, mode); r = p.solve(t.belief, 4)
            assert r.exact and r.upper == exact
            if r.upper < inf:
                assert p.verify(t.belief, 4, r.policy) == r.upper
