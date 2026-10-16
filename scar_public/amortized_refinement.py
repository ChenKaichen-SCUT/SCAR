"""Reuse an automatically selected projection; reselection only on mismatch.

Selection may be suboptimal and is never a proof. The chosen atoms remain
dynamic, their *current* common values are used at each query, and all effects
are propagated. A different common value never reuses a cached capacity key.
At most four selections per run; no empirical timing threshold is fitted.
"""
from time import perf_counter
from scar_public.certificate_refinement import projection_view, indices
from scar_public.incremental_channels import IncrementalCoverage, IncrementalRefinementCoverage
from scar_public.decision_coverage import DecisionPlanner


class AmortizedCoverage(IncrementalRefinementCoverage):
    coverage_type = IncrementalCoverage

    def __init__(self, task, counts_only=False):
        super().__init__(task)
        self.counts_only = counts_only
        self.active_extra = None
        self.selection_attempts = 0
        self.amortized_stats = dict(reused=0, selections=0, mismatches=0, selection_seconds=0.,
            inference_seconds=0., scalar_prunes=0, relation_prunes=0, collapsed_skips=0)

    def decide(self, belief, budget, mode='relation_gate'):
        live = [(n,s) for n,s in belief if not self.task.goal.holds(s)]
        if budget < 1 or len(live) < 2 or len({self.project(s) for _,s in live}) != 1:
            return False, dict(reason='amortized_inapplicable')
        first, common = self.known(live)
        extra = self.active_extra
        if extra is not None and extra & ~common:
            self.amortized_stats['mismatches'] += 1
            extra = None
        if extra is None:
            if self.selection_attempts >= 4:
                return False, dict(reason='selection_attempt_limit')
            self.selection_attempts += 1; self.amortized_stats['selections'] += 1
            start = perf_counter()
            try:
                extra, _ = self.select(live)
                self.active_extra = extra
            finally:
                self.amortized_stats['selection_seconds'] += perf_counter()-start
        else:
            self.amortized_stats['reused'] += 1
        if extra not in self.refined:
            self.check()
            self.refined[extra] = self.coverage_type(projection_view(self.task, extra), pool=self.channel_pool)
        bound = self.refined[extra]; bound.deadline = self.deadline
        start = perf_counter()
        try:
            # One-static-class collapse permits skipping only the relation
            # recurrence, not scalar reasoning or exact search.
            count = self.counts_only or len(self.group_masks) == 1
            if count and not self.counts_only:
                self.amortized_stats['collapsed_skips'] += 1
            prune, evidence = bound.decide(belief,budget,'count_threshold' if count else 'relation_threshold')
        finally:
            self.amortized_stats['inference_seconds'] += perf_counter()-start
        if prune:
            self.amortized_stats['scalar_prunes' if evidence['reason']=='scalar_prune' else 'relation_prunes'] += 1
        return prune, dict(evidence, selected_atoms=[self.task.atom_names[i] for i in indices(extra)])

    @property
    def stats(self):
        return dict(super().stats, amortized=dict(self.amortized_stats))


class AmortizedPlanner(DecisionPlanner):
    def __init__(self, task, mode='amortized_relation'):
        if mode not in ('amortized_count','amortized_relation'):
            raise ValueError(mode)
        super().__init__(task,'relation_threshold')
        self.target_coverage = AmortizedCoverage(task, counts_only=mode=='amortized_count')
