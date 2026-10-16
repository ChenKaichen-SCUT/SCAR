"""Additional deterministic state-machine audit, independent of workshop logic."""
from itertools import combinations
import json
from pathlib import Path

from scar_public.finite_planner import State, Goal, compile_model
from scar_public.information_instances import StudyInstance
from scar_public.information_reference import independent_oracle, reachable_contexts
from scar_public.observation_capacity import ObservationCapacity


def state_machine(code):
    actions = dict.fromkeys(('a', 'b', 'c'), 1)

    def transition(name, state, action):
        model, index = int(name[1:]), ord(action) - ord('a')
        phase, done = state.symbols
        resource, = state.resources
        if done:
            return state, (phase, done, resource, None)
        need = 1 + ((model + index + code) % 2)
        if resource >= need and phase == ((code >> index) & 1):
            done = (model + index) % 3 == (code >> 3) % 3
        if index == 0:
            phase = 1 - phase
        # Covers resource use, free actions, and bounded replenishment. No RNG.
        delta = ((code >> (index + 1)) + model + index) % 3 - 1
        resource = max(0, min(2, resource + delta))
        signal = model % 2 if (code >> (index + 2)) & 1 else None
        result = State((phase, done), (resource,))
        return result, (phase if code & 1 else None, done, resource, signal)

    models = [compile_model(f'm{i}', ((0, 1), (False, True)), (2,), actions, transition)
              for i in range(3)]
    start = State((0, False), (1 + code % 2,))
    return StudyInstance(f'machine_{code}', 'generated_state_machine', models,
                         Goal(symbols=((1, True),)), frozenset((m.name, start) for m in models), 3)


def audit_generated(count=64):
    checked = finite = infeasible = strict = 0
    for code in range(count):
        instance = state_machine(code)
        oracle = independent_oracle(instance)
        bound = ObservationCapacity(instance.models, instance.goal, instance.allowed)
        assert bound.stats['disabled_reason'] is None
        contexts = reachable_contexts(instance)
        # Also test every nonempty subset at each reachable context. This is
        # exhaustive within these generated models, not over all possible models.
        projections = set()
        for belief, horizon in contexts:
            worlds = tuple(belief)
            for size in range(1, len(worlds) + 1):
                for subset in combinations(worlds, size):
                    projections.add((frozenset(subset), horizon))
        for belief, horizon in projections:
            lower = bound.lower(belief, horizon)
            truth = oracle(belief, horizon)
            assert lower <= truth, (code, belief, horizon, lower, truth)
            checked += 1
            finite += truth != float('inf')
            infeasible += lower == float('inf')
            strict += 0 < lower < float('inf')
        oracle.cache_clear()
    return dict(generated_models=count, checked_belief_horizon_subproblems=checked,
                finite_optima=finite, certified_infeasible=infeasible, positive_finite_bounds=strict,
                all_capacity_bounds_admissible=True, api_calls=0, random_seeds_used=False,
                scope='64 deterministic parameter settings; exhaustive reachable contexts and subsets '
                      'within each, not an exhaustive enumeration of all transition systems.')


if __name__ == '__main__':
    result = audit_generated()
    path = Path(__file__).parent / 'results/2026-10-16-information-bound/validation.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result), flush=True)
