"""Shared unit-cost strong-policy search with budget decisions and reusable bounds.

This is search infrastructure, not a new coverage heuristic. Beliefs are exact;
goal truth is never an observation. A failed decision at d proves only V > d.
No ancestor-dependent cycle pruning is cached. Every recursive edge costs one,
so the finite decision tree is acyclic even when the physical task has cycles.
"""
from collections import deque
from dataclasses import dataclass
from math import inf
from time import perf_counter

from scar_public.finite_planner import Result
from scar_public.symbolic_coverage import LazyCoveragePlanner
from scar_public.relational_coverage import RelationalCoverage


class InterruptedSearch(Exception):
    pass


@dataclass
class Record:
    lower: float = 0
    upper: float = inf
    policy: object = None
    checked: int = -1


class ThresholdPlanner(LazyCoveragePlanner):
    MODES = ('single', 'counts', 'lineage', 'matching')

    def __init__(self, task, mode='matching', node_limit=5000):
        if mode not in self.MODES:
            raise ValueError(mode)
        super().__init__(task, 'single')
        self.coverage = None if mode == 'single' else RelationalCoverage(task, mode, node_limit)
        self.records, self.world_records = {}, {}
        self.edge_cache, self.transition_cache = {}, {}
        self.search_stats = dict(decisions=0, decision_hits=0, bound_prunes=0,
            failed_decisions=0, successful_decisions=0, edges_built=0,
            singleton_seconds=0., coverage_seconds=0., edge_seconds=0.,
            thresholds=[], first_policy_seconds=None, transition_cache_hits=0)
        self.root = None
        self.started = None

    def _step(self, world, action):
        name, state = world
        key = state, action
        self.bound_stats['transition_lookups'] += 1
        if key not in self.transition_cache:
            # SymbolicTask has one transition interpreter for every model label.
            self.transition_cache[key] = self.task.step(state, action)
        else:
            self.search_stats['transition_cache_hits'] += 1
        successor, obs = self.transition_cache[key]
        return (name, successor), obs

    def record(self, belief):
        if belief not in self.records:
            if any(not self.allowed(s) for _, s in belief):
                self.records[belief] = Record(inf, inf)
            elif all(self.goal.holds(s) for _, s in belief):
                self.records[belief] = Record(0, 0, {'stop': True})
            else:
                self.records[belief] = Record(1)
        return self.records[belief]

    def known_world(self, world, budget):
        rec = self.world_records.setdefault(world, Record())
        if rec.lower > budget or rec.upper < inf:
            return rec
        started = perf_counter()
        try:
            if not self.allowed(world[1]):
                rec.lower = inf
                return rec
            if self.goal.holds(world[1]):
                rec.lower = rec.upper = 0
                rec.policy = {'stop': True}
                return rec
            queue = deque([(world, 0)])
            parents = {world: None}
            found = None
            while queue:
                current, depth = queue.popleft()
                self.bound_stats['single_nodes'] += 1
                if depth >= budget:
                    continue
                for action in self.costs:
                    child, obs = self._step(current, action)
                    if not self.allowed(child[1]) or child in parents:
                        continue
                    parents[child] = current, action, obs
                    if self.goal.holds(child[1]):
                        found = child
                        break
                    queue.append((child, depth + 1))
                if found is not None:
                    break
            if found is None:
                rec.lower = max(rec.lower, budget + 1)
                return rec
            # Every suffix of a shortest path to the goal set is also shortest.
            policy = {'stop': True}
            distance = 0
            current = found
            while True:
                suffix = self.world_records.setdefault(current, Record())
                suffix.lower = suffix.upper = distance
                suffix.policy = policy
                if parents[current] is None:
                    break
                parent, action, obs = parents[current]
                policy = dict(action=action, branches={obs: policy})
                distance += 1
                current = parent
            return rec
        finally:
            self.search_stats['singleton_seconds'] += perf_counter() - started

    def estimate(self, belief, budget):
        rec = self.record(belief)
        if rec.lower > budget or rec.lower == rec.upper or rec.checked >= budget:
            return rec
        self.bound_stats['calls'] += 1
        if self.coverage is not None:
            started = perf_counter()
            try:
                value = self.coverage.lower(belief, budget)
            finally:
                self.search_stats['coverage_seconds'] += perf_counter() - started
            # Infinity here certifies bounded infeasibility, not global failure.
            rec.lower = max(rec.lower, budget + 1 if value == inf else value)
        if rec.lower <= budget:
            for world in sorted(belief, key=lambda w: w[0]):
                known = self.known_world(world, budget)
                rec.lower = max(rec.lower, known.lower)
                if len(belief) == 1 and known.upper < inf:
                    rec.upper, rec.policy = known.upper, known.policy
                if rec.lower > budget:
                    break
        rec.checked = budget
        assert rec.lower <= rec.upper
        return rec

    def initial(self, belief, horizon):
        assert belief and horizon >= 0
        rec = self.estimate(belief, horizon)
        if rec.lower > horizon:
            return Result(inf, inf)
        return Result(rec.lower, rec.upper if rec.upper <= horizon else inf,
                      rec.policy if rec.upper <= horizon else None)

    def edges(self, belief):
        if belief in self.edge_cache:
            return self.edge_cache[belief]
        started = perf_counter()
        edges = []
        try:
            for action in self.costs:
                branches = {}
                for world in sorted(belief, key=lambda w: w[0]):
                    child, obs = self._step(world, action)
                    if not self.allowed(child[1]):
                        break
                    branches.setdefault(obs, set()).add(child)
                else:
                    branches = {o: frozenset(ws) for o, ws in branches.items()}
                    if len(branches) == 1 and next(iter(branches.values())) == belief:
                        continue
                    edges.append((action, branches))
            self.search_stats['edges_built'] += len(edges)
            self.edge_cache[belief] = edges
            return edges
        finally:
            self.search_stats['edge_seconds'] += perf_counter() - started

    def decision(self, belief, budget):
        self.search_stats['decisions'] += 1
        rec = self.record(belief)
        if rec.upper <= budget:
            self.search_stats['decision_hits'] += 1
            return True
        if rec.lower > budget:
            self.search_stats['bound_prunes'] += 1
            return False
        rec = self.estimate(belief, budget)
        if rec.upper <= budget:
            return True
        if rec.lower > budget:
            self.search_stats['bound_prunes'] += 1
            return False
        if self.remaining is not None:
            if self.remaining <= 0:
                raise InterruptedSearch()
            self.remaining -= 1
        self.expanded += 1
        edges = self.edges(belief)
        # Ordering only uses already-known bounds; no eager child heuristics.
        order = sorted(edges, key=lambda e: (
            max(self.record(b).lower for b in e[1].values()), e[0]))
        for action, branches in order:
            children = sorted(branches.values(), key=lambda b: (
                self.record(b).lower, len(b)), reverse=True)
            if all(self.decision(child, budget - 1) for child in children):
                value = 1 + max(self.record(b).upper for b in branches.values())
                if value < rec.upper:
                    rec.upper = value
                    rec.policy = dict(action=action, branches={
                        o: self.record(b).policy for o, b in branches.items()})
                self.search_stats['successful_decisions'] += 1
                assert rec.lower <= rec.upper <= budget
                return True
        rec.lower = max(rec.lower, budget + 1)
        if not edges:
            rec.lower = inf
        self.search_stats['failed_decisions'] += 1
        assert rec.lower <= rec.upper
        return False

    def solve(self, belief, horizon, expansion_budget=None):
        assert belief and isinstance(horizon, int) and horizon >= 0
        assert expansion_budget is None or expansion_budget >= 0
        self.root, self.started, self.remaining = belief, perf_counter(), expansion_budget
        rec = self.estimate(belief, horizon)
        try:
            while rec.lower <= horizon and rec.lower < rec.upper:
                budget = int(rec.lower)
                self.search_stats['thresholds'].append(budget)
                if self.decision(belief, budget):
                    break
            if rec.upper <= horizon:
                self.search_stats['first_policy_seconds'] = perf_counter() - self.started
        except InterruptedSearch:
            pass
        if rec.lower > horizon:
            return Result(inf, inf)
        return Result(rec.lower, rec.upper if rec.upper <= horizon else inf,
                      rec.policy if rec.upper <= horizon else None)

    def statistics(self):
        return dict(super().statistics(), threshold=dict(self.search_stats,
            belief_records=len(self.records), world_records=len(self.world_records),
            cached_edges=len(self.edge_cache), cached_transitions=len(self.transition_cache)))
