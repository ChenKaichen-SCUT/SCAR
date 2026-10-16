"""Exact dependency-keyed channel cores shared across progress projections.

Unwritten projected atoms are copied, never independently enumerated. Cache keys
retain every read dependency and its known/unknown status; no relaxation changes.
"""
from collections import defaultdict
from time import perf_counter
import z3
from scar_public.symbolic_task import atoms
from scar_public.demand_coverage import formula, negate, junction, simplify
from scar_public.symbolic_coverage import Unavailable
from scar_public.decision_coverage import DecisionCoverage, DecisionPlanner
from scar_public.certificate_refinement import RefinementCoverage, projection_view, indices
from scar_public.direct_saturation import SaturationCoverage


class ChannelPool:
    def __init__(self, task):
        self.task = task
        self.specs = {}; self.patterns = {}; self.channels = {}
        self.effects = {}; self.targets = {}
        self.goals = atoms(task.goal_expr)
        self.stats = dict(pattern_hits=0, pattern_misses=0, channel_hits=0,
            channel_misses=0, sat_calls=0, core_outcomes=0, copied_outputs=0,
            formula_seconds=0., sat_seconds=0.)
        for name, a in task.actions.items():
            adds, deletes = defaultdict(list), defaultdict(list)
            for guard, lit in a.effects:
                (adds if lit > 0 else deletes)[abs(lit)-1].append(guard)
            self.effects[name] = adds, deletes
            self.targets[name] = set(adds) | set(deletes)

    def spec(self, projection, action):
        key = projection, action.name
        if key in self.specs:
            return self.specs[key]
        outputs = tuple(i for i in projection if i in self.targets[action.name])
        post = self.goals | set(outputs) | (atoms(action.observation) if action.observation is not None else set())
        support = atoms(action.pre) | self.goals | post
        adds, deletes = self.effects[action.name]
        for i in post:
            for guard in tuple(adds.get(i, ())) + tuple(deletes.get(i, ())):
                support |= atoms(guard)
        read = sum(1 << i for i in support)
        static = read & ~self.task.dynamic_mask
        retained = read & sum(1 << i for i in projection)
        copied = sum(1 << i for i in projection if i not in self.targets[action.name])
        result = outputs, static, retained, copied
        self.specs[key] = result
        return result

    def pattern(self, owner, static, projected, action, spec):
        owner.check()
        outputs, static_mask, retained, _ = spec
        known_mask = static_mask | retained
        values = (static | projected) & known_mask
        key = action.name, outputs, known_mask, values
        if key in self.patterns:
            self.stats['pattern_hits'] += 1
            return self.patterns[key]
        self.stats['pattern_misses'] += 1
        started = perf_counter()
        def before(i):
            return bool(values & (1 << i)) if known_mask & (1 << i) else self.task.zvars[i]
        condition = simplify(junction((formula(action.pre, before),
            negate(formula(self.task.goal_expr, before))), True))
        adds, deletes = self.effects[action.name]
        after_cache = {}
        def after(i):
            if i not in after_cache:
                add = junction((formula(g, before) for g in adds.get(i, ())), False)
                delete = junction((formula(g, before) for g in deletes.get(i, ())), False)
                after_cache[i] = simplify(junction((add,
                    junction((before(i), negate(delete)), True)), False))
            return after_cache[i]
        if condition is False:
            result = False, ()
            self.stats['formula_seconds'] += perf_counter()-started
        else:
            goal = simplify(formula(self.task.goal_expr, after))
            observation = [] if action.observation is None else [simplify(formula(action.observation, after))]
            expressions = observation + [after(i) for i in outputs]
            self.stats['formula_seconds'] += perf_counter()-started
            def decode(v):
                return tuple(v[:len(observation)]), sum(1 << i for i,b in zip(outputs,v[len(observation):]) if b)
            if condition is True and type(goal) is bool and all(type(e) is bool for e in expressions):
                result = goal, () if goal else (decode(expressions),)
            else:
                solver = z3.Solver(); solver.set(timeout=1000); solver.add(condition)
                def check():
                    owner.check(); self.stats['sat_calls'] += 1; now = perf_counter()
                    answer = solver.check()
                    self.stats['sat_seconds'] += perf_counter()-now
                    if answer == z3.unknown:
                        raise Unavailable('incremental channel SAT unknown')
                    return answer == z3.sat
                solver.push(); solver.add(goal); immediate = check(); solver.pop()
                solver.add(negate(goal)); outcomes = []
                while check():
                    model = solver.model()
                    vals = [e if type(e) is bool else z3.is_true(model.eval(e,model_completion=True)) for e in expressions]
                    outcomes.append(decode(vals))
                    if len(outcomes) > owner.outcome_limit:
                        raise Unavailable('incremental outcome limit')
                    solver.add(z3.Or(*[e != v for e,v in zip(expressions,vals)]))
                result = immediate, tuple(outcomes)
        self.stats['core_outcomes'] += len(result[1])
        if len(self.patterns) < 100000:
            self.patterns[key] = result
        return result

    def action_channels(self, owner, projected, action):
        spec = self.spec(owner.task.projection, action)
        outputs, static_mask, retained, copied = spec
        key = action.name, outputs, retained, projected & retained
        if key in self.channels:
            self.stats['channel_hits'] += 1
            goal_mask, core = self.channels[key]
        else:
            self.stats['channel_misses'] += 1
            goal_mask = 0; buckets = defaultdict(int)
            for static, names in owner.group_masks.items():
                immediate, outcomes = self.pattern(owner,static,projected,action,spec)
                if immediate:
                    goal_mask |= names
                for obs, nxt in outcomes:
                    buckets[obs,nxt] |= names
            core = tuple((obs,nxt,names) for (obs,nxt),names in sorted(buckets.items()))
            if len(self.channels) < 100000:
                self.channels[key] = goal_mask, core
        carry = projected & copied
        self.stats['copied_outputs'] += copied.bit_count()
        return goal_mask, tuple((obs,nxt|carry,names) for obs,nxt,names in core)


class IncrementalChannels:
    def __init__(self, task, *args, pool=None, **kwargs):
        super().__init__(task,*args,**kwargs)
        if pool is not None:
            assert task.actions is pool.task.actions and task.initial_bits == pool.task.initial_bits
        self.channel_pool = pool if pool is not None else ChannelPool(task)

    def pattern(self, static, projected, action):
        pool = self.channel_pool; spec = pool.spec(self.task.projection,action)
        immediate, core = pool.pattern(self,static,projected,action,spec)
        carry = projected & spec[3]
        return immediate, tuple((obs,nxt|carry) for obs,nxt in core)

    def get_channels(self, key):
        self.check()
        if key in self.channels:
            return self.channels[key]
        self._stats['channel_queries'] += 1
        resources, projected = key; records = []
        for action in self.task.actions.values():
            self.check()
            if any(r < c for r,c in zip(resources,action.consumption)):
                continue
            goals, core = self.channel_pool.action_channels(self,projected,action)
            # An action with no possible success or live successor contributes
            # exactly zero. Its omission cannot change C0 or C1 maxima.
            if not goals and not core:
                continue
            remaining = tuple(r-c for r,c in zip(resources,action.consumption))
            channels = tuple((names,(remaining,nxt)) for _,nxt,names in core)
            records.append((action.name,goals,channels))
        self.mask_channels[key] = tuple(records)
        self.channels[key] = tuple((a,g.bit_count(),tuple((m.bit_count(),q) for m,q in cs)) for a,g,cs in records)
        return self.channels[key]

    @property
    def stats(self):
        return dict(super().stats, incremental_pool=dict(self.channel_pool.stats,
            patterns=len(self.channel_pool.patterns), channel_cores=len(self.channel_pool.channels)))


class IncrementalCoverage(IncrementalChannels, DecisionCoverage):
    pass


class IncrementalRefinementCoverage(IncrementalChannels, RefinementCoverage):
    def decide(self, belief, budget, mode='relation_gate'):
        self.refinement_stats['queries'] += 1
        live = [(n,s) for n,s in belief if not self.task.goal.holds(s)]
        if budget < 1 or len(live) < 2 or len({self.project(s) for _,s in live}) != 1:
            return False, dict(reason='refinement_inapplicable')
        started = perf_counter()
        try:
            extra, evidence = self.select(live)
        finally:
            self.refinement_stats['selection_seconds'] += perf_counter()-started
        if not extra:
            prune, old = SaturationCoverage.decide(self,belief,budget,mode)
            return prune, dict(old,refinement=evidence)
        self.refinement_stats['selected'] += 1
        self.refinement_stats['added_atoms'] += extra.bit_count()
        evidence = dict(evidence,selection='certificate',
            added_atoms=[self.task.atom_names[i] for i in indices(extra)],
            known_values=[bool(live[0][1].symbols[0] & (1<<i)) for i in indices(extra)])
        if extra not in self.refined:
            if len(self.refined) >= 16:
                self.refinement_stats['refinement_cache_limit'] += 1
                return False,dict(reason='refinement_cache_limit',refinement=evidence)
            self.check()
            self.refined[extra] = IncrementalCoverage(projection_view(self.task,extra),pool=self.channel_pool)
        refined = self.refined[extra]; refined.deadline = self.deadline
        self.refinement_stats['refined_queries'] += 1; started = perf_counter()
        try:
            prune, answer = refined.decide(belief,budget,'relation_threshold')
        finally:
            self.refinement_stats['inference_seconds'] += perf_counter()-started
        if prune:
            self.refinement_stats['refined_'+('scalar' if answer['reason']=='scalar_prune' else 'relation')+'_prunes'] += 1
        else:
            self.refinement_stats['refined_passes'] += 1
        return prune,dict(answer,reason='refined_'+answer['reason'],refinement=evidence)


class IncrementalPlanner(DecisionPlanner):
    def __init__(self, task, mode='incremental_refinement'):
        if mode != 'incremental_refinement':
            raise ValueError(mode)
        super().__init__(task,'relation_gate')
        self.target_coverage = IncrementalRefinementCoverage(task)
