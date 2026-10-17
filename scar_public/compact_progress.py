"""Lossless grouping of prefix-labelled progress; lazy resource-free edges.

An abstract carrier is (static facts, hidden progress, candidate mask) triples.
Equal states share transitions, but masks retain the relation to initial IDs.
The count and lineage variants are exactly the recurrences in ProgressCarrier.
The matching variant additionally bounds distinct IDs across actual observations.
Neither grouping nor hidden progress creates an observation for the controller.
"""
from collections import defaultdict
from time import perf_counter
from scar_public.progress_carrier import ProgressCarrier, causal_pattern
from scar_public.incremental_channels import IncrementalChannels
from scar_public.relational_coverage import matching_size
from scar_public.decision_coverage import DecisionPlanner


def names(carrier):
    mask = 0
    for _, _, ids in carrier:
        mask |= ids
    return mask


def remove(carrier, mask):
    return tuple((s, p, ids & ~mask) for s, p, ids in carrier if ids & ~mask)


class CompactProgress(IncrementalChannels, ProgressCarrier):
    def __init__(self, task, pattern=None, node_limit=50000):
        super().__init__(task, pattern=pattern, node_limit=node_limit)
        self.cores = {}; self.compact_cache = {}; self.support_witness = {}
        self.continuation_deadline = None
        self.compact_stats = dict(core_hits=0, core_misses=0, core_seconds=0.,
            state_groups=0, represented_pairs=0, max_groups=0,
            value_hits=0, value_nodes=0, clipped_resources=0,
            matching_calls=0, matching_seconds=0., sibling_reductions=0,
            deterministic_actions=0, ambiguous_actions=0,
            lineage_skips=0, matching_skips=0, continuation_grants=0)

    @property
    def stats(self):
        return dict(super().stats, compact_progress=dict(self.compact_stats,
            core_entries=len(self.cores), value_entries=len(self.compact_cache)))

    def carrier(self, belief):
        live = [(n, s) for n, s in belief if not self.original.goal.holds(s)]
        resources = {s.resources for _, s in live}
        if len(resources) != 1:
            return None
        grouped = defaultdict(int)
        for name, state in live:
            i = int(name[1:])
            grouped[self.task.static_bits[i], state.symbols[0] & self.task.projection_mask] |= 1 << i
        return next(iter(resources)), tuple((s, p, ids) for (s, p), ids in sorted(grouped.items()))

    def core(self, carrier, action):
        """Complete action core, published atomically; no resource dependence."""
        self.check()
        key = carrier, action.name
        if key in self.cores:
            self.compact_stats['core_hits'] += 1
            return self.cores[key]
        self.compact_stats['core_misses'] += 1
        started = perf_counter()
        try:
            goals = 0; buckets = defaultdict(lambda: defaultdict(int))
            self.compact_stats['state_groups'] += len(carrier)
            self.compact_stats['represented_pairs'] += sum(m.bit_count() for _, _, m in carrier)
            self.compact_stats['max_groups'] = max(self.compact_stats['max_groups'], len(carrier))
            for static, projected, ids in carrier:
                immediate, outcomes = self.pattern(static, projected, action)
                if immediate:
                    goals |= ids
                for obs, nxt in outcomes:
                    buckets[obs][static, nxt] |= ids
            children = tuple(tuple((s, p, ids) for (s, p), ids in sorted(b.items()))
                for _, b in sorted(buckets.items()))
            seen = goals; overlap = False
            for child in children:
                mask = names(child); overlap |= bool(seen & mask); seen |= mask
            self.compact_stats['ambiguous_actions' if overlap else 'deterministic_actions'] += 1
            result = goals, children
            # Cache storage is optional; completed result is still usable.
            if len(self.cores) < 100000:
                self.cores[key] = result
            return result
        finally:
            self.compact_stats['core_seconds'] += perf_counter()-started

    def value(self, key, horizon, identity=False):
        self.check()
        kind = 'lineage' if identity is True else ('counts' if identity is False else identity)
        if kind not in ('counts', 'lineage', 'matching'):
            raise ValueError(kind)
        if not horizon or not key[1]:
            return 0
        canonical = self.canonical(key, horizon)
        self.compact_stats['clipped_resources'] += canonical[0] != key[0]
        key = canonical; memo = key, horizon, kind
        if memo in self.compact_cache:
            self.compact_stats['value_hits'] += 1
            return self.compact_cache[memo]
        ceiling = names(key[1]).bit_count()
        scalar_memo = key, horizon, 'counts'
        # This is a lower witness for the optimistic abstract recurrence, NOT
        # a real policy. Deleting other candidate IDs preserves its channels.
        if kind != 'counts' and self.support_witness.get(scalar_memo, 0) == names(key[1]):
            self.compact_stats['matching_skips' if kind == 'matching' else 'lineage_skips'] += 1
            self.compact_cache[memo] = ceiling
            self.support_witness[memo] = names(key[1])
            return ceiling
        if self.compact_stats['value_nodes'] >= self.carrier_node_limit:
            self.carrier_stats['node_fallbacks'] += 1
            return ceiling
        self.compact_stats['value_nodes'] += 1
        resources, carrier = key; best = 0; best_support = 0
        # Laziness matters: a saturated action needs no later action SAT calls.
        for action in self.task.actions.values():
            self.check()
            if any(r < c for r, c in zip(resources, action.consumption)):
                continue
            goals, children = self.core(carrier, action)
            if not goals and not children:
                continue
            remaining = tuple(r-c for r, c in zip(resources, action.consumption))
            if not goals and len(children) == 1 and children[0] == carrier and remaining == resources:
                continue
            total = goals.bit_count(); buckets = []; support = goals
            for child in children:
                if kind != 'counts' and goals:
                    child = remove(child, goals)
                value = self.value((remaining, child), horizon-1, kind)
                child_memo = self.canonical((remaining, child), horizon-1), horizon-1, kind
                support |= self.support_witness.get(child_memo, 0)
                total += value
                if kind == 'matching' and value:
                    buckets.append((names(child), value))
                if kind != 'matching' and total >= ceiling:
                    break
            if kind == 'matching' and len(buckets) > 1:
                self.compact_stats['matching_calls'] += 1
                started = perf_counter(); distinct = matching_size(buckets)
                self.compact_stats['matching_seconds'] += perf_counter()-started
                self.compact_stats['sibling_reductions'] += distinct < sum(c for _, c in buckets)
                total = goals.bit_count()+distinct
            best = max(best, min(ceiling, total))
            if support.bit_count() > best_support.bit_count():
                best_support = support
            if best == ceiling:
                break
        self.compact_cache[memo] = best
        self.support_witness[memo] = best_support
        return best

    def decide(self, belief, budget, mode):
        query_started = perf_counter()
        key = self.carrier(belief)
        n = names(key[1]).bit_count() if key is not None else 0
        if n < 2:
            return False, dict(reason='carrier_inapplicable')
        self.decision_stats['scalar_queries'] += 1
        count = self.value(key, budget)
        e = dict(candidates=n, budget=budget, scalar=count)
        if count < n:
            self.decision_stats['scalar_prunes'] += 1
            return True, dict(e, reason='scalar_prune')
        if mode == 'count_threshold':
            return False, dict(e, reason='count_pass')
        scalar_memo = self.canonical(key, budget), budget, 'counts'
        witness = self.support_witness.get(scalar_memo, 0).bit_count()
        e['distinct_witness'] = witness
        # A deficit is only a scheduling signal, never a rejection certificate.
        # Do not steal time from unfinished scalar queries. Spend at most the
        # original run-wide remainder, with no task/domain specific threshold.
        if witness < n and self.continuation_deadline is not None:
            extended = self.continuation_deadline(query_started)
            if extended > self.deadline:
                self.deadline = extended
                self.compact_stats['continuation_grants'] += 1
                e['continuation'] = True
        self.decision_stats['relation_queries'] += 1
        kind = 'matching' if mode == 'matching' else 'lineage'
        value = self.value(key, budget, kind)
        prune = value < n; self.decision_stats['relation_prunes'] += prune
        return prune, dict(e, identity_capacity=value, relation_kind=kind,
            reason='relation_prune' if prune else 'relation_pass')


class CompactPlanner(DecisionPlanner):
    def __init__(self, task, mode='compact_relation', width=12):
        if mode not in ('compact_count', 'compact_relation', 'compact_matching', 'compact_continue'):
            raise ValueError(mode)
        super().__init__(task, 'count_threshold' if mode == 'compact_count' else 'relation_threshold')
        if mode == 'compact_matching':
            self.decision_mode = 'matching'
        self.target_coverage = CompactProgress(task, pattern=causal_pattern(task, width))
        if mode == 'compact_continue':
            self.target_coverage.continuation_deadline = lambda start: start+max(0., 3.-self.target_seconds)
