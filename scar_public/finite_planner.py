"""Finite research reference for SCAR's proposed planner; NOT the TTCL/V6 agent.

Grounded deterministic cases, symbolic-flow/resource-balance LP lower bounds,
exact rational checking of dual/Farkas certificates, and bounded AND/OR search.
Dependencies: Python 3, NumPy, SciPy. No network, API, credentials, or game access.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from fractions import Fraction as F
from functools import lru_cache
from itertools import product
from math import inf, isfinite
from pathlib import Path
from time import perf_counter
import json
import hashlib
import sys
import numpy as np
import scipy
from scipy.optimize import linprog


@dataclass(frozen=True)
class State:
    symbols: tuple
    resources: tuple[int, ...]


@dataclass(frozen=True)
class Guard:
    """Conjunction of finite-domain equalities and integer linear >= constraints."""
    symbols: tuple[tuple[int, object], ...]
    numeric: tuple[tuple[tuple[int, ...], int], ...]

    def accepts(self, s):
        return (all(s.symbols[i] == value for i, value in self.symbols)
                and all(sum(a*r for a, r in zip(row, s.resources)) >= rhs
                        for row, rhs in self.numeric))


@dataclass(frozen=True)
class Case:
    action: str
    guard: Guard
    changes: tuple[tuple[int, object, object], ...]  # variable, source, destination
    delta: tuple[int, ...]
    observation: tuple  # A literal observed tuple in this fully grounded reference.

    def apply(self, s):
        assert self.guard.accepts(s)
        z = list(s.symbols)
        for i, old, new in self.changes:
            assert z[i] == old
            z[i] = new
        return State(tuple(z), tuple(a+b for a, b in zip(s.resources, self.delta)))


@dataclass(frozen=True)
class Goal:
    symbols: tuple[tuple[int, object], ...] = ()
    numeric: tuple[tuple[tuple[int, ...], int], ...] = ()

    def holds(self, s):
        return (all(s.symbols[i] == value for i, value in self.symbols)
                and all(sum(a*r for a, r in zip(row, s.resources)) >= rhs
                        for row, rhs in self.numeric))


@dataclass
class Model:
    name: str
    domains: tuple[tuple, ...]
    bounds: tuple[int, ...]
    costs: dict[str, int]
    cases: tuple[Case, ...]
    lookup: dict = field(repr=False)

    def step(self, s, action):
        case = self.lookup[(s, action)]
        successor = case.apply(s)
        assert all(0 <= r <= upper for r, upper in zip(successor.resources, self.bounds))
        return successor, case.observation


def compile_model(name, domains, bounds, costs, transition):
    """Exact case splitting for tiny examples; not a scalable model compiler.

    All bounded states and commands are represented, including charged failures.
    Cases use exact old-state guards, so the partition is disjoint and exhaustive.
    Equivalent LP columns are merged later, without changing execution cases.
    """
    assert all(domain and len(set(domain)) == len(domain) for domain in domains)
    assert all(isinstance(upper, int) and upper >= 0 for upper in bounds)
    assert costs and all(isinstance(cost, (int, F)) and cost > 0 for cost in costs.values())
    cases, lookup = [], {}
    for symbol_values in product(*domains):
        for resources in product(*(range(u+1) for u in bounds)):
            state = State(tuple(symbol_values), tuple(resources))
            numeric = []
            for i, value in enumerate(resources):
                row = tuple(int(j == i) for j in range(len(bounds)))
                numeric.extend(((row, value), (tuple(-x for x in row), -value)))
            guard = Guard(tuple(enumerate(symbol_values)), tuple(numeric))
            for action in costs:
                successor, observation = transition(name, state, action)
                case = Case(action, guard,
                            tuple((i, old, new) for i, (old, new) in
                                  enumerate(zip(state.symbols, successor.symbols)) if old != new),
                            tuple(y-x for x, y in zip(state.resources, successor.resources)),
                            tuple(observation))
                assert case.apply(state) == successor
                assert all(v in domains[i] for i, v in enumerate(successor.symbols))
                assert all(0 <= r <= bounds[i] for i, r in enumerate(successor.resources))
                cases.append(case)
                assert (state, action) not in lookup
                lookup[(state, action)] = case
    return Model(name, domains, bounds, costs, tuple(cases), lookup)


def rational_vector(values):
    return [max(F(0), F(float(v)).limit_denominator(1_000_000)) for v in values]


class Relaxation:
    """min c*x subject to A*x >= b, x >= 0; only verified dual values are used."""
    def __init__(self, model, goal):
        self.model, self.goal = model, goal
        self.facts = tuple((i, value) for i, domain in enumerate(model.domains) for value in domain)
        fi = {fact: i for i, fact in enumerate(self.facts)}
        columns = set()
        for case in model.cases:
            change = [0] * len(fi)
            for i, old, new in case.changes:
                change[fi[i, old]] -= 1
                change[fi[i, new]] += 1
            columns.add((tuple(change), case.delta, model.costs[case.action]))
        self.columns = tuple(sorted(columns))
        self.symbol_rows = tuple(tuple(col[0][i] for col in self.columns) for i in range(len(fi)))
        self.resource_rows = tuple(tuple(col[1][i] for col in self.columns) for i in range(len(model.bounds)))
        self.c = tuple(col[2] for col in self.columns)
        self.fi = fi
        self.calls = 0
        self.certificates = {'dual': 0, 'farkas': 0, 'zero_fallback': 0}

    def program(self, s, horizon):
        A, b = [], []
        def add(row, rhs):
            A.append(tuple(row)); b.append(rhs)
        for (i, value), row in zip(self.facts, self.symbol_rows):
            z = int(s.symbols[i] == value)
            add(row, -z)  # z_final >= 0
            add(tuple(-x for x in row), z-1)  # z_final <= 1
        for i, row in enumerate(self.resource_rows):
            add(row, -s.resources[i])
            add(tuple(-x for x in row), s.resources[i]-self.model.bounds[i])
        for i, value in self.goal.symbols:
            add(self.symbol_rows[self.fi[i, value]], 1-int(s.symbols[i] == value))
        for coeff, rhs in self.goal.numeric:
            add(tuple(sum(coeff[i]*self.resource_rows[i][j] for i in range(len(coeff)))
                      for j in range(len(self.c))), rhs-sum(a*r for a, r in zip(coeff, s.resources)))
        add(tuple(-1 for _ in self.c), -horizon)
        return tuple(A), tuple(b)

    @lru_cache(None)
    def lower(self, s, horizon):
        if self.goal.holds(s): return F(0)
        A, b = self.program(s, horizon)
        self.calls += 1
        ans = linprog(np.array(self.c, dtype=float), A_ub=-np.array(A, dtype=float),
                      b_ub=-np.array(b, dtype=float), bounds=(0, None), method='highs')
        if ans.status == 0:
            # A feasible primal value is NOT a safe lower bound on a minimization problem.
            # Recover, rationalize and exactly verify a nonnegative dual vector instead.
            y = rational_vector(-ans.ineqlin.marginals)
            lhs = [sum(F(A[i][j])*y[i] for i in range(len(A))) for j in range(len(self.c))]
            scale = min([F(1)] + [F(cost)/value for cost, value in zip(self.c, lhs) if value > cost])
            y = [scale*v for v in y]
            assert all(v >= 0 for v in y)
            assert all(sum(F(A[i][j])*y[i] for i in range(len(A))) <= self.c[j]
                       for j in range(len(self.c)))
            value = max(F(0), sum(F(rhs)*v for rhs, v in zip(b, y)))
            self.certificates['dual'] += 1
            return value
        if ans.status == 2:
            # Infeasibility is used only after exact checking of a Farkas witness:
            # y>=0, A^T y<=0, b^T y>0. Solver status alone is insufficient.
            farkas = linprog(-np.array(b, dtype=float),
                            A_ub=np.vstack((np.array(A, dtype=float).T, np.ones((1, len(A))))),
                            b_ub=np.zeros(len(self.c)).tolist()+[1.0],
                            bounds=(0, None), method='highs')
            if farkas.status == 0:
                y = rational_vector(farkas.x)
                if (all(sum(F(A[i][j])*y[i] for i in range(len(A))) <= 0
                        for j in range(len(self.c)))
                        and sum(F(rhs)*v for rhs, v in zip(b, y)) > 0):
                    self.certificates['farkas'] += 1
                    return inf
        self.certificates['zero_fallback'] += 1
        return F(0)


@dataclass
class Result:
    lower: F | float
    upper: F | float
    policy: object = None

    @property
    def exact(self): return self.lower == self.upper

    @property
    def status(self):
        if self.lower == inf: return 'NO_STRONG_POLICY_WITHIN_H'
        if self.upper < inf: return 'PLAN_FOUND'
        return 'UNKNOWN'


class Planner:
    def __init__(self, models, goal, allowed=lambda s: True, use_lp=True):
        self.models = {m.name: m for m in models}
        self.goal, self.allowed, self.use_lp = goal, allowed, use_lp
        self.costs = dict(models[0].costs)
        assert all(m.costs == self.costs for m in models)
        self.relax = {m.name: Relaxation(m, goal) for m in models}
        self.memo = {}
        self.expanded = self.pruned = 0
        self.remaining = None

    def branches(self, belief, action):
        outcomes = {}
        for name, state in sorted(belief, key=lambda w: (w[0], repr(w[1]))):
            successor, obs = self.models[name].step(state, action)
            outcomes.setdefault(obs, set()).add((name, successor))
        for worlds in outcomes.values():
            assert len({self.goal.holds(s) for _, s in worlds}) == 1, 'Completion must be observable in these instances.'
        return {obs: frozenset(worlds) for obs, worlds in outcomes.items()}

    def initial(self, belief, horizon):
        assert belief, 'An empty actual belief is MODEL_MISMATCH, never solved.'
        key = (belief, horizon)
        if key in self.memo: return self.memo[key]
        if any(not self.allowed(s) for _, s in belief): return Result(inf, inf)
        if all(self.goal.holds(s) for _, s in belief): return Result(F(0), F(0), {'stop': True})
        if horizon == 0: return Result(inf, inf)
        lower = max(self.relax[m].lower(s, horizon) for m, s in belief) if self.use_lp else F(0)
        return Result(lower, inf)

    def solve(self, belief, horizon, expansion_budget=None):
        assert isinstance(horizon, int) and horizon >= 0
        assert expansion_budget is None or (isinstance(expansion_budget, int) and expansion_budget >= 0)
        self.remaining = expansion_budget
        return self._search(belief, horizon)

    def _search(self, belief, horizon):
        base = self.initial(belief, horizon)
        if base.exact: return base
        if self.remaining is not None and self.remaining <= 0: return base
        if self.remaining is not None: self.remaining -= 1
        self.expanded += 1
        edges = []
        for action, cost in self.costs.items():
            branches = self.branches(belief, action)
            children = {obs: self.initial(child, horizon-1) for obs, child in branches.items()}
            lower = F(cost) + max(r.lower for r in children.values())
            edges.append({'action': action, 'cost': F(cost), 'branches': branches,
                          'children': children, 'lower': lower, 'upper': inf, 'policy': None})
        edges.sort(key=lambda edge: (edge['lower'], edge['action']))
        upper, policy = inf, None
        for edge in edges:
            if edge['lower'] >= upper:
                self.pruned += 1
                continue
            order = sorted(edge['children'], key=lambda o: (edge['children'][o].lower, repr(o)), reverse=True)
            for obs in order:
                if self.remaining is not None and self.remaining <= 0: break
                if not edge['children'][obs].exact:
                    edge['children'][obs] = self._search(edge['branches'][obs], horizon-1)
                edge['lower'] = edge['cost'] + max(r.lower for r in edge['children'].values())
                if edge['lower'] >= upper: break
            if all(r.upper < inf for r in edge['children'].values()):
                edge['upper'] = edge['cost'] + max(r.upper for r in edge['children'].values())
                edge['policy'] = {'action': edge['action'],
                                  'branches': {obs: r.policy for obs, r in edge['children'].items()}}
                if edge['upper'] < upper:
                    upper, policy = edge['upper'], edge['policy']
        lower = max(base.lower, min(edge['lower'] for edge in edges))
        answer = Result(lower, upper, policy)
        assert lower <= upper
        if answer.exact: self.memo[(belief, horizon)] = answer
        return answer

    def verify(self, belief, horizon, policy):
        costs = []
        for name, initial in belief:
            state, node, count, cost = initial, policy, 0, 0
            while True:
                assert self.allowed(state)
                if node.get('stop'):
                    assert self.goal.holds(state)
                    break
                assert count < horizon and not self.goal.holds(state)
                action = node['action']
                state, obs = self.models[name].step(state, action)
                count += 1; cost += self.costs[action]
                node = node['branches'][obs]
            costs.append(cost)
        return max(costs)

    def oracle(self):
        """Independent unpruned minimax recursion; it never calls LP or search()."""
        @lru_cache(None)
        def value(belief, horizon):
            if any(not self.allowed(s) for _, s in belief): return inf
            if all(self.goal.holds(s) for _, s in belief): return 0
            if horizon == 0: return inf
            return min(cost + max(value(child, horizon-1) for child in self.branches(belief, a).values())
                       for a, cost in self.costs.items())
        return value


def machine_models():
    domains = ((0, 1, 2, 3), ('live', 'broken', 'done'))
    bounds = (2, 1)  # held material, collectible reserve
    costs = dict.fromkeys(('collect', 'test', 'scan', 'finish_A', 'finish_B'), 1)
    def transition(model, s, action):
        scan, status = s.symbols
        held, reserve = s.resources
        message, reveal = 'ok', None
        if status != 'live': message = 'terminal'
        elif action == 'collect':
            if reserve and held < 2: held += 1; reserve -= 1
            else: message = 'unavailable'
        elif action == 'scan':
            scan = min(scan+1, 3)
            if scan == 3: reveal = model
        elif action == 'test':
            if held: held -= 1; reveal = model
            else: message = 'no_material'
        elif action.startswith('finish_'):
            if held:
                held -= 1
                status = 'done' if action[-1] == model else 'broken'
            else: message = 'no_material'
        nxt = State((scan, status), (held, reserve))
        return nxt, (message, held, reserve, scan, status, reveal)
    return [compile_model(m, domains, bounds, costs, transition) for m in ('A', 'B')]


def document_models():
    domains = (('E', 'O', 'N', 'X'), ('absent', 'E', 'O', 'N', 'X'))
    bounds = (3,)
    costs = dict.fromkeys(('new_D', 'old_D', 'inspect_D', 'new_S', 'old_S', 'inspect_S'), 1)
    def transition(model, s, action):
        target, spare = s.symbols
        ink, = s.resources
        if target == 'N': return s, ('goal', ink, True)
        verb, doc = action.split('_')
        content = target if doc == 'D' else spare
        if content == 'absent': return s, ('missing', ink, False)
        if verb == 'inspect': return s, ('text', doc, content, ink, False)
        if ink == 0: return s, ('no_ink', ink, False)
        payload = 'N' if verb == 'new' else 'O'
        text = payload if model == 'replace' or content == 'E' else 'X'
        if doc == 'D': target = text
        else: spare = text
        return State((target, spare), (ink-1,)), ('written', ink-1, target == 'N')
    return [compile_model(m, domains, bounds, costs, transition) for m in ('append', 'replace')]


def crafting_model(capacity=2):
    domains = (('store', 'forge'), (False, True))
    bounds = (2, 2, 1, 1, 1)  # ore at store, held ore, held ingot, ground sword, held sword
    costs = dict.fromkeys(('to_forge', 'to_store', 'take_ore', 'smelt', 'smith', 'pick_sword'), 1)
    def transition(model, s, action):
        location, crafted = s.symbols
        stock, ore, ingot, ground, sword = s.resources
        message = 'failed'
        if action == 'to_forge': location = 'forge'; message = 'moved'
        elif action == 'to_store': location = 'store'; message = 'moved'
        elif action == 'take_ore' and location == 'store' and stock and ore < 2 and ore+ingot+sword < capacity:
            stock -= 1; ore += 1; message = 'taken'
        elif action == 'smelt' and location == 'forge' and ore >= 2 and ingot == 0:
            ore -= 2; ingot += 1; message = 'smelted'
        elif action == 'smith' and location == 'forge' and ingot and ground == 0:
            ingot -= 1; ground += 1; crafted = True; message = 'crafted'
        elif action == 'pick_sword' and location == 'forge' and ground and sword == 0 and ore+ingot+sword < capacity:
            ground -= 1; sword += 1; message = 'picked'
        nxt = State((location, crafted), (stock, ore, ingot, ground, sword))
        return nxt, (message, location, crafted, *nxt.resources)
    return compile_model('craft', domains, bounds, costs, transition)


def batch_model():
    bounds = (4, 4, 1)  # stock, held ore, held sword
    costs = {'gather_two': 1, 'forge_three': 1}
    def transition(model, s, action):
        stock, ore, sword = s.resources
        message = 'failed'
        if action == 'gather_two' and stock >= 2 and ore <= 2:
            stock -= 2; ore += 2; message = 'taken'
        elif action == 'forge_three' and ore >= 3 and sword == 0:
            ore -= 3; sword = 1; message = 'crafted'
        nxt = State((), (stock, ore, sword))
        return nxt, (message, stock, ore, sword)
    return compile_model('batch', (), bounds, costs, transition)


def printable(x):
    if x == inf: return 'infinity'
    if isinstance(x, F): return int(x) if x.denominator == 1 else str(x)
    return x


def run_checks():
    start = perf_counter()
    rows, solver_stats, checks = [], [], 0

    def exercise(label, planner, initial, horizons):
        nonlocal checks
        oracle = planner.oracle()
        for horizon in horizons:
            expected = oracle(initial, horizon)
            lower = max(planner.relax[m].lower(s, horizon) for m, s in initial)
            assert lower <= expected, (label, horizon, lower, expected)
            result = planner.solve(initial, horizon)
            assert result.exact and result.upper == expected, (label, horizon, result, expected)
            if isfinite(result.upper):
                assert planner.verify(initial, horizon, result.policy) == result.upper
            rows.append({'instance':label, 'horizon':horizon, 'lower':printable(lower),
                         'optimum':printable(expected), 'result':result.status})
            checks += 1
        solver_stats.append({'instance':label, 'expanded_nodes':planner.expanded,
                             'pruned_edges':planner.pruned,
                             'lp_calls':sum(r.calls for r in planner.relax.values()),
                             'certificates':{k:sum(r.certificates[k] for r in planner.relax.values())
                                             for k in ('dual','farkas','zero_fallback')}})

    mm = machine_models()
    mg = Goal(symbols=((1, 'done'),))
    machine = Planner(mm, mg)
    no_reserve = frozenset((m.name, State((0,'live'), (1,0))) for m in mm)
    with_reserve = frozenset((m.name, State((0,'live'), (1,1))) for m in mm)
    exercise('machine_no_reserve', machine, no_reserve, range(0,6))
    exercise('machine_with_reserve', machine, with_reserve, range(0,5))
    assert machine.oracle()(no_reserve,4) == 4
    assert machine.oracle()(with_reserve,3) == 3
    assert max(machine.relax[m].lower(s,4) for m,s in no_reserve) == 1
    assert all(machine.initial(b,3).lower == inf for b in machine.branches(no_reserve,'test').values())
    assert all(machine.initial(b,2).lower == 2 for b in machine.branches(with_reserve,'test').values())
    assert all(machine.oracle()(frozenset([world]),1) == 1 for world in no_reserve)
    assert machine.oracle()(no_reserve,1) == inf
    limited = Planner(mm, mg)
    limited_result = limited.solve(no_reserve,4,expansion_budget=0)
    assert limited_result.status == 'UNKNOWN' and limited_result.lower == 1 and limited_result.upper == inf
    budget_checks = 0
    for initial, horizon, optimum in ((no_reserve,4,4),(with_reserve,3,3)):
        for budget in range(9):
            p = Planner(mm, mg)
            r = p.solve(initial,horizon,expansion_budget=budget)
            assert r.lower <= optimum <= r.upper
            if r.upper < inf: assert p.verify(initial,horizon,r.policy) == r.upper
            budget_checks += 1
    bound_ablation = []
    for use_lp in (False, True):
        p = Planner(mm, mg, use_lp=use_lp)
        r = p.solve(no_reserve,4)
        assert r.exact and r.upper == 4 and p.verify(no_reserve,4,r.policy) == 4
        bound_ablation.append({'use_lp':use_lp,'optimum':4,'expanded_nodes':p.expanded,
                               'pruned_edges':p.pruned,'lp_calls':sum(t.calls for t in p.relax.values())})

    dm = document_models()
    dg = Goal(symbols=((0,'N'),))
    docs = Planner(dm, dg)
    blank = frozenset((m.name, State(('E','absent'), (2,))) for m in dm)
    spare = frozenset((m.name, State(('E','E'), (3,))) for m in dm)
    exercise('blank_document', docs, blank, range(0,5))
    exercise('spare_document', docs, spare, range(0,5))
    assert docs.oracle()(blank,4) == 1
    after_old = next(iter(docs.branches(blank,'old_D').values()))
    assert docs.initial(after_old,3).lower == inf

    cg = Goal(symbols=((1,True),), numeric=(((0,0,0,0,1),1),))
    craft_start = frozenset([('craft', State(('store',False),(2,0,0,0,0)))])
    for capacity in (2,1):
        cp = Planner([crafting_model(capacity)], cg,
                     allowed=lambda s, cap=capacity: sum(s.resources[i] for i in (1,2,4)) <= cap)
        # Capture the initial relaxed value before exact results are cached.
        initial_lb = cp.initial(craft_start,7).lower
        exercise('craft_capacity_'+str(capacity), cp, craft_start, range(0,8))
        assert initial_lb == 5
        assert cp.oracle()(craft_start,7) == (6 if capacity==2 else inf)

    bm = batch_model()
    bg = Goal(numeric=(((0,0,1),1),))
    batch = Planner([bm], bg)
    batch_start = frozenset([('batch',State((),(4,0,0)))])
    assert batch.initial(batch_start,3).lower == F(5,2)
    exercise('batch_fractional_relaxation', batch, batch_start, range(0,5))

    # A concrete exact count vector must satisfy every LP inequality.
    witness_planner = Planner([bm], bg)
    result = witness_planner.solve(batch_start,3)
    assert witness_planner.verify(batch_start,3,result.policy) == 3

    # A feasible primal value can exceed the real optimum: never use it for pruning.
    A, b = batch.relax['batch'].program(next(iter(batch_start))[1], 5)
    # The actual optimal trajectory has cost 3, but inserting two charged failures
    # gives a feasible count vector of cost 5. This is an upper bound, not a lower bound.
    state = next(iter(batch_start))[1]
    actions = ('forge_three','forge_three','gather_two','gather_two','forge_three')
    column_index = {col:i for i,col in enumerate(batch.relax['batch'].columns)}
    counts = [0]*len(column_index)
    for action in actions:
        case = bm.lookup[state,action]
        counts[column_index[((),case.delta,bm.costs[action])]] += 1
        state,_ = bm.step(state,action)
    assert bg.holds(state)
    assert all(sum(a*x for a,x in zip(row,counts)) >= rhs for row,rhs in zip(A,b))
    assert sum(c*x for c,x in zip(batch.relax['batch'].c,counts)) == 5 > 3

    return {'version':'research-reference-0.1','date':'2026-10-16',
            'scope':'Synthetic finite cases only; not integrated with V6 or TTCL.',
            'api_calls':0,'checked_instance_horizon_pairs':checks,
            'all_exact_search_values_match_unpruned_oracle':True,
            'all_finite_returned_policies_replayed_in_all_initial_worlds':True,
            'floating_primal_values_never_used_as_lower_bounds':True,
            'dual_and_farkas_conditions_checked_with_exact_rationals':True,
            'budget_zero_returns_unknown':True,
            'additional_budget_checks':budget_checks,
            'tiny_instance_bound_ablation':bound_ablation,
            'cases':rows,'statistics':solver_stats,
            'special_checks':{'machine_initial_lower_vs_optimum':[1,4],
                              'test_without_reserve_lower':'infinity',
                              'test_with_reserve_continuation_lower':2,
                              'craft_capacity_two_lower_vs_optimum':[5,6],
                              'craft_capacity_one_lower_vs_optimum':[5,'infinity'],
                              'batch_lower_vs_optimum':['5/2',3],
                              'feasible_primal_can_exceed_true_optimum':[5,3],
                              'per_world_one_step_plans_are_not_a_shared_policy':True},
            'runtime_seconds':round(perf_counter()-start,3)}


if __name__ == '__main__':
    result = run_checks()
    result['source_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result['dependencies'] = {'python':sys.version.split()[0], 'numpy':np.__version__, 'scipy':scipy.__version__}
    out = Path(__file__).with_name('SCAR_planning_reference_results.json')
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('cases','statistics')},ensure_ascii=False))
