"""Exact resource-aware pair projections, not a renamed LUG reproduction.

On conformant tasks completed pair feasibility is at least as discriminating as
the pair-goal LUG-X set-level test. On contingent tasks this checks actual
observation branches; conformant cross-world mutex rejection is not used there.
"""
from time import perf_counter
from scar_public.indexed_planner import IndexedPlanner,IndexedControls
from scar_public.information_controls import ControlLimit

class TimedPairs(IndexedControls):
    def __init__(self,task):
        super().__init__(task,work_limit=300000);self.deadline=float('inf')
    def charge(self):
        if perf_counter()>=self.deadline:raise ControlLimit()
        super().charge()

class PairControlPlanner(IndexedPlanner):
    def __init__(self,task):
        super().__init__(task);self.pairs=TimedPairs(task);self.pair_seconds=0.
        self.pair_prunes=0;self.pair_seen=set()
    def optional_lower(self,belief,budget,cheap):
        key=belief,budget
        if key in self.pair_seen or len(belief)<2 or self.pair_seconds>=3.:return cheap
        self.pair_seen.add(key);start=perf_counter()
        self.pairs.deadline=start+min(.25,3.-self.pair_seconds)
        try:
            bound=self.pairs.pair_lower(belief,budget)
            self.pair_prunes+=bound>budget
            return max(cheap,bound)
        finally:self.pair_seconds+=perf_counter()-start
    def statistics(self):
        return dict(super().statistics(),resource_pair=dict(self.pairs.stats,
            seconds=self.pair_seconds,prunes=self.pair_prunes))
