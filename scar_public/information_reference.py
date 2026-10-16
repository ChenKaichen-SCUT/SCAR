"""Independent exhaustive reference; no lower-bound or Planner imports."""
from functools import lru_cache
from math import inf


def branches(instance, belief, action):
    models = {m.name: m for m in instance.models}
    outcomes = {}
    for name, state in belief:
        successor, observation = models[name].step(state, action)
        outcomes.setdefault(observation, set()).add((name, successor))
    return tuple(frozenset(worlds) for worlds in outcomes.values())


def independent_oracle(instance):
    """Unpruned minimax recursion; shares only the environment transition API."""
    costs = instance.models[0].costs

    @lru_cache(None)
    def value(belief, horizon):
        if any(not instance.allowed(s) for _, s in belief):
            return inf
        if all(instance.goal.holds(s) for _, s in belief):
            return 0
        if horizon == 0:
            return inf
        return min(cost + max(value(child, horizon - 1) for child in branches(instance, belief, action))
                   for action, cost in costs.items())
    return value


def reachable_contexts(instance):
    """All distinct belief/horizon pairs, including branches of failed actions."""
    contexts = {(instance.belief, instance.horizon)}
    pending = list(contexts)
    while pending:
        belief, horizon = pending.pop()
        if horizon == 0:
            continue
        for action in instance.models[0].costs:
            for child in branches(instance, belief, action):
                key = child, horizon - 1
                if key not in contexts:
                    contexts.add(key)
                    pending.append(key)
    return contexts
