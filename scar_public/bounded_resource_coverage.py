"""Finite-horizon canonical resource keys; identical coverage feasibility.

For SymbolicTask, resources are only tested for nonnegative fixed consumption.
In t steps resource i cannot consume more than t * max_a consumption(a,i).
Any larger stock is indistinguishable for this capacity query and is clipped.
No numeric goal, replenishment or resource-dependent observation is supported.
"""
from scar_public.demand_coverage import DemandCoverage
from scar_public.threshold_search import ThresholdPlanner


class BoundedResourceCoverage(DemandCoverage):
    def __init__(self, task, mode='matching', node_limit=5000):
        super().__init__(task, mode, node_limit)
        self.max_consumption = tuple(max((a.consumption[i] for a in task.actions.values()),default=0)
            for i in range(len(task.resources)))

    def canonical(self, key, horizon):
        resources, projection = key
        return tuple(min(r,horizon*c) for r,c in zip(resources,self.max_consumption)),projection

    def capacity(self, key, horizon):
        return super().capacity(self.canonical(key,horizon),horizon)

    def relational_capacity(self, key, candidates, horizon):
        return super().relational_capacity(self.canonical(key,horizon),candidates,horizon)


class BoundedResourcePlanner(ThresholdPlanner):
    def __init__(self, task, mode='matching', node_limit=5000):
        if mode not in self.MODES:
            raise ValueError(mode)
        super().__init__(task,'single')
        if mode != 'single':
            self.coverage=BoundedResourceCoverage(task,mode,node_limit)
