"""Deterministic, enumerable micro-domains; no sampled games or LLM calls.

These controlled instances isolate information/resource effects. They are not
claimed to be a representative benchmark of real game failures.
"""
from dataclasses import dataclass, field
from math import ceil, log2

from scar_public.finite_planner import State, Goal, compile_model


@dataclass
class StudyInstance:
    name: str
    family: str
    models: list
    goal: Goal
    belief: frozenset
    horizon: int
    metadata: dict = field(default_factory=dict)

    @staticmethod
    def allowed(state):
        return state.symbols[1] != 'broken'


def workshop(*, count=2, stock=1, horizon=5, scan_steps=0, assay=False,
             bits=False, wrong_breaks=True, common=False, family='workshop',
             name=None, costs=None):
    """A hidden recipe calibration; stock is an irreversible material resource.

    make_i costs one material; matching calibration completes the task. A wrong
    attempt either breaks the workpiece or spends one material but allows retry.
    assay consumes one material and reveals calibration. scan takes scan_steps
    actions but no material. Bit tests consume one material per test. A common
    recipe works in every model; its productive observation can reveal the model.
    All emitted observations include goal status, never a free hidden model ID.
    """
    assert count >= 2 and stock >= 0 and horizon >= 0 and scan_steps >= 0
    actions = [f'make_{i}' for i in range(count)]
    if scan_steps:
        actions.append('scan')
    if assay:
        actions.append('assay')
    if bits:
        actions.extend(f'bit_{j}' for j in range(ceil(log2(count))))
    action_costs = dict.fromkeys(actions, 1)
    if costs:
        action_costs.update(costs)
    assert set(action_costs) == set(actions)
    domains = (tuple(range(scan_steps + 1)), ('live', 'done', 'broken'))

    def transition(model, state, action):
        calibration = int(model[1:])
        progress, status = state.symbols
        material, = state.resources
        message, signal = 'terminal', None
        if status == 'live':
            message = 'no_material'
            if action == 'scan':
                progress = min(progress + 1, scan_steps)
                message = 'scanning'
                if progress == scan_steps:
                    signal = ('calibration', calibration)
            elif material:
                material -= 1
                if action == 'assay':
                    message, signal = 'assayed', ('calibration', calibration)
                elif action.startswith('bit_'):
                    bit = int(action[4:])
                    message, signal = 'bit', (bit, (calibration >> bit) & 1)
                else:
                    if common or int(action[5:]) == calibration:
                        status, message = 'done', 'made'
                        if common:
                            signal = ('calibration', calibration)
                    else:
                        status = 'broken' if wrong_breaks else 'live'
                        message = 'wrong_recipe'
        successor = State((progress, status), (material,))
        return successor, (message, progress, status, material, signal)

    models = [compile_model(f'm{i}', domains, (stock,), action_costs, transition)
              for i in range(count)]
    initial = State((0, 'live'), (stock,))
    config = dict(count=count, stock=stock, horizon=horizon, scan_steps=scan_steps,
                  assay=assay, bits=bits, wrong_breaks=wrong_breaks, common=common)
    return StudyInstance(name or f'{family}_n{count}_r{stock}_h{horizon}_s{scan_steps}',
                         family, models, Goal(symbols=((1, 'done'),)),
                         frozenset((m.name, initial) for m in models), horizon, config)


def study_grid():
    for count in (2, 3, 4, 6):
        for scan in (1, 3, 5):
            for horizon in (scan, scan + 1):
                yield workshop(count=count, scan_steps=scan, horizon=horizon,
                               family='delayed_observation')
    for count in (2, 4, 6):
        for stock in (1, 2):
            for scan in (2, 4):
                yield workshop(count=count, stock=stock, scan_steps=scan,
                               assay=True, horizon=scan + 1, family='consumptive_probe')
    for count in (2, 3, 4, 6):
        for stock in range(1, count + 1):
            yield workshop(count=count, stock=stock, horizon=count,
                           wrong_breaks=False, family='retry_budget')
    for count in (4, 6, 8):
        for stock in (1, 2, 3, 4):
            yield workshop(count=count, stock=stock, horizon=4, bits=True,
                           family='binary_observations')
    for count in (2, 4, 8):
        yield workshop(count=count, horizon=4, common=True, assay=True,
                       family='productive_information')
