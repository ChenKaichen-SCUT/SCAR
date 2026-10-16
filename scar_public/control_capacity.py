"""Coverage relaxation retaining a declared, known symbolic control projection.

The original resource-only implementation and its six planner modes are frozen.
This refinement never reads a model ID through the projection. A current belief
must agree on the projected state; an observation must determine its successor.
If that contract fails, the original resource-only criterion is used lazily.
"""
from math import inf

from scar_public.information_bound import InformationBoundPlanner
from scar_public.observation_capacity import ObservationCapacity


class ControlCapacity:
    def __init__(self, models, goal, allowed, symbol_indices=()):
        indices = tuple(symbol_indices)
        if len(set(indices)) != len(indices) or any(type(i) is not int or i < 0 for i in indices):
            raise ValueError('projection must contain distinct nonnegative symbolic indices')
        if any(i >= len(m.domains) for m in models for i in indices):
            raise ValueError('symbolic projection outside a model schema')
        self.indices = indices
        self.models, self.goal, self.allowed = models, goal, allowed
        self.model_count = len(models)
        self.channels, self.cache, self.fallback = {}, {}, None
        self._stats = dict(compiled_transitions=0, dp_nodes=0, lower_calls=0,
                           inapplicable_queries=0, disabled_reason=None,
                           abstract_states=0, action_channels=0, observation_channels=0)
        if any(cost != 1 for model in models for cost in model.costs.values()):
            self._stats['disabled_reason'] = 'requires unit action costs'
            return
        temporary, completion = {}, {}
        for model in models:
            for (state, action), case in model.lookup.items():
                if not allowed(state) or goal.holds(state):
                    continue
                self._stats['compiled_transitions'] += 1
                successor = case.apply(state)
                if not allowed(successor):
                    continue
                key = self.project(state)
                obs_key = key, action, case.observation
                done = goal.holds(successor)
                previous = completion.setdefault(obs_key, done)
                if previous != done:
                    self._stats['disabled_reason'] = 'completion is not observable'
                    return
                record = temporary.setdefault((key, action), [set(), {}])
                if done:
                    record[0].add(model.name)
                else:
                    bucket = record[1].setdefault(case.observation, [set(), set()])
                    bucket[0].add(model.name)
                    bucket[1].add(self.project(successor))
        for (key, action), (goals, observations) in temporary.items():
            if any(len(successors) != 1 for _, successors in observations.values()):
                self._stats['disabled_reason'] = 'same observation permits different successor projections'
                self.channels.clear()
                return
            channels = tuple((len(names), next(iter(successors)))
                             for names, successors in observations.values())
            self.channels.setdefault(key, []).append((action, len(goals), channels))
            self._stats['action_channels'] += 1
            self._stats['observation_channels'] += len(channels)
        self._stats['abstract_states'] = len(self.channels)

    def project(self, state):
        return state.resources, tuple(state.symbols[i] for i in self.indices)

    @property
    def stats(self):
        result = dict(self._stats, symbol_indices=list(self.indices),
                      cached_entries=len(self.cache),
                      fallback=dict(self.fallback.stats) if self.fallback is not None else None)
        # Totals include fallback work; fine-only counters remain available.
        result['fine_compiled_transitions'] = self._stats['compiled_transitions']
        result['fine_dp_nodes'] = self._stats['dp_nodes']
        if self.fallback is not None:
            result['compiled_transitions'] += self.fallback.stats['compiled_transitions']
            result['dp_nodes'] += self.fallback.stats['dp_nodes']
        return result

    def coarse_lower(self, belief, horizon):
        self._stats['inapplicable_queries'] += 1
        if self.fallback is None:
            self.fallback = ObservationCapacity(self.models, self.goal, self.allowed)
        return self.fallback.lower(belief, horizon)

    def capacity(self, key, horizon):
        if horizon == 0:
            return 0
        memo_key = key, horizon
        if memo_key in self.cache:
            return self.cache[memo_key]
        self._stats['dp_nodes'] += 1
        best = 0
        for _, immediate, channels in self.channels.get(key, ()):
            covered = immediate
            for possible_models, successor_key in channels:
                covered += min(possible_models, self.capacity(successor_key, horizon - 1))
            best = max(best, min(self.model_count, covered))
            if best == self.model_count:
                break
        self.cache[memo_key] = best
        return best

    def lower(self, belief, horizon):
        self._stats['lower_calls'] += 1
        if self._stats['disabled_reason']:
            return self.coarse_lower(belief, horizon)
        if any(not self.allowed(s) for _, s in belief):
            return inf
        complete = [self.goal.holds(s) for _, s in belief]
        if all(complete):
            return 0
        keys = {self.project(s) for _, s in belief}
        if any(complete) or len(keys) != 1:
            return self.coarse_lower(belief, horizon)
        key = next(iter(keys))
        required = len({name for name, _ in belief})
        for steps in range(1, horizon + 1):
            if self.capacity(key, steps) >= required:
                return steps
        return inf


class ControlInformationPlanner(InformationBoundPlanner):
    """Original exact search/tail bounds, replacing only the coverage object."""
    def __init__(self, models, goal, allowed=lambda s: True, *, base='lp', symbol_indices=()):
        if base not in ('lp', 'single'):
            raise ValueError('base must be lp or single')
        # Avoid constructing the coarse table before replacing it.
        super().__init__(models, goal, allowed, mode=base)
        self.mode = 'capacity_' + base
        self.coverage = ControlCapacity(models, goal, allowed, symbol_indices)
