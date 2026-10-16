"""Compute the same existential channels from only the formulas actually read.

No new relaxation or heuristic: pre-state literals and required successor atoms
are substituted on demand. Fully constant queries are decided directly; all
remaining symbolic queries use the original bounded SAT/outcome protocol.
"""
from collections import defaultdict
import z3
from scar_public.relational_coverage import RelationalCoverage
from scar_public.symbolic_coverage import Unavailable


def negate(value):
    return not value if type(value) is bool else z3.Not(value)


def junction(values, conjunction):
    pending = []
    for value in values:
        if type(value) is bool:
            if value != conjunction:
                return not conjunction
        else:
            pending.append(value)
    if not pending:
        return conjunction
    if len(pending) == 1:
        return pending[0]
    return z3.And(pending) if conjunction else z3.Or(pending)


def formula(expr, lookup):
    if type(expr) is bool:
        return expr
    if type(expr) is int:
        value = lookup(abs(expr)-1)
        return value if expr > 0 else negate(value)
    op, args = expr
    if op == 'not':
        return negate(formula(args[0], lookup))
    if op in ('and', 'or'):
        return junction((formula(x, lookup) for x in args), op == 'and')
    if op == 'oneof':
        values = [formula(x, lookup) for x in args]
        count = sum(v is True for v in values)
        pending = [v for v in values if type(v) is not bool]
        if count > 1:
            return False
        if not pending:
            return count == 1
        return z3.PbEq([(v, 1) for v in pending], 1-count)
    raise ValueError(op)


def simplify(value):
    if type(value) is bool:
        return value
    value = z3.simplify(value)
    if z3.is_true(value):
        return True
    if z3.is_false(value):
        return False
    return value


class DemandCoverage(RelationalCoverage):
    def __init__(self, task, mode='matching', node_limit=5000):
        super().__init__(task, mode, node_limit)
        self.effect_index = {}
        for a in task.actions.values():
            adds, deletes = defaultdict(list), defaultdict(list)
            for guard, lit in a.effects:
                (adds if lit > 0 else deletes)[abs(lit)-1].append(guard)
            self.effect_index[a.name] = adds, deletes
        self.common_values = {}
        for i in range(len(task.zvars)):
            if i not in task.dynamic:
                values = {bool(bits & (1 << i)) for bits in task.static_bits}
                if len(values) == 1:
                    self.common_values[i] = next(iter(values))
        self.demand_stats = dict(pre_atom_reads=0, successor_atoms=0, constant_patterns=0)

    @property
    def stats(self):
        return dict(super().stats, demand=dict(self.demand_stats))

    def pattern(self, static, projected, action):
        key = static, projected, action.name
        if key in self.patterns:
            return self.patterns[key]
        t = self.task
        def before(i):
            self.demand_stats['pre_atom_reads'] += 1
            if i not in t.dynamic:
                return bool(static & (1 << i))
            if i in t.projection:
                return bool(projected & (1 << i))
            return t.zvars[i]
        condition = simplify(junction((formula(action.pre, before),
            negate(formula(t.goal_expr, before))), True))
        if condition is False:
            self.patterns[key] = (False, ())
            return self.patterns[key]
        adds, deletes = self.effect_index[action.name]
        after_cache = {}
        def after(i):
            if i not in after_cache:
                self.demand_stats['successor_atoms'] += 1
                add = junction((formula(g, before) for g in adds.get(i, ())), False)
                delete = junction((formula(g, before) for g in deletes.get(i, ())), False)
                after_cache[i] = simplify(junction((add,
                    junction((before(i), negate(delete)), True)), False))
            return after_cache[i]
        goal = simplify(formula(t.goal_expr, after))
        obs = [] if action.observation is None else [simplify(formula(action.observation, after))]
        outputs = obs + [after(i) for i in t.projection]
        signature = tuple(str(v) if type(v) is bool else v.sexpr()
            for v in [condition, goal] + outputs), len(obs)
        if signature in self.formula_patterns:
            self.patterns[key] = self.formula_patterns[signature]
            return self.patterns[key]
        def decode(values):
            return tuple(values[:len(obs)]), sum(1 << i for i, b in
                zip(t.projection, values[len(obs):]) if b)
        if condition is True and type(goal) is bool and all(type(v) is bool for v in outputs):
            result = goal, () if goal else (decode(outputs),)
            self.demand_stats['constant_patterns'] += 1
        else:
            solver = z3.Solver();solver.set(timeout=1000);solver.add(condition)
            def check():
                self._stats['sat_calls'] += 1
                answer = solver.check()
                if answer == z3.unknown:
                    raise Unavailable('SAT query returned unknown')
                return answer == z3.sat
            solver.push();solver.add(goal);immediate = check();solver.pop()
            solver.add(negate(goal));outcomes = []
            while check():
                model = solver.model()
                values = [v if type(v) is bool else z3.is_true(model.eval(v, model_completion=True))
                    for v in outputs]
                outcomes.append(decode(values))
                if len(outcomes) > self.outcome_limit:
                    raise Unavailable('abstract outcome enumeration limit')
                solver.add(z3.Or(*[v != b for v, b in zip(outputs, values)]))
            result = immediate, tuple(outcomes)
        self._stats['sat_patterns'] += 1
        self._stats['abstract_outcomes'] += len(result[1])
        self.patterns[key] = result
        self.formula_patterns[signature] = result
        return result

    def get_channels(self, key):
        if key in self.channels:
            return self.channels[key]
        self._stats['channel_queries'] += 1
        resources, projected = key
        def common(i):
            if i in self.task.projection:
                return bool(projected & (1 << i))
            return self.common_values.get(i, self.task.zvars[i])
        records = []
        for a in self.task.actions.values():
            if any(r < c for r, c in zip(resources, a.consumption)):
                continue
            if simplify(formula(a.pre, common)) is False:
                continue
            nxt_resources = tuple(r-c for r, c in zip(resources, a.consumption))
            goal_mask, buckets = 0, defaultdict(int)
            for static, names in self.group_masks.items():
                immediate, outcomes = self.pattern(static, projected, a)
                if immediate:
                    goal_mask |= names
                for obs, nxt in outcomes:
                    buckets[obs, nxt] |= names
            channels = tuple((names, (nxt_resources, nxt)) for (obs, nxt), names in sorted(buckets.items()))
            records.append((a.name, goal_mask, channels))
        self.mask_channels[key] = tuple(records)
        self.channels[key] = tuple((a, f.bit_count(), tuple((u.bit_count(), q) for u, q in children))
            for a, f, children in records)
        return self.channels[key]


from scar_public.threshold_search import ThresholdPlanner


class DemandPlanner(ThresholdPlanner):
    def __init__(self, task, mode='matching', node_limit=5000):
        if mode not in self.MODES:
            raise ValueError(mode)
        super().__init__(task, 'single')
        if mode != 'single':
            self.coverage = DemandCoverage(task, mode, node_limit)
