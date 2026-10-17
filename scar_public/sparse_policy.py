"""Sparse candidate/time constraints for optimistic bounded policy coverage.

No abstract belief-prefix graph is enumerated. Each admitted candidate has a
bounded trace; actions agree while actual observation histories agree. Omitted
dynamic atom links are existentially free. A candidate may retire immediately
after a goal witness (the same optimistic credit convention as coverage bounds).
Only UNSAT prunes. SAT traces are refinement proposals, never real plans.

Candidate sampling and counterexample refinement are established ideas (CPCES,
CEGAR); this implementation makes no originality claim for those ingredients.
"""
from collections import defaultdict
from itertools import combinations
from time import perf_counter
import z3
from scar_public.symbolic_task import atoms
from scar_public.demand_coverage import formula, junction, negate
from scar_public.budgeted_planner import InferenceStop
from scar_public.symbolic_coverage import Unavailable
from scar_public.amortized_refinement import AmortizedCoverage
from scar_public.decision_coverage import DecisionPlanner
from scar_public.finite_planner import State


def obs_code(obs):
    return 0 if not obs else 2 if obs[0] else 1


class SparseEncoding:
    def __init__(self, task, horizon, check=lambda: None):
        self.task = task; self.horizon = horizon; self.check_work = check
        self.solver = z3.Solver(); self.frames = {}; self.actions = tuple(task.actions.values())
        self.effects = {}; self.writers = defaultdict(list)
        for j, action in enumerate(self.actions):
            adds, deletes = defaultdict(list), defaultdict(list)
            for guard, lit in action.effects:
                (adds if lit > 0 else deletes)[abs(lit)-1].append(guard)
            self.effects[j] = adds, deletes
            for p in set(adds) | set(deletes):
                self.writers[p].append(j)
        self.goals = atoms(task.goal_expr) & task.dynamic
        self.has_observations = any(a.observation is not None for a in self.actions)
        self.shared_actions = [z3.Int(f'common_a_{t}') for t in range(horizon)]
        self.stats = dict(frames=0, links_built=0, checks=0, sat_seconds=0., build_seconds=0.,
            refinements=0, added_links=0, concrete_steps=0, counterexamples=0,
            peak_candidates=0, cores=[], rounds=0)

    def add_candidate(self, name, state, pattern=None):
        self.check_work()
        if name in self.frames:
            return self.frames[name]
        started = perf_counter(); h = self.horizon; task = self.task
        f = dict(name=name, state=state, use=z3.Bool(f'use_{name}'),
            x={}, post={}, links={}, retained=set(),
            a=([z3.Int(f'a_{name}_{t}') for t in range(h)] if self.has_observations else self.shared_actions),
            done=[z3.Bool(f'done_{name}_{t}') for t in range(h+1)],
            obs=[z3.Int(f'obs_{name}_{t}') for t in range(h)])
        def before(t, p):
            if p not in task.dynamic:
                return bool(state.symbols[0] & (1 << p))
            if (t, p) not in f['x']:
                f['x'][t, p] = z3.Bool(f'x_{name}_{t}_{p}')
            return f['x'][t, p]
        def after(t, p):
            if (t, p) not in f['post']:
                value = before(t, p)
                for j in self.writers.get(p, ()):
                    adds, deletes = self.effects[j]
                    add = junction((formula(g, lambda i: before(t, i)) for g in adds.get(p, ())), False)
                    delete = junction((formula(g, lambda i: before(t, i)) for g in deletes.get(p, ())), False)
                    effect = junction((add, junction((before(t, p), negate(delete)), True)), False)
                    value = z3.If(f['a'][t] == j, effect, value)
                f['post'][t, p] = value
            return f['post'][t, p]
        f['before'] = before; f['after'] = after
        constraints = [z3.Not(f['done'][0]), f['done'][h]]
        for t in range(h):
            self.check_work(); live = z3.Not(f['done'][t]); choice = f['a'][t]
            constraints.append(z3.Implies(live, z3.And(choice >= 0, choice < len(self.actions))))
            for j, action in enumerate(self.actions):
                pre = formula(action.pre, lambda p: before(t, p))
                if pre is not True:
                    constraints.append(z3.Implies(z3.And(live, choice == j), pre))
            goal = formula(task.goal_expr, lambda p: after(t, p))
            constraints.append(f['done'][t+1] == z3.Or(f['done'][t], goal))
            observation = z3.IntVal(0)
            for j, action in enumerate(self.actions):
                if action.observation is not None:
                    sense = formula(action.observation, lambda p: after(t, p))
                    observation = z3.If(choice == j, z3.If(sense, 2, 1), observation)
            constraints.append(f['obs'][t] == observation)
        for dimension, resource in enumerate(state.resources):
            terms = []
            for t in range(h):
                cost = sum(z3.If(f['a'][t] == j, a.consumption[dimension], 0)
                    for j, a in enumerate(self.actions) if a.consumption[dimension])
                terms.append(z3.If(f['done'][t], 0, cost))
            constraints.append(z3.Sum(terms) <= resource)
        # Publishing only complete frames prevents interrupted construction from
        # being mistaken for a complete abstraction in a later query.
        self.solver.add(z3.Implies(f['use'], z3.And(*constraints)))
        if self.has_observations:
            for other in self.frames.values():
                same = z3.BoolVal(True); pair = z3.And(f['use'], other['use'])
                for t in range(h):
                    self.check_work()
                    self.solver.add(z3.Implies(z3.And(pair, same, z3.Not(f['done'][t]),
                        z3.Not(other['done'][t])), f['a'][t] == other['a'][t]))
                    same = z3.And(same, f['obs'][t] == other['obs'][t])
        self.frames[name] = f
        for p in sorted(self.goals | (set(pattern) if pattern is not None else set())):
            self.link(f, p); f['retained'].add(p)
        self.stats['frames'] += 1; self.stats['peak_candidates'] = len(self.frames)
        self.stats['build_seconds'] += perf_counter()-started
        return f

    def link(self, f, p):
        if p not in self.task.dynamic:
            raise ValueError('only dynamic atoms have temporal links')
        if p in f['links']:
            return f['links'][p]
        self.check_work(); label = z3.Bool(f'link_{f["name"]}_{p}')
        constraints = [f['before'](0, p) == bool(f['state'].symbols[0] & (1 << p))]
        for t in range(self.horizon):
            self.check_work()
            constraints.append(z3.Implies(z3.Not(f['done'][t]), f['before'](t+1, p) == f['after'](t, p)))
        self.solver.add(z3.Implies(z3.And(f['use'], label), z3.And(*constraints)))
        f['links'][p] = label; self.stats['links_built'] += 1
        return label

    def assumptions(self):
        return [v for f in self.frames.values() for v in [f['use']]+[f['links'][p] for p in sorted(f['retained'])]]

    def check(self, assumptions=None, deadline=float('inf')):
        self.check_work(); remaining = deadline-perf_counter()
        if remaining <= 0:
            raise InferenceStop()
        self.solver.set(timeout=max(1, min(1000, int(remaining*1000))) if remaining != float('inf') else 1000)
        start = perf_counter(); self.stats['checks'] += 1
        answer = self.solver.check(*(self.assumptions() if assumptions is None else assumptions))
        self.stats['sat_seconds'] += perf_counter()-start
        if answer == z3.unknown:
            raise Unavailable('sparse policy solver: '+self.solver.reason_unknown())
        return answer

    def certificate(self, labels=None, minimal=False):
        core = {str(x) for x in (self.solver.unsat_core() if labels is None else labels)}
        members = [n for n, f in self.frames.items() if str(f['use']) in core]
        links = {n: sorted(p for p, label in f['links'].items() if str(label) in core)
            for n, f in self.frames.items()}
        assert members, 'An empty task core is an encoding error'
        return dict(members=members, links={n: p for n, p in links.items() if p},
            core_labels=sorted(core), minimal=minimal)

    def minimize_certificate(self, deadline=float('inf'), limit=64):
        """Optional offline deletion minimization; retain a proved core on stop."""
        core = list(self.solver.unsat_core()); complete = True
        try:
            for index, label in enumerate(tuple(core)):
                if index >= limit:
                    complete = False; break
                trial = [x for x in core if str(x) != str(label)]
                if self.check(trial, deadline) == z3.unsat:
                    core = trial
        except (InferenceStop, Unavailable):
            complete = False
        return self.certificate(core, minimal=complete)

    def rule(self, certificate):
        rows = []
        for name in certificate['members']:
            f = self.frames[name]; state = f['state']
            mask = sum(1 << p for p in certificate['links'].get(name, ()))
            rows.append(dict(name=name, mask=mask, value=state.symbols[0] & mask,
                static=state.symbols[0] & ~self.task.dynamic_mask, resources=list(state.resources)))
        return dict(horizon=self.horizon, rows=rows, certificate=certificate)

    def proposals(self, model):
        policy = {}; traces = {}
        for name, f in self.frames.items():
            history = (); trace = []
            for t in range(self.horizon):
                if z3.is_true(model.eval(f['done'][t], model_completion=True)):
                    break
                action = model.eval(f['a'][t], model_completion=True).as_long()
                observation = model.eval(f['obs'][t], model_completion=True).as_long()
                if history in policy:
                    assert policy[history] == action, 'nonanticipativity violation'
                policy[history] = action; trace.append((action, observation)); history += (observation,)
            traces[name] = trace
        return policy, traces

    def validate(self, worlds, policy, first_only=False):
        failures = []
        for name, state in sorted(worlds, key=lambda x: x[0]):
            self.check_work(); current = state; history = (); reason = None
            for _ in range(self.horizon):
                if self.task.goal.holds(current):
                    break  # optimistic goal credit, never a real-plan claim
                if history not in policy:
                    reason = 'unrepresented_observation'; break
                action = self.actions[policy[history]].name
                current, obs = self.task.step(current, action)
                self.stats['concrete_steps'] += 1
                if not self.task.allowed(current):
                    reason = 'invalid_action'; break
                history += (obs_code(obs),)
            if reason is None and not self.task.goal.holds(current):
                reason = 'goal_not_reached'
            if reason is not None:
                failures.append((name, state, reason))
                if first_only:
                    break
        self.stats['counterexamples'] += len(failures)
        return failures

    def refine(self, name, trace, deadline=float('inf')):
        """Restore only a sufficient temporal-link core for this one trace.

        A core is sufficient to exclude the spurious proposal, not necessarily
        minimum, nor evidence that the full task is infeasible.
        """
        f = self.frames[name]
        if len(self.task.dynamic) > 128:
            return None
        for p in sorted(self.task.dynamic):
            self.link(f, p)
        base = [f['use']]+[f['links'][p] for p in sorted(f['retained'])]
        full = [f['use']]+[f['links'][p] for p in sorted(self.task.dynamic)]
        self.solver.push()
        try:
            for t, (action, obs) in enumerate(trace):
                self.solver.add(z3.Implies(z3.Not(f['done'][t]),
                    z3.And(f['a'][t] == action, f['obs'][t] == obs)))
            self.solver.add(f['done'][len(trace)])
            if self.check(base, deadline) != z3.sat:
                raise AssertionError('extracted trace is not a witness')
            if self.check(full, deadline) != z3.unsat:
                return None
            core = {str(v) for v in self.solver.unsat_core()}
            extra = {p for p, label in f['links'].items() if str(label) in core} - f['retained']
            assert extra, 'failed concrete trace needs a missing progress link'
        finally:
            self.solver.pop()
        f['retained'] |= extra
        self.stats['refinements'] += 1; self.stats['added_links'] += len(extra)
        self.stats['cores'].append(dict(candidate=name, added_atoms=[self.task.atom_names[p] for p in sorted(extra)]))
        return extra

    def run(self, worlds, deadline=float('inf'), candidate_limit=8, rounds=16, patterns=None, full=False):
        live = sorted(((n,s) for n,s in worlds if not self.task.goal.holds(s)), key=lambda w:w[0])
        if not live:
            return False, dict(reason='no_live_candidates')
        patterns = {} if patterns is None else patterns
        self.add_candidate(*live[0], pattern=self.task.dynamic if full else patterns.get(live[0][0]))
        for _ in range(rounds):
            self.stats['rounds'] += 1
            if self.check(deadline=deadline) == z3.unsat:
                return True, dict(reason='sparse_policy_prune', certificate=self.certificate(),
                    candidates=len(live), selected=len(self.frames), upper=len(live)-1)
            policy, traces = self.proposals(self.solver.model())
            failures = self.validate([(n,s) for n,s in live if n in self.frames], policy, first_only=True)
            if not failures:
                failures = self.validate([(n,s) for n,s in live if n not in self.frames], policy, first_only=True)
            if not failures:
                return False, dict(reason='optimistic_policy_pass', selected=len(self.frames))
            # Repair the represented candidate before adding another one; this
            # prevents a spurious local transition from causing sample growth.
            failed = next((f for f in failures if f[0] in self.frames), failures[0])
            name, state, _ = failed
            if name in self.frames:
                if self.refine(name, traces[name], deadline) is None:
                    return False, dict(reason='refinement_unavailable')
            elif len(self.frames) < candidate_limit:
                self.add_candidate(name, state, pattern=self.task.dynamic if full else patterns.get(name))
            else:
                return False, dict(reason='candidate_limit', selected=len(self.frames))
        return False, dict(reason='round_limit', selected=len(self.frames))


class SparsePolicyCoverage(AmortizedCoverage):
    def __init__(self, task, reuse=True, full=False):
        super().__init__(task)
        self.learned_links = {}; self.rules = []; self.reuse = reuse; self.full = full
        self.sparse_stats = dict(queries=0, prunes=0, interrupted=0, seconds=0.,
            frames=0, added_links=0, sat_seconds=0., build_seconds=0., cores=[], rule_hits=0)

    def match_rule(self, belief, budget):
        live = {n:s for n,s in belief if not self.task.goal.holds(s)}
        for rule in self.rules:
            if budget > rule['horizon']:
                continue
            for row in rule['rows']:
                state = live.get(row['name'])
                if state is None or state.symbols[0] & row['mask'] != row['value']:
                    break
                if state.symbols[0] & ~self.task.dynamic_mask != row['static']:
                    break
                if any(r > old for r,old in zip(state.resources,row['resources'])):
                    break
            else:
                return rule
        return None

    @property
    def stats(self):
        return dict(super().stats, sparse_policy=dict(self.sparse_stats))

    def decide(self, belief, budget, mode='relation_threshold'):
        rule = self.match_rule(belief,budget) if self.reuse else None
        if rule is not None:
            self.sparse_stats['rule_hits'] += 1
            return True,dict(reason='sparse_core_reuse',budget=budget,rule=rule)
        prune, coarse = super().decide(belief, budget, mode)
        if prune or budget > 24 or len(self.task.actions) > 256:
            return prune, coarse
        self.check(); started = perf_counter(); self.sparse_stats['queries'] += 1
        encoding = SparseEncoding(self.task, budget, self.check)
        try:
            prune, answer = encoding.run(belief, self.deadline, patterns=self.learned_links if self.reuse else None, full=self.full)
            if prune:
                answer['rule'] = encoding.rule(answer['certificate'])
            self.sparse_stats['prunes'] += prune
            if prune and len(self.sparse_stats['cores']) < 32:
                self.sparse_stats['cores'].append(dict(budget=budget, **answer))
            if prune and self.reuse and len(self.rules) < 128:
                self.rules.append(answer['rule'])
            return prune, dict(answer, coarse=coarse)
        except (InferenceStop, Unavailable):
            self.sparse_stats['interrupted'] += 1
            raise
        finally:
            # Facts to retain are reusable choices; initial truth values and
            # every transition are rebuilt from this query, never reused as
            # immutable state. No old UNSAT result is transferred here.
            for name, frame in encoding.frames.items():
                self.learned_links[name] = self.learned_links.get(name, set()) | frame['retained']
            self.sparse_stats['seconds'] += perf_counter()-started
            for k in ('frames', 'added_links', 'sat_seconds', 'build_seconds'):
                self.sparse_stats[k] += encoding.stats[k]


class SparsePolicyPlanner(DecisionPlanner):
    def __init__(self, task, mode='sparse_policy'):
        if mode not in ('sparse_policy', 'sparse_fresh', 'sparse_full'):
            raise ValueError(mode)
        super().__init__(task, 'relation_threshold')
        self.target_coverage = SparsePolicyCoverage(task, reuse=mode!='sparse_fresh', full=mode=='sparse_full')


def replay_rule(task, rule, deadline=float('inf')):
    """Rebuild a saved proof obligation, without its original solver or prefixes.

    Unlinked initial dynamic values are deliberately arbitrary: no assumed
    temporal link may read them. This is a fresh encoding replay, not a separate
    verified SMT proof checker. Malformed labels/rows are rejected, never trusted.
    """
    encoding = SparseEncoding(task, rule['horizon'])
    expected = set(rule['certificate']['members'])
    assert len(rule['rows']) == len(expected)
    assert {r['name'] for r in rule['rows']} == expected
    for row in rule['rows']:
        pattern = rule['certificate']['links'].get(row['name'], [])
        assert row['mask'] == sum(1 << p for p in pattern)
        assert row['value'] & ~row['mask'] == 0
        assert row['static'] & task.dynamic_mask == 0
        state = State((row['static'] | row['value'], True), tuple(row['resources']))
        encoding.add_candidate(row['name'], state, pattern=pattern)
    available = {str(f['use']) for f in encoding.frames.values()} | {
        str(label) for f in encoding.frames.values() for label in f['links'].values()}
    labels = rule['certificate']['core_labels']
    assert set(labels) <= available
    return encoding.check([z3.Bool(s) for s in labels], deadline) == z3.unsat


def compress_rule(task, belief, rule, deadline, checks=32):
    """Optional certificate postprocessing; no prefix graph and no new prune.

    Try singles/pairs inside the existing core, restoring their true progress
    facts. A smaller candidate core can require more facts per candidate. This
    bounded search is not global minimum-certificate optimization. Retain the
    old proved rule on interruption. Full current states are REQUIRED: forgotten
    values cannot be reconstructed from the old sparse rule.
    """
    current = {n:s for n,s in belief}
    for row in rule['rows']:
        state = current[row['name']]
        assert state.symbols[0] & row['mask'] == row['value']
        assert state.symbols[0] & ~task.dynamic_mask == row['static']
        assert tuple(state.resources) == tuple(row['resources'])
    stats = dict(tests=0, candidate_reduced=False, unknown=False)
    names = sorted(rule['certificate']['members'])
    if len(names) < 2 or len(task.dynamic) > 128:
        return rule, stats
    def check():
        if perf_counter() >= deadline:
            raise InferenceStop()
    encoding = SparseEncoding(task, rule['horizon'], check)
    try:
        for size in (1,2):
            if size >= len(names):
                break
            for subset in combinations(names,size):
                if stats['tests'] >= checks:
                    return rule,stats
                assumptions=[]
                for name in subset:
                    f=encoding.add_candidate(name,current[name],task.dynamic)
                    assumptions += [f['use']]+list(f['links'].values())
                stats['tests'] += 1
                if encoding.check(assumptions,deadline)==z3.unsat:
                    cert=encoding.minimize_certificate(deadline,limit=64)
                    stats['candidate_reduced']=True
                    return encoding.rule(cert),stats
    except (InferenceStop,Unavailable):
        stats['unknown']=True
    return rule,stats
