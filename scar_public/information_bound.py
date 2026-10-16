"""Offline candidate bounds for finite resource-constrained contingent planning.

Pair projection is a relaxation, not a claim of a new heuristic family. A pair
must use the same action until its observations differ. Resource-changing tests
and productive actions use exactly the same transition function and cost.
This module is intentionally not enabled in the V6/V8 execution adapter.
"""
from __future__ import annotations

from itertools import combinations
from math import inf

from scar_public.finite_planner import Planner, Result
from scar_public.observation_capacity import ObservationCapacity


class BoundBudgetExceeded(RuntimeError):
    pass


class InformationBoundPlanner(Planner):
    """Same AND/OR search as Planner, with alternative initial lower bounds.

    lp: existing per-world certified LP maximum.
    single: maximum exact known-world completion cost (perfect information).
    pair_lp: common pair actions until first observation split, then LP tails;
             maximized with the existing LP bound.
    pair_exact: maximum exact one/two-world policy cost. The exact singleton
                ablation separates information coupling from stronger tails.
    capacity_lp / capacity_single: resource-indexed policy coverage upper bound,
                combined with LP / exact perfect-information completion costs.

    node_limit bounds additional DP work over this planner's lifetime. Completed
    subproblems remain valid; unfinished work never becomes an infinity proof.
    The existing LP is the fallback if a single-world DP cannot finish.
    """

    MODES = ('lp', 'single', 'pair_lp', 'pair_exact', 'capacity_lp', 'capacity_single')

    def __init__(self, models, goal, allowed=lambda s: True, mode='pair_lp',
                 node_limit=None):
        if mode not in self.MODES:
            raise ValueError(mode)
        if node_limit is not None and (type(node_limit) is not int or node_limit < 0):
            raise ValueError('node_limit must be None or a nonnegative integer')
        super().__init__(models, goal, allowed, use_lp=mode in ('lp', 'pair_lp', 'capacity_lp'))
        self.mode, self.node_limit = mode, node_limit
        self.single_cache, self.pair_cache, self.bound_cache = {}, {}, {}
        self.bound_stats = dict(single_nodes=0, pair_nodes=0, transition_lookups=0,
                                calls=0, budget_exhausted=False)
        self.coverage = ObservationCapacity(models, goal, allowed) if mode.startswith('capacity_') else None

    def _charge(self, kind):
        used = self.bound_stats['single_nodes'] + self.bound_stats['pair_nodes']
        if self.node_limit is not None and used >= self.node_limit:
            self.bound_stats['budget_exhausted'] = True
            raise BoundBudgetExceeded
        self.bound_stats[kind] += 1

    def _step(self, world, action):
        self.bound_stats['transition_lookups'] += 1
        name, state = world
        successor, observation = self.models[name].step(state, action)
        return (name, successor), observation

    def _terminal(self, worlds, horizon):
        if any(not self.allowed(s) for _, s in worlds):
            return inf
        if all(self.goal.holds(s) for _, s in worlds):
            return 0
        if horizon == 0:
            return inf
        return None

    def singleton(self, world, horizon):
        key = world, horizon
        if key in self.single_cache:
            return self.single_cache[key]
        terminal = self._terminal((world,), horizon)
        if terminal is not None:
            return terminal
        self._charge('single_nodes')
        best = inf
        for action, cost in self.costs.items():
            if cost >= best:
                continue
            successor, _ = self._step(world, action)
            best = min(best, cost + self.singleton(successor, horizon - 1))
        self.single_cache[key] = best
        return best

    def _tail(self, world, horizon):
        terminal = self._terminal((world,), horizon)
        if terminal is not None:
            return terminal
        if self.mode == 'pair_lp':
            name, state = world
            return self.relax[name].lower(state, horizon)
        return self.singleton(world, horizon)

    def pair(self, first, second, horizon):
        if first == second:
            return self._tail(first, horizon)
        worlds = tuple(sorted((first, second), key=lambda w: (w[0], repr(w[1]))))
        key = worlds, horizon
        if key in self.pair_cache:
            return self.pair_cache[key]
        terminal = self._terminal(worlds, horizon)
        if terminal is not None:
            return terminal
        self._charge('pair_nodes')
        best = inf
        for action, cost in self.costs.items():
            if cost >= best:
                continue
            (left, obs_left), (right, obs_right) = (self._step(w, action) for w in worlds)
            if obs_left == obs_right:
                tail = self.pair(left, right, horizon - 1)
            else:
                tail = max(self._tail(left, horizon - 1), self._tail(right, horizon - 1))
            best = min(best, cost + tail)
        self.pair_cache[key] = best
        return best

    def information_lower(self, belief, horizon):
        key = belief, horizon
        if key in self.bound_cache:
            return self.bound_cache[key]
        self.bound_stats['calls'] += 1
        worlds = tuple(sorted(belief, key=lambda w: (w[0], repr(w[1]))))
        lower = 0
        try:
            if self.mode in ('single', 'pair_exact', 'capacity_single'):
                for world in worlds:
                    lower = max(lower, self.singleton(world, horizon))
                    if lower == inf:
                        break
            if self.mode in ('pair_lp', 'pair_exact') and lower < inf:
                for left, right in combinations(worlds, 2):
                    lower = max(lower, self.pair(left, right, horizon))
                    if lower == inf:
                        break
        except BoundBudgetExceeded:
            # A partial min over actions is an UPPER bound, so interrupted DP
            # nodes are never cached or used. Only finished projections count.
            lower = max(lower, max(self.relax[n].lower(s, horizon) for n, s in worlds))
        if self.coverage is not None:
            lower = max(lower, self.coverage.lower(belief, horizon))
        self.bound_cache[key] = lower
        return lower

    def initial(self, belief, horizon):
        base = super().initial(belief, horizon)
        if base.exact or self.mode == 'lp':
            return base
        lower = max(base.lower, self.information_lower(belief, horizon))
        return Result(lower, inf)

    def statistics(self):
        return dict(self.bound_stats, search_expanded=self.expanded, search_pruned=self.pruned,
                    cached_singletons=len(self.single_cache), cached_pairs=len(self.pair_cache),
                    coverage=dict(self.coverage.stats) if self.coverage is not None else None,
                    lp_calls=sum(r.calls for r in self.relax.values()),
                    lp_certificates={k: sum(r.certificates[k] for r in self.relax.values())
                                     for k in ('dual', 'farkas', 'zero_fallback')})
