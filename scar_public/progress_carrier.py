"""Prefix-consistent labelled abstraction: carry (candidate, progress) pairs.

This stronger reference/optional bound closes a gap left by global reachable
envelopes. A successor witness must originate in this candidate's current set,
via the chosen action; it cannot borrow a state reached by another action prefix.
Only actual observations partition children. Auxiliary progress is NOT observed.

Both C0 and CL propagate the SAME labelled progress transition relation. C0 can
double-count an ID with an immediate-goal witness and a non-goal witness; CL
removes immediately credited IDs before recursing. This is a deliberately strong
count control: preserving labelled transition support can itself explain gains.
If every candidate has a unique projected successor/outcome and goal status,
there is no such duplication, so the two recurrences coincide.
"""
from collections import defaultdict
from time import perf_counter
from scar_public.symbolic_task import atoms
from scar_public.certificate_refinement import projection_view
from scar_public.budgeted_planner import MeteredCoverage
from scar_public.decision_coverage import DecisionPlanner


def causal_pattern(task, width=12):
    parents = defaultdict(set)
    for a in task.actions.values():
        for guard, lit in a.effects:
            parents[abs(lit)-1] |= (atoms(a.pre) | atoms(guard)) & task.dynamic
    retained = atoms(task.goal_expr) & task.dynamic
    if len(retained) > width:
        retained = set(sorted(retained)[:width])
    frontier = sorted(retained)
    while frontier and len(retained) < width:
        new = sorted(set().union(*(parents[i] for i in frontier))-retained)
        frontier = new[:width-len(retained)]
        retained.update(frontier)
    return tuple(sorted(retained))


class ProgressCarrier(MeteredCoverage):
    def __init__(self, task, pattern=None, node_limit=50000):
        pattern = causal_pattern(task) if pattern is None else tuple(sorted(pattern))
        if len(pattern) > 16 or not set(pattern) <= task.dynamic:
            raise ValueError('carrier pattern must be <=16 dynamic atoms')
        # Deliberately replace the old common-only projection. This hidden
        # projection can differ between candidates and is never an observation.
        view = projection_view(task, 0)
        view.projection = pattern
        view.projection_mask = sum(1 << i for i in pattern)
        super().__init__(view, 'lineage')
        self.original = task
        self.carrier_edges = {}; self.carrier_cache = {}
        self.carrier_node_limit = node_limit
        self.decision_stats = dict(scalar_queries=0, scalar_prunes=0, relation_queries=0, relation_prunes=0)
        self.carrier_stats = dict(nodes=0, edge_queries=0, edge_hits=0, self_loops=0,
            prefix_state_pairs=0, max_pairs=0, goals_with_live_successors=0,
            node_fallbacks=0,
            pattern_atoms=[task.atom_names[i] for i in pattern])

    @property
    def stats(self):
        return dict(super().stats, progress_carrier=dict(self.carrier_stats))

    def carrier(self, belief):
        live = [(n, s) for n, s in belief if not self.original.goal.holds(s)]
        resources = {s.resources for _, s in live}
        if len(resources) != 1:
            return None
        by_name = defaultdict(set)
        for name, s in live:
            by_name[int(name[1:])].add(s.symbols[0] & self.task.projection_mask)
        return next(iter(resources)), tuple((i, tuple(sorted(v))) for i, v in sorted(by_name.items()))

    def edges(self, key):
        self.check()
        if key in self.carrier_edges:
            self.carrier_stats['edge_hits'] += 1
            return self.carrier_edges[key]
        self.carrier_stats['edge_queries'] += 1
        resources, carrier = key
        self.carrier_stats['prefix_state_pairs'] += sum(len(v) for _, v in carrier)
        self.carrier_stats['max_pairs'] = max(self.carrier_stats['max_pairs'], sum(len(v) for _, v in carrier))
        records = []
        for a in self.task.actions.values():
            self.check()
            if any(r < c for r, c in zip(resources, a.consumption)):
                continue
            goals = 0; buckets = defaultdict(lambda: defaultdict(set))
            for i, values in carrier:
                for value in values:
                    immediate, outcomes = self.pattern(self.task.static_bits[i], value, a)
                    if immediate:
                        goals |= 1 << i
                    for obs, nxt in outcomes:
                        buckets[obs][i].add(nxt)
            remaining = tuple(r-c for r, c in zip(resources, a.consumption))
            children = tuple((remaining, tuple((i, tuple(sorted(v))) for i, v in sorted(b.items())))
                for _, b in sorted(buckets.items()))
            if not goals and not children:
                continue
            if not goals and len(children) == 1 and children[0] == key:
                self.carrier_stats['self_loops'] += 1
                continue
            child_names = 0
            for _, child in children:
                for i, _ in child:
                    child_names |= 1 << i
            self.carrier_stats['goals_with_live_successors'] += bool(goals & child_names)
            records.append((a.name, goals, children))
        self.carrier_edges[key] = tuple(records)
        return self.carrier_edges[key]

    def value(self, key, horizon, identity=False):
        self.check()
        if not horizon or not key[1]:
            return 0
        memo = key, horizon, identity
        if memo in self.carrier_cache:
            return self.carrier_cache[memo]
        if self.carrier_stats['nodes'] >= self.carrier_node_limit:
            # A complete upper fallback, never a partial maximization result.
            self.carrier_stats['node_fallbacks'] += 1
            return len(key[1])
        self.carrier_stats['nodes'] += 1
        ceiling = len(key[1]); best = 0
        for _, goals, children in self.edges(key):
            total = goals.bit_count()
            for resources, child in children:
                if identity and goals:
                    child = tuple((i, v) for i, v in child if not goals & (1 << i))
                total += self.value((resources, child), horizon-1, identity)
                if total >= ceiling:
                    break
            best = max(best, min(ceiling, total))
            if best == ceiling:
                break
        self.carrier_cache[memo] = best
        return best

    def decide(self, belief, budget, mode):
        key = self.carrier(belief)
        if key is None or len(key[1]) < 2:
            return False, dict(reason='carrier_inapplicable')
        n = len(key[1]); self.decision_stats['scalar_queries'] += 1
        count = self.value(key, budget)
        e = dict(candidates=n, budget=budget, scalar=count)
        if count < n:
            self.decision_stats['scalar_prunes'] += 1
            return True, dict(e, reason='scalar_prune')
        if mode == 'count_threshold':
            return False, dict(e, reason='count_pass')
        self.decision_stats['relation_queries'] += 1
        value = self.value(key, budget, True)
        prune = value < n
        self.decision_stats['relation_prunes'] += prune
        return prune, dict(e, identity_capacity=value, reason='relation_prune' if prune else 'relation_pass')


class CarrierPlanner(DecisionPlanner):
    def __init__(self, task, mode='carrier_relation'):
        if mode not in ('carrier_count', 'carrier_relation'):
            raise ValueError(mode)
        super().__init__(task, 'count_threshold' if mode == 'carrier_count' else 'relation_threshold')
        self.target_coverage = ProgressCarrier(task)
