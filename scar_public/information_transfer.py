"""Transfer tests for the FROZEN information bounds; no agent or API changes.

Finite production tasks add typed resources, upstream conversion, locations and
inventory. Their workflow interpretation is an analogy, not workflow evaluation.
Separate bridge cases use the existing V8 resource transition implementation.
"""
from collections import deque
from dataclasses import dataclass, field
from math import inf

from scar_public.finite_planner import State, Guard, Case, Model, Goal
from scar_public.resource_competition import Recipe, ResourceProblem, compile_resources


@dataclass
class TransferInstance:
    name: str
    family: str
    models: list
    goal: Goal
    belief: frozenset
    horizon: int
    allowed: object
    metadata: dict = field(default_factory=dict)


def compile_reachable(name, initial, domains, costs, transition, max_states=10000):
    """Complete finite reachable graph, with no horizon truncation or oracle data."""
    queue, seen, lookup, cases = deque([initial]), {initial}, {}, []
    size = len(initial.resources)
    units = [tuple(int(i == j) for j in range(size)) for i in range(size)]
    while queue:
        state = queue.popleft()
        guard = Guard(tuple(enumerate(state.symbols)), tuple(
            constraint for row, value in zip(units, state.resources)
            for constraint in ((row, value), (tuple(-x for x in row), -value))))
        for action in costs:
            successor, observation = transition(name, state, action)
            assert all(x >= 0 for x in successor.resources)
            case = Case(action, guard,
                        tuple((i, a, b) for i, (a, b) in enumerate(zip(state.symbols, successor.symbols)) if a != b),
                        tuple(b - a for a, b in zip(state.resources, successor.resources)), observation)
            lookup[state, action] = case
            cases.append(case)
            if successor not in seen:
                seen.add(successor)
                if len(seen) > max_states:
                    raise ValueError('Reachable graph limit exceeded; no truncated-model result')
                queue.append(successor)
    bounds = tuple(max(s.resources[i] for s in seen) for i in range(size))
    return Model(name, domains, bounds, costs, tuple(cases), lookup)


def production(*, family, count=3, ore=3, fiber=3, fuel=None, upstream=False,
               distance=0, gather=False, capacity=None, assay=False, horizon=6):
    """Resource vector: depot ore/fiber, held ore/fiber/ingot, fuel, held product.

    All resources are public in this controlled domain. make_i consumes ingot and
    fiber even on a wrong calibration. Assay consumes one ingot and reveals the
    calibration. Refinement converts ore+fuel to an ingot. Movement follows an
    explicit path; gather/store occur only at the depot, refine/assay at the forge,
    and final fabrication at the bench. Failures still cost one action.
    """
    assert distance in (0, 1, 2) and (not gather or upstream)
    fuel = ore if fuel is None and upstream else (fuel or 0)
    capacity = (ore + fiber + 1) if capacity is None else capacity
    locations = ('workshop',) if distance == 0 else (('forge', 'bench') if distance == 1
                                                    else ('depot', 'forge', 'bench'))
    depot, forge, bench = 0, max(0, len(locations)-2), len(locations)-1
    resources = ((ore, fiber, 0, 0, 0, fuel, 0) if gather else
                 (0, 0, ore if upstream else 0, fiber, 0 if upstream else ore, fuel, 0))
    initial = State((0, 'live'), resources)
    assert sum(initial.resources[i] for i in (2, 3, 4, 6)) <= capacity
    actions = [f'make_{i}' for i in range(count)]
    if upstream:
        actions.append('refine')
    if gather:
        actions.extend(('gather_ore', 'gather_fiber', 'store_ore', 'store_fiber'))
    if distance:
        actions.extend(('move_next', 'move_previous'))
    if assay:
        actions.append('assay')
    costs = dict.fromkeys(actions, 1)

    def transition(model, state, action):
        location, status = state.symbols
        stock_o, stock_f, raw, strand, ingot, energy, target = state.resources
        message, signal = 'failure', None
        load = raw + strand + ingot + target
        if status == 'done':
            message = 'terminal'
        elif action == 'move_next' and location < bench:
            location += 1; message = 'moved'
        elif action == 'move_previous' and location > 0:
            location -= 1; message = 'moved'
        elif action == 'gather_ore' and location == depot and stock_o and load < capacity:
            stock_o -= 1; raw += 1; message = 'taken'
        elif action == 'gather_fiber' and location == depot and stock_f and load < capacity:
            stock_f -= 1; strand += 1; message = 'taken'
        elif action == 'store_ore' and location == depot and raw:
            raw -= 1; stock_o += 1; message = 'stored'
        elif action == 'store_fiber' and location == depot and strand:
            strand -= 1; stock_f += 1; message = 'stored'
        elif action == 'refine' and location == forge and raw and energy:
            raw -= 1; energy -= 1; ingot += 1; message = 'refined'
        elif action == 'assay' and location == forge and ingot:
            ingot -= 1; message = 'assayed'; signal = model
        elif action.startswith('make_') and location == bench and ingot and strand:
            ingot -= 1; strand -= 1
            if int(action[5:]) == int(model[1:]):
                target += 1; status = 'done'; message = 'made'
            else:
                message = 'wrong_calibration'
        successor = State((location, status), (stock_o, stock_f, raw, strand, ingot, energy, target))
        return successor, (message, location, status, successor.resources, signal)

    models = [compile_reachable(f'm{i}', initial, (tuple(range(len(locations))), ('live', 'done')),
                                costs, transition) for i in range(count)]
    config = dict(count=count, ore=ore, fiber=fiber, fuel=fuel, upstream=upstream,
                  distance=distance, gather=gather, capacity=capacity, assay=assay,
                  horizon=horizon, public_resources=True, locations=locations,
                  graph_states=sum(len({s for s,a in m.lookup}) for m in models),
                  graph_transitions=sum(len(m.cases) for m in models))
    name = f'{family}_n{count}_o{ore}_f{fiber}_e{fuel}_c{capacity}_d{distance}_a{int(assay)}_h{horizon}'
    allowed = lambda s: all(x >= 0 for x in s.resources) and sum(s.resources[i] for i in (2,3,4,6)) <= capacity
    return TransferInstance(name, family, models,
                            Goal(symbols=((1, 'done'),), numeric=(((0,0,0,0,0,0,1),1),)),
                            frozenset((m.name, initial) for m in models), horizon, allowed, config)


def production_grid():
    for ore in (1, 2, 3):
        for fiber in (1, 2, 3):
            yield production(family='multi_resource', ore=ore, fiber=fiber, horizon=3)
    for ore in (2, 3):
        for fiber in (2, 3):
            yield production(family='upstream_conversion', ore=ore, fiber=fiber,
                             upstream=True, horizon=6)
    for ore in (2, 3):
        for distance in (1, 2):
            for assay in (False, True):
                yield production(family='cross_location', ore=ore, fiber=ore,
                                 distance=distance, assay=assay, horizon=3+distance)
    for capacity, horizons in ((3, (8, 9)), (2, (10, 11))):
        for horizon in horizons:
            yield production(family='combined_chain', ore=2, fiber=1, upstream=True,
                             distance=2, gather=True, capacity=capacity,
                             assay=True, horizon=horizon)
    for ore, horizon in ((2, 10), (3, 14)):
        yield production(family='combined_chain', ore=ore, fiber=ore, upstream=True,
                         distance=2, gather=True, horizon=horizon)


def bridge_instance(kind, horizon):
    """Synthetic specs executed by the unchanged V8 transition/compiler code."""
    upstream = kind != 'recipe_multiresource'
    remote = kind == 'recipe_cross_location'
    locations = ('depot', 'forge') if remote else ('forge',)
    items = ('ore', 'fiber', 'ingot', 'blade') if upstream else ('ore', 'fiber', 'blade')
    recipes = ((Recipe('ingot', (('ore', 1000),), ('forge',), ('exact',), ('hand',)),) if upstream else ())
    recipes += (Recipe('blade', ((('ingot' if upstream else 'ore'), 500), ('fiber', 500)),
                       ('forge',), ('exact','ceil_batch'), ('hand',)),)
    problem = ResourceProblem(locations=locations,
        routes={'depot':{'forge':'forge'}, 'forge':{'depot':'depot'}} if remote else {},
        items=items, recipes=recipes, start_location=locations[0],
        holding={} if remote else {'ore':1000, 'fiber':1000},
        ground={'depot':{'ore':1000, 'fiber':1000}} if remote else {},
        bag={}, bag_name=None, hand_capacity=2000, bag_capacity=0,
        hand_background=0, bag_background=0, target='blade')
    compiled = compile_resources(problem, horizon=horizon, max_states=15000)
    return TransferInstance(f'{kind}_h{horizon}', kind, compiled.models, compiled.domain.goal(),
                            compiled.belief, horizon, compiled.domain.allowed,
                            dict(source='existing ResourceDomain', graph_states=compiled.states,
                                 graph_transitions=sum(len(m.cases) for m in compiled.models),
                                 fingerprint=compiled.fingerprint))


def bridge_grid():
    for kind, horizons in (('recipe_multiresource', (1,2,4)),
                           ('recipe_upstream', (3,4,6)),
                           ('recipe_cross_location', (6,7,8))):
        for horizon in horizons:
            yield bridge_instance(kind, horizon)
