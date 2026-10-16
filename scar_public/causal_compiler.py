"""Bounded compiler from candidate transition rules into the SAME finite planner.

Every unmodelled branch goes to an explicit unknown state. Results are conditional
on the selected fields, rule alternatives, bounds, and observation abstraction.
No result certifies a TTCL task, global dead end, or true-model coverage.
"""
import itertools
import math
from functools import reduce

from scar_public.causal_model import digest, predicate, predict


class CompilationGap(ValueError):
    pass


def search_fragment(monitor, actions, goal_atoms, bounds, horizon=3, expansion_budget=100,
                    max_states=4096, max_worlds=8):
    from scar_public.finite_planner import State, Goal, Planner, compile_model

    def require(condition, message):
        if not condition:
            raise CompilationGap(message)

    require(actions and len(set(actions)) == len(actions), 'nonempty distinct commands required')
    require(goal_atoms, 'an explicit observable LOCAL milestone is required')
    choices = [[r for r in monitor.rules.get(a, []) if r['status'] == 'candidate'] for a in actions]
    require(all(choices), 'action has no candidate rule')
    worlds = math.prod(map(len, choices))
    require(worlds <= max_worlds, 'candidate-model product exceeds bound')
    rules = [r for group in choices for r in group]
    fields = sorted({atom['field'] for rule in rules for key in ('guard', 'effects')
                     for atom in rule[key]} | {a['field'] for a in goal_atoms})
    require(all(f in monitor.fields for f in fields), 'unknown field in fragment')
    # Text is not observed on every command; accepting it here would invent an observation.
    require(all(not f.startswith('text:') for f in fields), 'text requires a separate observation action adapter')
    current = monitor.current
    require(all(f in current for f in fields), 'initial projected state contains unknown values')
    symbols = [f for f in fields if monitor.fields[f] == 'symbol']
    resources = [f for f in fields if monitor.fields[f] == 'numeric']
    domains = [(0, 1)]  # 0 = outside the represented transition fragment
    for field in symbols:
        values = {current[field]}
        for rule in rules:
            values.update(a['value'] for a in rule['guard'] if a['field'] == field)
            values.update(a['value'] for a in rule['effects'] if a['field'] == field and a['op'] == 'set')
        values.update(a['value'] for a in goal_atoms if a['field'] == field)
        domains.append(tuple(sorted(values)))
    units, upper = {}, []
    for field in resources:
        require(type(bounds.get(field)) is int and current[field] <= bounds[field] <= 1_000_000,
                'explicit finite bound required for every resource')
        values = [current[field], bounds[field]]
        values += [a['value'] for r in rules for k in ('guard', 'effects') for a in r[k]
                   if a['field'] == field and 'value' in a]
        values += [a['value'] for a in goal_atoms if a['field'] == field]
        units[field] = reduce(math.gcd, map(abs, values)) or 1
        upper.append(bounds[field] // units[field])
    states = math.prod(map(len, domains)) * math.prod(n+1 for n in upper)
    require(states * worlds <= max_states, 'finite grounding exceeds state budget')
    si = {f: i+1 for i, f in enumerate(symbols)}
    ri = {f: i for i, f in enumerate(resources)}

    def encode(values, known=1):
        return State((known,) + tuple(values[f] for f in symbols),
                     tuple(values[f] // units[f] for f in resources))

    def decode(state):
        return {**{f: state.symbols[i] for f, i in si.items()},
                **{f: state.resources[i]*units[f] for f, i in ri.items()}}

    mappings = {str(i): dict(zip(actions, chosen)) for i, chosen in enumerate(itertools.product(*choices))}

    def transition(name, state, action):
        values = decode(state)
        rule = mappings[name][action]
        expected = predict(rule, values) if state.symbols[0] else None
        modelled = (expected is not None and all(f in expected for f in fields)
                    and expected.get('result') in ('success', 'failure'))
        if modelled:
            modelled = (all(0 <= expected[f] <= bounds[f] and expected[f] % units[f] == 0 for f in resources)
                         and all(expected[f] in domains[si[f]] for f in symbols))
        if not modelled:
            return encode(values, 0), ('UNMODELLED',)
        successor = encode(expected)
        # Only fresh public fields are represented. Case/model IDs never enter observations.
        return successor, (expected['result'],) + tuple(expected[f] for f in fields)

    models = [compile_model(name, tuple(domains), tuple(upper), dict.fromkeys(actions, 1), transition)
              for name in mappings]
    goal_symbols, numeric = [(0, 1)], []
    for atom in goal_atoms:
        field, op, value = atom['field'], atom['op'], atom['value']
        require(op in ('eq', 'ge', 'le'), 'unsupported goal operator')
        if field in si:
            require(op == 'eq', 'symbolic goal must be equality')
            goal_symbols.append((si[field], value))
        else:
            require(type(value) is int and value % units[field] == 0, 'noninteger goal')
            row = tuple(int(i == ri[field]) for i in range(len(resources)))
            if op in ('eq', 'ge'):
                numeric.append((row, value // units[field]))
            if op in ('eq', 'le'):
                numeric.append((tuple(-x for x in row), -value // units[field]))
    goal = Goal(tuple(goal_symbols), tuple(numeric))
    start = encode(current)
    belief = frozenset((m.name, start) for m in models)
    planner = Planner(models, goal, allowed=lambda s: s.symbols[0] == 1)
    result = planner.solve(belief, horizon, expansion_budget)
    finite = math.isfinite(result.upper)
    if finite:
        assert planner.verify(belief, horizon, result.policy) == result.upper
    certificate = {'model_version': monitor.version, 'prefix_hash': monitor.prefix_hash,
                   'fragment_hash': digest({'actions': actions, 'rules': rules, 'bounds': bounds,
                                            'goal': goal_atoms, 'horizon': horizon}),
                   'valid': True, 'scope': 'candidate finite projection; NOT true-world feasibility',
                   'status': 'CONDITIONAL_PLAN_FOUND' if finite else 'UNKNOWN_FOR_ENVIRONMENT',
                   'lower': str(result.lower), 'upper': str(result.upper),
                   'first_action': result.policy.get('action') if finite else None,
                   'already_at_local_milestone': bool(finite and result.policy.get('stop')),
                   'worlds': worlds, 'ground_states_per_world': states,
                   'search_expansions': planner.expanded,
                   'lp_calls': sum(r.calls for r in planner.relax.values()),
                   'omitted_effects_become_unknown': True, 'true_model_coverage': 'unestablished',
                   'goal_scope': 'caller supplied local milestone; no task completion inference',
                   'unresolved': sorted({x for r in rules for x in r['unknowns']})}
    monitor.certificates.append(certificate)
    return certificate


def fragment_check(monitor, action):
    if action.startswith('pick up '):
        field, target = 'holding:' + action[8:], 1000
    elif action.startswith('craft '):
        field = 'ground:' + action.split()[-1]
        if field not in monitor.current:
            return {'status': 'NOT_COMPILED', 'reason': 'output name not in fresh public projection'}
        target = monitor.current[field] + 1000
    else:
        return {'status': 'NOT_COMPILED', 'reason': 'no externally specified local resource milestone'}
    all_rules = monitor.rules.get(action, [])
    numeric = {a['field'] for r in all_rules for k in ('guard', 'effects') for a in r[k]
               if monitor.fields[a['field']] == 'numeric'} | {field}
    bounds = {}
    for name in numeric:
        largest_delta = max([1000] + [abs(a.get('value', 0)) for r in all_rules for a in r['effects']
                                     if a['field'] == name and a['op'] == 'add'])
        bounds[name] = max(monitor.current.get(name, 0), target if name == field else 0) + 2*largest_delta
    try:
        return search_fragment(monitor, [action], [{'field': field, 'op': 'ge', 'value': target}],
                               bounds, horizon=2, expansion_budget=80)
    except CompilationGap as error:
        return {'status': 'NOT_COMPILED', 'reason': str(error)}
