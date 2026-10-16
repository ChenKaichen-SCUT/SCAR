"""A resource-indexed upper relaxation of policy model coverage.

This is an offline candidate criterion, not an established novelty claim.
Required interface: finite deterministic models, unit action costs, observable
completion (as in finite_planner), and a common observed resource vector in the
queried belief. Symbolic states are relaxed away. Ambiguous resource observations
disable the criterion rather than support an unsound infeasibility conclusion.
"""
from math import inf


class ObservationCapacity:
    def __init__(self, models, goal, allowed):
        self.goal, self.allowed = goal, allowed
        self.model_count = len(models)
        self.channels, self.cache = {}, {}
        self.stats = dict(compiled_transitions=0, dp_nodes=0, lower_calls=0,
                          inapplicable_queries=0, disabled_reason=None)
        if any(cost != 1 for model in models for cost in model.costs.values()):
            self.stats['disabled_reason'] = 'requires unit action costs'
            return
        temporary, completion_observations = {}, {}
        for model in models:
            for (state, action), case in model.lookup.items():
                if not allowed(state) or goal.holds(state):
                    continue
                self.stats['compiled_transitions'] += 1
                successor = case.apply(state)
                if not allowed(successor):
                    continue  # Such a trajectory cannot count toward safe coverage.
                observation_key = state.resources, action, case.observation
                completion_observations.setdefault(observation_key, set()).add(goal.holds(successor))
                if len(completion_observations[observation_key]) > 1:
                    self.stats['disabled_reason'] = 'completion is not observable'
                    self.channels.clear()
                    return
                record = temporary.setdefault((state.resources, action), [set(), {}])
                if goal.holds(successor):
                    record[0].add(model.name)
                else:
                    bucket = record[1].setdefault(case.observation, [set(), set()])
                    bucket[0].add(model.name)
                    bucket[1].add(successor.resources)
        for (resource, action), (goals, observations) in temporary.items():
            if any(len(resources) != 1 for _, resources in observations.values()):
                self.stats['disabled_reason'] = 'same observation permits different successor resources'
                self.channels.clear()
                return
            channels = tuple((len(names), next(iter(resources)))
                             for names, resources in observations.values())
            self.channels.setdefault(resource, []).append((action, len(goals), channels))

    def capacity(self, resource, horizon):
        """Upper bound on distinct models a safe depth-h policy can complete."""
        if horizon == 0:
            return 0
        key = resource, horizon
        if key in self.cache:
            return self.cache[key]
        self.stats['dp_nodes'] += 1
        best = 0
        for _, immediate, channels in self.channels.get(resource, ()):
            covered = immediate
            for possible_models, successor_resource in channels:
                covered += min(possible_models, self.capacity(successor_resource, horizon - 1))
            best = max(best, min(self.model_count, covered))
            if best == self.model_count:
                break
        self.cache[key] = best
        return best

    def lower(self, belief, horizon):
        self.stats['lower_calls'] += 1
        if self.stats['disabled_reason']:
            self.stats['inapplicable_queries'] += 1
            return 0
        if any(not self.allowed(state) for _, state in belief):
            return inf
        complete = [self.goal.holds(state) for _, state in belief]
        if all(complete):
            return 0
        resources = {state.resources for _, state in belief}
        if any(complete) or len(resources) != 1:
            self.stats['inapplicable_queries'] += 1
            return 0
        resource = next(iter(resources))
        required = len({name for name, _ in belief})
        for steps in range(1, horizon + 1):
            if self.capacity(resource, steps) >= required:
                return steps
        return inf
