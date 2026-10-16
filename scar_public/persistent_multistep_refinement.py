"""Engineering correction: preserve chosen identities and stop exhausted gates.

Chosen atoms temporarily lacking a common value are omitted from that query's
view, then restored once common again. No old truth value is restored. Completed
views/caches are reused by atom set; this does not assert monotone capacity.
"""
from scar_public.cached_multistep_refinement import CachedMultistepCoverage, BatchedWorkPlanner
from scar_public.work_scheduled_refinement import WorkMixin
from scar_public.decision_coverage import DecisionPlanner


class PersistentMultistepCoverage(CachedMultistepCoverage):
    def __init__(self,task):
        super().__init__(task)
        self.retained_identities=0
        self.persistence_stats=dict(restored=0,restricted=0)

    def decide(self,belief,budget,mode='relation_threshold'):
        live=[(n,s) for n,s in belief if not self.task.goal.holds(s)]
        if self.active_extra is not None and live:
            _,common=self.known(live)
            desired=self.retained_identities&common
            self.persistence_stats['restored']+=bool(desired&~self.active_extra)
            self.persistence_stats['restricted']+=bool(self.active_extra&~desired)
            self.active_extra=desired
        try:return super().decide(belief,budget,mode)
        finally:
            if self.active_extra is not None:
                self.retained_identities|=self.active_extra

    @property
    def stats(self):
        return dict(super().stats,persistence=dict(self.persistence_stats,
            chosen_identities=self.retained_identities.bit_count()))


class PersistentWorkCoverage(WorkMixin,PersistentMultistepCoverage):
    pass


class FinalWorkPlanner(BatchedWorkPlanner):
    def __init__(self,task,multistep=True):
        super().__init__(task,multistep=False)
        if multistep:self.target_coverage=PersistentWorkCoverage(task)

    def decision(self,belief,budget):
        # This fast path avoids admission-key construction on every remaining
        # search node after no optional work can run. Keep recursion dispatch.
        if self.target_attempts>=64 or self.target_seconds>2.975:
            return super(DecisionPlanner,self).decision(belief,budget)
        return super().decision(belief,budget)
