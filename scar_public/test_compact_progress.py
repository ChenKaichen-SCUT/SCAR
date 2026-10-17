from collections import defaultdict
from itertools import combinations
from math import inf
import pytest
from scar_public.compact_progress import CompactProgress, CompactPlanner, names
from scar_public.progress_carrier import ProgressCarrier
from scar_public.test_progress_carrier import microtask
from scar_public.test_reachable_labels import dynamic_identity
from scar_public.information_reference import independent_oracle
from scar_public.budgeted_planner import InferenceStop


def reachable(task, depth=2):
    frontier = {task.belief}; result = set(frontier)
    for _ in range(depth):
        later = set()
        for belief in frontier:
            for action in task.actions:
                buckets = defaultdict(set); valid = True
                for name, state in belief:
                    nxt, obs = task.step(state, action)
                    valid &= task.allowed(nxt); buckets[obs].add((name, nxt))
                if valid:
                    later.update(frozenset(x) for x in buckets.values())
        result |= later; frontier = later
    return result


def test_lossless_grouping_and_capacity_equivalence():
    for resources in ((2, 0), (2, 1), (3, 1)):
        for variant in range(3):
            t, pattern = microtask(resources, variant)
            old = ProgressCarrier(t, pattern); new = CompactProgress(t, pattern)
            oracle = independent_oracle(t)
            for belief in reachable(t):
                worlds = sorted(belief, key=lambda w: w[0])
                for size in range(1, len(worlds)+1):
                    for subset in combinations(worlds, size):
                        b = frozenset(subset); ok = old.carrier(b); nk = new.carrier(b)
                        if ok is None:
                            assert nk is None; continue
                        decoded = defaultdict(set)
                        for _, projected, mask in nk[1]:
                            for i in range(len(t.models)):
                                if mask & (1 << i):
                                    decoded[i].add(projected)
                        assert ok[1] == tuple((i, tuple(sorted(v))) for i, v in sorted(decoded.items()))
                        for h in range(4):
                            scalar = new.value(nk, h)
                            lineage = new.value(nk, h, True)
                            matching = new.value(nk, h, 'matching')
                            memo = new.canonical(nk, h), h, 'counts'
                            assert new.support_witness.get(memo, 0).bit_count() <= matching
                            assert scalar == old.value(ok, h)
                            assert lineage == old.value(ok, h, True)
                            assert matching <= lineage <= scalar
                            if oracle(b, h) < inf:
                                assert matching >= names(nk[1]).bit_count()


def test_dynamic_identity_separation_and_full_projection_collapse():
    t = dynamic_identity(3, consume_at_finish=True, ambiguous_ready=True)
    pattern = tuple(sorted(set(t.projection) | {i for i, n in enumerate(t.atom_names) if n[0].startswith('h')}))
    c = CompactProgress(t, pattern); k = c.carrier(t.belief)
    assert c.value(k, 2) == 3 and c.value(k, 2, True) == 2
    assert c.value(k, 2, 'matching') == 2
    full = CompactProgress(t, tuple(sorted(t.dynamic))); k = full.carrier(t.belief)
    for h in range(4):
        assert full.value(k, h) == full.value(k, h, True) == full.value(k, h, 'matching')


def test_interrupted_core_not_published_and_node_fallback_safe():
    t, pat = microtask((3, 1), 1); c = CompactProgress(t, pat)
    k = c.carrier(t.belief); action = next(iter(t.actions.values()))
    def stop(*args):
        raise InferenceStop()
    c.pattern = stop
    with pytest.raises(InferenceStop):
        c.core(k[1], action)
    assert not c.cores
    c = CompactProgress(t, pat, node_limit=0); k = c.carrier(t.belief)
    for kind in (False, True, 'matching'):
        assert c.value(k, 4, kind) == names(k[1]).bit_count()


def test_search_and_policy_replay():
    for resources in ((2, 0), (3, 1)):
        t, _ = microtask(resources, 0); exact = independent_oracle(t)(t.belief, 4)
        for mode in ('compact_count', 'compact_relation', 'compact_matching', 'compact_continue'):
            p = CompactPlanner(t, mode); r = p.solve(t.belief, 4)
            assert r.exact and r.upper == exact
            if r.upper < inf:
                assert p.verify(t.belief, 4, r.policy) == r.upper


def test_saturation_skip_requires_distinct_candidate_witness():
    t = dynamic_identity(3, consume_at_finish=True, ambiguous_ready=True)
    pattern = tuple(sorted(set(t.projection) | {i for i, n in enumerate(t.atom_names) if n[0].startswith('h')}))
    c = CompactProgress(t, pattern); key = c.carrier(t.belief)
    assert c.value(key, 2) == 3
    assert c.support_witness[c.canonical(key, 2), 2, 'counts'].bit_count() == 2
    assert c.value(key, 2, True) == 2
    t, pat = microtask((3, 1), 0); c = CompactProgress(t, pat); key = c.carrier(t.belief)
    assert c.value(key, 3) == 2
    assert c.value(key, 3, True) == 2
    assert c.compact_stats['lineage_skips'] > 0


def test_continuation_only_after_scalar_pass_and_witness_deficit():
    t = dynamic_identity(3, consume_at_finish=True, ambiguous_ready=True)
    pattern = tuple(sorted(set(t.projection) | {i for i, n in enumerate(t.atom_names) if n[0].startswith('h')}))
    c = CompactProgress(t, pattern); seen = []
    def extend(start):
        seen.append(start)
        return float('inf')
    c.continuation_deadline = extend
    prune, evidence = c.decide(t.belief, 2, 'relation_threshold')
    assert prune and evidence['reason'] == 'relation_prune' and len(seen) == 1
    c.decide(t.belief, 1, 'relation_threshold')
    assert len(seen) == 1
    t, pattern = microtask((3, 1), 0); c = CompactProgress(t, pattern)
    c.continuation_deadline = extend
    c.decide(t.belief, 3, 'relation_threshold')
    assert len(seen) == 1
