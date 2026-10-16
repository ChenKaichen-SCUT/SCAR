"""Resource-aware observation-tree control, independent of capacity abstractions.

For each world, compute the largest number of Boolean observations on a legal
goal-reaching path within the *joint* horizon/resource budget. For each pair,
exhaust a synchronous open-loop search with those same budgets. Incompatible
pairs must terminate at different policy leaves. A conflict clique K therefore
obeys sum(2**-max_observations[w] for w in K) <= 1 (Kraft's inequality).

This is our explicit stronger research control, not a reproduction of an
existing planner. A timed-out subproblem contributes no negative evidence.
All arithmetic in the final certificate is integer, not floating point.
"""
from itertools import combinations
from time import perf_counter
from scar_public.budgeted_planner import InferenceStop


class ResourceInformation:
    def __init__(self, task, work_limit=300000):
        self.task = task
        self.work_limit = work_limit
        self.deadline = float('inf')
        self.transitions, self.max_cache, self.open_cache = {}, {}, {}
        self.stats = dict(work=0, max_nodes=0, open_nodes=0, pairs=0,
                          conflicts=0, interrupted=0, queries=0, prunes=0, seconds=0.)

    def check(self):
        if self.stats['work'] >= self.work_limit or perf_counter() >= self.deadline:
            raise InferenceStop()
        self.stats['work'] += 1

    def actions(self, state):
        return self.task.applicable(state) if hasattr(self.task, 'applicable') else self.task.actions

    def step(self, state, action):
        key = state, action
        if key not in self.transitions:
            self.check()
            self.transitions[key] = self.task.step(state, action)
        return self.transitions[key][0]

    def sensor_ceiling(self, state, depth):
        senses = [a for a in self.task.actions.values() if a.observation is not None]
        if not senses:
            return 0
        cap = depth
        for i, r in enumerate(state.resources):
            minimum = min(a.consumption[i] for a in senses)
            if minimum:
                cap = min(cap, r // minimum)
        return cap

    def max_observations(self, state, depth):
        """-1 means no goal-reaching trajectory; goal states may continue."""
        if not self.task.allowed(state):
            return -1
        key = state, depth
        if key in self.max_cache:
            return self.max_cache[key]
        self.check(); self.stats['max_nodes'] += 1
        best = 0 if self.task.goal.holds(state) else -1
        ceiling = self.sensor_ceiling(state, depth)
        if depth and best < ceiling:
            for action in self.actions(state):
                nxt = self.step(state, action)
                if not self.task.allowed(nxt):
                    continue
                tail = self.max_observations(nxt, depth-1)
                if tail >= 0:
                    best = max(best, int(self.task.actions[action].observation is not None)+tail)
                    if best == ceiling:
                        break
        self.max_cache[key] = best
        return best

    def open_loop(self, states, depth):
        """Existence of one action sequence; actual observations are ignored."""
        if any(not self.task.allowed(s) for s in states):
            return False
        if all(self.task.goal.holds(s) for s in states):
            return True
        if not depth:
            return False
        key = states, depth
        if key in self.open_cache:
            return self.open_cache[key]
        self.check(); self.stats['open_nodes'] += 1
        for action in self.actions(states[0]):
            nxt = tuple(self.step(s, action) for s in states)
            if nxt == states:
                continue
            if self.open_loop(nxt, depth-1):
                self.open_cache[key] = True
                return True
        self.open_cache[key] = False
        return False

    def decide(self, belief, depth, mode=None):
        start = perf_counter(); self.stats['queries'] += 1
        worlds = sorted(belief, key=lambda w: w[0])
        caps, edges = {}, {n: set() for n, _ in worlds}
        incomplete = False
        try:
            for name, state in worlds:
                try:
                    caps[name] = self.max_observations(state, depth)
                except InferenceStop:
                    caps[name] = self.sensor_ceiling(state, depth)
                    incomplete = True
                if caps[name] == -1:
                    self.stats['prunes'] += 1
                    return True, dict(reason='single_resource_infeasible', world=name, complete=True)
            try:
                for (n, s), (m, t) in combinations(worlds, 2):
                    self.check(); self.stats['pairs'] += 1
                    if not self.open_loop((s, t), depth):
                        edges[n].add(m); edges[m].add(n)
                        self.stats['conflicts'] += 1
            except InferenceStop:
                incomplete = True
            # Every reported set is a clique. Greedy coloring is NOT used as a
            # lower bound. Trying each vertex also preserves singleton bounds.
            order = sorted(edges, key=lambda n: (caps[n], -len(edges[n]), n))
            scale = max(caps.values(), default=0)
            weight = {n: 1 << (scale-caps[n]) for n in edges}
            best, chosen = 0, []
            for first in order:
                clique = [first]; possible = set(edges[first])
                for n in order:
                    if n in possible:
                        clique.append(n); possible &= edges[n]
                total = sum(weight[n] for n in clique)
                if total > best:
                    best, chosen = total, clique
            prune = best > (1 << scale)
            self.stats['prunes'] += int(prune)
            self.stats['interrupted'] += int(incomplete)
            return prune, dict(reason='resource_kraft_prune' if prune else 'resource_kraft_no_certificate',
                complete=not incomplete, observation_caps=caps, clique=chosen,
                kraft_numerator=best, kraft_denominator=1 << scale,
                conflict_pairs=sum(map(len, edges.values()))//2)
        finally:
            self.stats['seconds'] += perf_counter()-start

    @property
    def decision_stats(self):
        return self.stats


def resource_planner(task):
    from scar_public.decision_coverage import DecisionPlanner
    planner = DecisionPlanner(task,'relation_threshold')
    planner.target_coverage = ResourceInformation(task)
    return planner
