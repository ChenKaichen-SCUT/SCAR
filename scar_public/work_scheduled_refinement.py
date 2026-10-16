"""Budget actual cache-miss work, not top-level calls or cache hits.

One unit per uncached scalar/identity recurrence entry, channel key, action core,
or static pattern. Work stopped mid-query never yields a rejection; completed
subproblems remain reusable. This is a bounded engineering scheduler, not a
prediction of search savings or a theorem about optimal computation allocation.
"""
from scar_public.incremental_channels import IncrementalCoverage
from scar_public.amortized_refinement import AmortizedCoverage
from scar_public.multistep_refinement import MultistepCoverage
from scar_public.decision_coverage import DecisionPlanner
from scar_public.budgeted_planner import InferenceStop


class WorkLedger:
    def __init__(self):
        self.earned = 128
        self.used = 0
        self.query_remaining = 1024
        self.stats = dict(scalar_misses=0, relation_misses=0, channel_misses=0,
            core_misses=0, pattern_misses=0, deferred=0, cache_hits=0)

    def charge(self, kind, amount=1):
        if amount > min(self.earned-self.used, self.query_remaining):
            self.stats['deferred'] += 1
            raise InferenceStop()
        self.used += amount
        self.query_remaining -= amount
        self.stats[kind] += amount


class WorkCoverage(IncrementalCoverage):
    def __init__(self, *args, pool=None, **kwargs):
        super().__init__(*args, pool=pool, **kwargs)
        self.ledger = pool.work_ledger

    def capacity(self, key, horizon):
        key = self.canonical(key, horizon)
        if horizon and (key, horizon) not in self.cache:
            self.ledger.charge('scalar_misses')
        else:
            self.ledger.stats['cache_hits'] += 1
        return super().capacity(key, horizon)

    def relational_capacity(self, key, candidates, horizon):
        key = self.canonical(key, horizon)
        if candidates and horizon and (key, candidates, horizon) not in self.relation_cache:
            self.ledger.charge('relation_misses')
        else:
            self.ledger.stats['cache_hits'] += 1
        return super().relational_capacity(key, candidates, horizon)

    def get_channels(self, key):
        self.check()
        if key in self.channels:
            return self.channels[key]
        self.ledger.charge('channel_misses')
        self._stats['channel_queries'] += 1
        resources, projected = key
        records = []
        pool = self.channel_pool
        for action in self.task.actions.values():
            self.check()
            if any(r < c for r, c in zip(resources, action.consumption)):
                continue
            spec = pool.spec(self.task.projection, action)
            outputs, static, retained, _ = spec
            core_key = action.name, outputs, retained, projected & retained
            if core_key not in pool.channels:
                self.ledger.charge('core_misses')
                known = static | retained
                missing = { (action.name, outputs, known, (s | projected) & known)
                    for s in self.group_masks } - pool.patterns.keys()
                self.ledger.charge('pattern_misses', len(missing))
            goals, core = pool.action_channels(self, projected, action)
            if not goals and not core:
                continue
            remaining = tuple(r-c for r, c in zip(resources, action.consumption))
            records.append((action.name, goals, tuple((m, (remaining, p)) for _, p, m in core)))
        self.mask_channels[key] = tuple(records)
        self.channels[key] = tuple((a, g.bit_count(), tuple((m.bit_count(), q) for m, q in cs))
                                   for a, g, cs in records)
        return self.channels[key]


class WorkMixin:
    coverage_type = WorkCoverage

    def __init__(self, task):
        super().__init__(task)
        self.channel_pool.work_ledger = WorkLedger()
        self.search_expansions = 0

    def decide(self, belief, budget, mode='relation_threshold'):
        ledger = self.channel_pool.work_ledger
        ledger.earned = min(16384, 128 + 4*self.search_expansions)
        ledger.query_remaining = 1024
        return super().decide(belief, budget, mode)

    @property
    def stats(self):
        ledger = self.channel_pool.work_ledger
        return dict(super().stats, work_schedule=dict(ledger.stats,
            earned=ledger.earned, used=ledger.used, remaining=ledger.earned-ledger.used))


class ScheduledCoverage(WorkMixin, AmortizedCoverage):
    pass


class ScheduledMultistepCoverage(WorkMixin, MultistepCoverage):
    pass


class WorkScheduledPlanner(DecisionPlanner):
    def __init__(self, task, multistep=True):
        super().__init__(task, 'relation_threshold')
        self.target_coverage = (ScheduledMultistepCoverage if multistep else ScheduledCoverage)(task)

    def decision(self, belief, budget):
        self.target_coverage.search_expansions = self.expanded
        return super().decision(belief, budget)
