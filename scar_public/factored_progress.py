"""Separate prefix transition support from the not-yet-credited ID mask.

For any S, projected transitions commute with candidate restriction:
T(R restricted to S, a, o) = T(R, a, o) restricted to S.
This follows because each SAT transition is candidate-local. We therefore keep
the full carrier in transition cache keys and pass S only to the capacity DP.
Lineage removal no longer rebuilds identical progress channels for ID subsets.
This is an exact refactoring of CompactProgress, not a new relaxation.
"""
from time import perf_counter
from scar_public.compact_progress import CompactProgress, names
from scar_public.progress_carrier import causal_pattern
from scar_public.decision_coverage import DecisionPlanner
from scar_public.relational_coverage import matching_size


class FactoredProgress(CompactProgress):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.factor_cache = {}
        self.factor_stats = dict(nodes=0, hits=0, witness_skips=0,
            fallback=0, matching_calls=0, matching_seconds=0.)

    @property
    def stats(self):
        return dict(super().stats, factored_progress=dict(self.factor_stats,
            entries=len(self.factor_cache)))

    def value(self, key, horizon, identity=False):
        if identity is False or identity == 'counts':
            return super().value(key, horizon, False)
        kind = 'lineage' if identity is True else identity
        if kind not in ('lineage', 'matching'):
            raise ValueError(kind)
        return self.relational(key, horizon, names(key[1]), kind)

    def relational(self, key, horizon, active, kind='lineage'):
        self.check(); active &= names(key[1])
        if not horizon or not active:
            return 0
        key = self.canonical(key, horizon); memo = key, horizon, active, kind
        if memo in self.factor_cache:
            self.factor_stats['hits'] += 1
            return self.factor_cache[memo]
        ceiling = active.bit_count()
        scalar_memo = key, horizon, 'counts'
        witness = self.support_witness.get(scalar_memo, 0)
        if not active & ~witness:
            self.factor_stats['witness_skips'] += 1
            self.factor_cache[memo] = ceiling
            return ceiling
        ceiling = min(ceiling, self.compact_cache.get(scalar_memo, ceiling))
        if self.compact_stats['value_nodes'] + self.factor_stats['nodes'] >= self.carrier_node_limit:
            self.factor_stats['fallback'] += 1
            return ceiling
        self.factor_stats['nodes'] += 1
        resources, carrier = key; best = 0
        for action in self.task.actions.values():
            self.check()
            if any(r < c for r, c in zip(resources, action.consumption)):
                continue
            possible_goals, children = self.core(carrier, action)
            goals = possible_goals & active; remaining_ids = active & ~goals
            remaining = tuple(r-c for r, c in zip(resources, action.consumption))
            if not goals and len(children) == 1 and children[0] == carrier and remaining == resources:
                continue
            total = goals.bit_count(); buckets = []
            for child in children:
                eligible = names(child) & remaining_ids
                if not eligible:
                    continue
                value = self.relational((remaining, child), horizon-1, eligible, kind)
                total += value
                if kind == 'matching' and value:
                    buckets.append((eligible, value))
                if kind != 'matching' and total >= ceiling:
                    break
            if kind == 'matching' and len(buckets) > 1:
                self.factor_stats['matching_calls'] += 1; start = perf_counter()
                total = goals.bit_count()+matching_size(buckets)
                self.factor_stats['matching_seconds'] += perf_counter()-start
            best = max(best, min(ceiling, total))
            if best == ceiling:
                break
        self.factor_cache[memo] = best
        return best


class FactoredPlanner(DecisionPlanner):
    def __init__(self, task, mode='factored_relation'):
        if mode not in ('factored_relation', 'factored_continue', 'factored_matching'):
            raise ValueError(mode)
        super().__init__(task, 'relation_threshold')
        self.target_coverage = FactoredProgress(task, pattern=causal_pattern(task))
        if mode == 'factored_matching':
            self.decision_mode = 'matching'
        if mode == 'factored_continue':
            self.target_coverage.continuation_deadline = lambda start: start+max(0., 3.-self.target_seconds)
