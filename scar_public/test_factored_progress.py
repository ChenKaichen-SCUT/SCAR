from scar_public.compact_progress import CompactProgress, names, remove
from scar_public.factored_progress import FactoredProgress, FactoredPlanner
from scar_public.test_progress_carrier import microtask
from scar_public.test_reachable_labels import dynamic_identity
from scar_public.test_compact_progress import reachable
from scar_public.information_reference import independent_oracle
from math import inf


def test_all_candidate_restrictions_commute_and_values_agree():
    cases = [microtask((3, 1), v) for v in range(3)]
    t = dynamic_identity(3, consume_at_finish=True, ambiguous_ready=True)
    pat = tuple(sorted(set(t.projection) | {i for i, n in enumerate(t.atom_names) if n[0].startswith('h')}))
    cases.append((t, pat))
    for t, pat in cases:
        plain = CompactProgress(t, pat); factored = FactoredProgress(t, pat)
        for belief in reachable(t, 1):
            key = plain.carrier(belief)
            if key is None:
                continue
            all_ids = names(key[1]); subset = all_ids
            while subset:
                restricted = key[0], remove(key[1], all_ids & ~subset)
                for h in range(4):
                    # Materializing the restriction is the independent old
                    # recurrence; factorized mode must return the same value.
                    for kind in ('lineage', 'matching'):
                        assert factored.relational(key, h, subset, kind) == plain.value(restricted, h, kind)
                subset = (subset-1) & all_ids


def test_search_replay_and_oracle():
    t, _ = microtask((3, 1), 0); optimal = independent_oracle(t)(t.belief, 4)
    for mode in ('factored_relation', 'factored_continue', 'factored_matching'):
        p = FactoredPlanner(t, mode); r = p.solve(t.belief, 4)
        assert r.exact and r.upper == optimal
        if optimal < inf:
            assert p.verify(t.belief, 4, r.policy) == optimal


def test_node_limit_returns_upper_not_partial_maximum():
    t, pat = microtask((3, 1), 1); c = FactoredProgress(t, pat, node_limit=0)
    k = c.carrier(t.belief)
    assert c.value(k, 3, True) == names(k[1]).bit_count()
