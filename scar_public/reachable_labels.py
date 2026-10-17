"""Candidate-labelled, resource-aware pattern reachability for witness channels.

Small Boolean patterns retain dynamic progress; labels are initial-world IDs.
An interval transition graph over-approximates concrete transitions, including
transitions out of goal states. Completed graph closures give necessary reachable
valuations for each ID. Independent shortest resource distances tighten these
sets without claiming that their witnesses form a jointly executable path.

The auxiliary patterns are constraints, NOT new observations or policy state.
C0 and CL use identical constrained channels and the original common projection.
Interrupted pattern construction is discarded, never used as an upper bound.
This is a labelled reachability abstraction, not a claim that label propagation
itself is new. The question tested here is its interaction with identity capacity.
"""
from collections import defaultdict, deque
from heapq import heappop, heappush
from math import inf
from time import perf_counter
import z3
from scar_public.symbolic_task import atoms
from scar_public.demand_coverage import formula, simplify, junction, negate
from scar_public.decision_coverage import DecisionCoverage, DecisionPlanner
from scar_public.budgeted_planner import InferenceStop
from scar_public.symbolic_coverage import Unavailable


# Possibilities: false=1, true=2, either=3. Repeated unknown occurrences may be
# independent: this only adds transitions. Keep exact simultaneous add-wins form.
def possible(expr, lookup):
    if type(expr) is bool:
        return 2 if expr else 1
    if type(expr) is int:
        v = lookup(abs(expr)-1)
        return v if expr > 0 else ((v & 1) << 1) | ((v & 2) >> 1)
    op, args = expr
    if op == 'not':
        v = possible(args[0], lookup)
        return ((v & 1) << 1) | ((v & 2) >> 1)
    vs = [possible(a, lookup) for a in args]
    if op == 'and':
        return (1 if any(v & 1 for v in vs) else 0) | (2 if all(v & 2 for v in vs) else 0)
    if op == 'or':
        return (1 if all(v & 1 for v in vs) else 0) | (2 if any(v & 2 for v in vs) else 0)
    if op == 'oneof':
        low, high = sum(v == 2 for v in vs), sum(bool(v & 2) for v in vs)
        return (2 if low <= 1 <= high else 0) | (1 if low != 1 or high != 1 else 0)
    raise ValueError(op)


def select_patterns(task, width=3, limit=24):
    """Deterministic syntax-only selection; no solutions or benchmark outcomes."""
    adjacency = defaultdict(lambda: defaultdict(int))
    for a in task.actions.values():
        pre = atoms(a.pre)
        for guard, lit in a.effects:
            target = abs(lit)-1
            for i in (pre | atoms(guard)) & task.dynamic:
                if i != target:
                    adjacency[target][i] += 1
                    adjacency[i][target] += 1
    varying = {i for i in task.dynamic if len({bool(s & (1 << i)) for s in task.initial_bits}) > 1}
    goal = atoms(task.goal_expr)
    # Include constant-initial progress: its later reachability can depend on a
    # model-specific immutable guard, even when dynamic initial values agree.
    order = sorted(task.dynamic, key=lambda i: (i not in varying, i not in goal, i in task.projection, i))
    patterns = []
    for i in order:
        neighbors = sorted(adjacency[i], key=lambda j: (j not in task.projection, -adjacency[i][j], j))
        pat = tuple(sorted({i, *neighbors[:width-1]}))
        if pat not in patterns:
            patterns.append(pat)
        if len(patterns) >= limit:
            break
    return tuple(patterns)


class LabelClosure:
    def __init__(self, task, check, patterns=None, work_limit=100000):
        self.task, self.check = task, check
        self.patterns = select_patterns(task) if patterns is None else tuple(tuple(sorted(p)) for p in patterns)
        if any(len(p) > 12 or not set(p) <= task.dynamic for p in self.patterns):
            raise ValueError('patterns must contain at most twelve dynamic atoms')
        self.work_limit = work_limit
        self.completed = []
        self.ready = False
        self.stats = dict(patterns_requested=len(self.patterns), patterns_completed=0,
            graph_nodes=0, graph_action_checks=0, graph_edges=0, distance_relaxations=0,
            interrupted=False, seconds=0., signature_calls=0, signature_hits=0,
            candidate_groups=0, max_candidate_groups=0)
        self.signatures = {}
        self.static_groups = defaultdict(list)
        for i, b in enumerate(task.static_bits):
            self.static_groups[b].append(i)
        self.effects = {}
        for a in task.actions.values():
            ad, de = defaultdict(list), defaultdict(list)
            for g, lit in a.effects:
                (ad if lit > 0 else de)[abs(lit)-1].append(g)
            self.effects[a.name] = ad, de

    def tick(self):
        self.check()
        if self.stats['graph_action_checks'] + self.stats['distance_relaxations'] >= self.work_limit:
            raise InferenceStop()

    def successors(self, pat, static, value, action):
        pset = set(pat)
        def lookup(i):
            if i not in self.task.dynamic:
                return 2 if static & (1 << i) else 1
            return (2 if value & (1 << i) else 1) if i in pset else 3
        if not possible(action.pre, lookup) & 2:
            return ()
        ad, de = self.effects[action.name]
        result = [0]
        for i in pat:
            av = possible(('or', tuple(ad.get(i, ()))), lookup)
            dv = possible(('or', tuple(de.get(i, ()))), lookup)
            before = lookup(i)
            yes = bool(av & 2) or bool(before & 2 and dv & 1)
            no = bool(av & 1) and (bool(before & 1) or bool(dv & 2))
            result = [v | bit for v in result for bit in ([0] if no else []) + ([1 << i] if yes else [])]
        return tuple(result)

    def build_pattern(self, pat):
        pmask = sum(1 << i for i in pat)
        # Each candidate keeps its own initial pattern valuation. Candidates with
        # the same (immutable facts, initial pattern) share graph distances.
        data = {}
        for static, names in self.static_groups.items():
            initials = {self.task.initial_bits[i] & pmask for i in names}
            queue = deque(sorted(initials)); seen = set(initials); graph = {}
            while queue:
                self.tick(); s = queue.popleft(); edges = {}
                self.stats['graph_nodes'] += 1
                for a in self.task.actions.values():
                    self.tick(); self.stats['graph_action_checks'] += 1
                    for nxt in self.successors(pat, static, s, a):
                        # Preserve different resource vectors; parallel edges
                        # can be useful in different single-resource relaxations.
                        edges[nxt, a.consumption] = None
                        if nxt not in seen:
                            seen.add(nxt); queue.append(nxt)
                graph[s] = tuple(edges)
                self.stats['graph_edges'] += len(edges)
            for init in sorted(initials):
                reach = {init}; todo = [init]
                while todo:
                    self.tick()
                    for nxt, _ in graph[todo.pop()]:
                        if nxt not in reach:
                            reach.add(nxt); todo.append(nxt)
                distances = []
                for r in range(len(self.task.resources)):
                    dist = {init: 0}; heap = [(0, init)]
                    while heap:
                        self.tick(); cost, s = heappop(heap)
                        if cost != dist[s]:
                            continue
                        for nxt, consumption in graph[s]:
                            self.stats['distance_relaxations'] += 1
                            c = cost + consumption[r]
                            if c < dist.get(nxt, inf):
                                dist[nxt] = c; heappush(heap, (c, nxt))
                    distances.append(dist)
                data[static, init] = tuple(sorted(reach)), tuple(distances)
        return pat, pmask, data

    def prepare(self):
        if self.ready:
            return
        started = perf_counter()
        try:
            for pat in self.patterns:
                record = self.build_pattern(pat)
                # Atomic publication: never use an unfinished reachable set.
                self.completed.append(record)
                self.stats['patterns_completed'] += 1
        except InferenceStop:
            self.stats['interrupted'] = True
        finally:
            self.ready = True
            self.stats['seconds'] += perf_counter()-started

    def groups(self, resources):
        self.stats['signature_calls'] += 1
        if resources in self.signatures:
            self.stats['signature_hits'] += 1
            return self.signatures[resources]
        spent = tuple(inf for _ in self.task.resources) if resources is None else tuple(a-b for a, b in zip(self.task.resources, resources))
        if any(x < 0 for x in spent):
            raise ValueError('remaining resources exceed initial resources')
        groups = defaultdict(int)
        for i, initial in enumerate(self.task.initial_bits):
            self.check(); static = self.task.static_bits[i]; restrictions = []
            for pat, pmask, data in self.completed:
                reach, ds = data[static, initial & pmask]
                allowed = tuple(v for v in reach if all(d.get(v, inf) <= c for d, c in zip(ds, spent)))
                if len(allowed) < 1 << len(pat):
                    restrictions.append((pat, allowed))
            groups[static, tuple(restrictions)] |= 1 << i
        answer = tuple((static, restrictions, mask) for (static, restrictions), mask in groups.items())
        self.stats['candidate_groups'] += len(answer)
        self.stats['max_candidate_groups'] = max(self.stats['max_candidate_groups'], len(answer))
        if len(self.signatures) < 4096:
            self.signatures[resources] = answer
        return answer


class ReachableCoverage(DecisionCoverage):
    def __init__(self, task, patterns=None, use_distances=True):
        super().__init__(task)
        self.labels = LabelClosure(task, self.check, patterns)
        self.use_distances = use_distances
        self.label_patterns = {}
        self.label_contexts = {}
        self.label_stats = dict(channel_patterns=0, sat_calls=0, constant_patterns=0,
            label_mask_splits=0, context_builds=0, context_hits=0, precondition_skips=0)

    def canonical(self, key, horizon):
        # Remaining resources now also encode a forward-reachability constraint.
        # The old horizon clipping preserves unconstrained channels but would
        # erase this information (allowing fictitious expenditure before q).
        return key

    @property
    def stats(self):
        return dict(super().stats, reachable_labels=dict(self.labels.stats), labelled_channels=dict(self.label_stats))

    def context(self, static, restrictions, projected):
        self.check()
        key = static, restrictions, projected
        if key in self.label_contexts:
            self.label_stats['context_hits'] += 1
            return self.label_contexts[key]
        self.label_stats['context_builds'] += 1
        t = self.task
        known = {i: bool(static & (1 << i)) for i in range(len(t.zvars)) if i not in t.dynamic}
        known.update((i, bool(projected & (1 << i))) for i in t.projection)
        # Condition the reachable pattern sets on the current common projection,
        # then propagate literals. This reduces SAT and channel-assembly work.
        filtered = []
        for pat, allowed in restrictions:
            values = tuple(v for v in allowed if all(bool(v & (1 << i)) == known[i] for i in pat if i in known))
            if not values:
                self.label_contexts[key] = None
                return None
            for i in pat:
                bits = {bool(v & (1 << i)) for v in values}
                if len(bits) == 1:
                    value = next(iter(bits))
                    if i in known and known[i] != value:
                        self.label_contexts[key] = None
                        return None
                    known[i] = value
            filtered.append((pat, values))
        def before(i):
            return known.get(i, t.zvars[i])
        invariant = junction((junction((junction((before(i) if v & (1 << i) else negate(before(i))
            for i in pat), True) for v in values), False) for pat, values in filtered), True)
        result = known, simplify(invariant)
        self.label_contexts[key] = result
        return result

    def labelled_pattern(self, static, restrictions, projected, action):
        self.check()
        key = static, restrictions, projected, action.name
        if key in self.label_patterns:
            return self.label_patterns[key]
        context = self.context(static, restrictions, projected)
        if context is None:
            self.label_patterns[key] = False, ()
            return False, ()
        t = self.task
        known, invariant = context
        def before(i):
            return known.get(i, t.zvars[i])
        condition = simplify(junction((invariant, formula(action.pre, before), negate(formula(t.goal_expr, before))), True))
        if condition is False:
            self.label_patterns[key] = False, ()
            return False, ()
        adds, deletes = self.effect_index[action.name]; after_cache = {}
        def after(i):
            if i not in after_cache:
                add = junction((formula(g, before) for g in adds.get(i, ())), False)
                delete = junction((formula(g, before) for g in deletes.get(i, ())), False)
                after_cache[i] = simplify(junction((add, junction((before(i), negate(delete)), True)), False))
            return after_cache[i]
        goal = simplify(formula(t.goal_expr, after))
        observation = [] if action.observation is None else [simplify(formula(action.observation, after))]
        outputs = observation + [after(i) for i in t.projection]
        signature = tuple(str(v) if type(v) is bool else v.sexpr() for v in [condition, goal]+outputs), len(observation)
        if signature in self.formula_patterns:
            self.label_patterns[key] = self.formula_patterns[signature]
            return self.label_patterns[key]
        def decode(v):
            return tuple(v[:len(observation)]), sum(1 << i for i, b in zip(t.projection, v[len(observation):]) if b)
        if condition is True and type(goal) is bool and all(type(v) is bool for v in outputs):
            result = goal, () if goal else (decode(outputs),)
            self.label_stats['constant_patterns'] += 1
        else:
            solver = z3.Solver(); solver.set(timeout=1000); solver.add(condition)
            def check():
                self.check(); self.label_stats['sat_calls'] += 1
                ans = solver.check()
                if ans == z3.unknown:
                    raise Unavailable('labelled channel SAT unknown')
                return ans == z3.sat
            solver.push(); solver.add(goal); immediate = check(); solver.pop()
            solver.add(negate(goal)); outcomes = []
            while check():
                m = solver.model()
                values = [v if type(v) is bool else z3.is_true(m.eval(v, model_completion=True)) for v in outputs]
                outcomes.append(decode(values))
                if len(outcomes) > self.outcome_limit:
                    raise Unavailable('labelled channel outcome limit')
                solver.add(z3.Or(*[v != b for v, b in zip(outputs, values)]))
            result = immediate, tuple(outcomes)
        self.label_stats['channel_patterns'] += 1
        self.label_patterns[key] = result
        self.formula_patterns[signature] = result
        return result

    def get_channels(self, key):
        self.check()
        if key in self.channels:
            return self.channels[key]
        self.labels.prepare(); self.check()
        self._stats['channel_queries'] += 1
        resources, projected = key
        signature_resources = resources if self.use_distances else None
        groups = self.labels.groups(signature_resources)
        self.label_stats['label_mask_splits'] += len(groups) > len(self.group_masks)
        records = []
        def common(i):
            if i in self.task.projection:
                return bool(projected & (1 << i))
            return self.common_values.get(i, self.task.zvars[i])
        for action in self.task.actions.values():
            self.check()
            if any(r < c for r, c in zip(resources, action.consumption)):
                continue
            if simplify(formula(action.pre, common)) is False:
                self.label_stats['precondition_skips'] += 1
                continue
            goals = 0; buckets = defaultdict(int)
            for static, restrictions, mask in groups:
                immediate, outcomes = self.labelled_pattern(static, restrictions, projected, action)
                if immediate:
                    goals |= mask
                for obs, nxt in outcomes:
                    buckets[obs, nxt] |= mask
            if goals or buckets:
                remaining = tuple(r-c for r, c in zip(resources, action.consumption))
                records.append((action.name, goals, tuple((m, (remaining, nxt)) for (_, nxt), m in sorted(buckets.items()))))
        self.mask_channels[key] = tuple(records)
        self.channels[key] = tuple((a, g.bit_count(), tuple((m.bit_count(), q) for m, q in cs)) for a, g, cs in records)
        return self.channels[key]


class ReachablePlanner(DecisionPlanner):
    def __init__(self, task, mode='reachable_relation'):
        if mode not in ('reachable_count', 'reachable_relation'):
            raise ValueError(mode)
        super().__init__(task, 'count_threshold' if mode == 'reachable_count' else 'relation_threshold')
        self.target_coverage = ReachableCoverage(task)
