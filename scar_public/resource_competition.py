"""Explicit quantity/access hypotheses and task-preserving experiment selection.

All guarantees are relative to this finite candidate family and its declared
local goal. No hidden engine state, LLM API, or task-translation oracle is used.
"""
from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass
from itertools import product
from math import inf, isfinite
from functools import lru_cache

from scar_public.causal_model import digest
from scar_public.finite_planner import State, Guard, Case, Model, Goal, Planner, Result

UNIT = 1000
QUANTITY_MODES = ('exact', 'ceil_batch', 'ceil_per_output')
ACCESS_MODES = ('hand', 'hand_bag', 'hand_ground', 'hand_bag_ground')


class ResourceGap(ValueError):
    pass


@dataclass(frozen=True)
class Recipe:
    output: str
    needs: tuple[tuple[str, int], ...]
    stations: tuple[str, ...]  # Explicit allowed locations, not hidden station rules.
    quantity_modes: tuple[str, ...] = QUANTITY_MODES
    access_modes: tuple[str, ...] = ACCESS_MODES
    quantities: tuple[int, ...] = (1,)


@dataclass
class ResourceProblem:
    locations: tuple[str, ...]
    routes: dict[str, dict[str, str]]  # location -> public enter argument -> destination
    items: tuple[str, ...]
    recipes: tuple[Recipe, ...]
    start_location: str
    holding: dict[str, int]
    ground: dict[str, dict[str, int]]
    bag: dict[str, int]
    bag_name: str | None
    hand_capacity: int
    bag_capacity: int
    hand_background: int
    bag_background: int
    target: str
    target_count: int = UNIT
    require_crafted: bool = True
    protected_totals: tuple[tuple[str, int], ...] = ()
    assumptions: tuple[str, ...] = ()
    source: dict | None = None


def consumption(recipe, quantity, mode):
    if mode not in QUANTITY_MODES or quantity <= 0:
        raise ValueError('unsupported consumption hypothesis')
    if mode == 'exact':
        return {item: amount*quantity for item, amount in recipe.needs}
    if mode == 'ceil_batch':
        return {item: ((amount*quantity+UNIT-1)//UNIT)*UNIT for item, amount in recipe.needs}
    return {item: ((amount+UNIT-1)//UNIT)*UNIT*quantity for item, amount in recipe.needs}


class ResourceDomain:
    """State includes finite resource locations, recipe events and elapsed actions.

    Bag contents are latent during ordinary actions. Only inspect BAG reveals them.
    Pickup/drop/store/take each transfer one unit. Failure is charged and preserves
    resources in this candidate family; that assumption is explicitly reported.
    """
    def __init__(self, problem):
        self.problem = p = problem
        if (not p.items or len(set(p.items)) != len(p.items) or p.target not in p.items
                or p.start_location not in p.locations):
            raise ResourceGap('invalid finite item/location/target universe')
        self.i = {name: i for i, name in enumerate(p.items)}
        self.l = {name: i for i, name in enumerate(p.locations)}
        self.recipes = {r.output: r for r in p.recipes}
        if len(self.recipes) != len(p.recipes):
            raise ResourceGap('duplicate recipe outputs')
        for r in p.recipes:
            if (r.output not in self.i or not r.needs or any(n not in self.i or type(v) is not int or v <= 0 for n,v in r.needs)
                    or any(x not in p.locations for x in r.stations) or not r.stations
                    or not set(r.quantity_modes) <= set(QUANTITY_MODES)
                    or not set(r.access_modes) <= set(ACCESS_MODES)
                    or not r.quantity_modes or not r.access_modes or not r.quantities
                    or any(type(q) is not int or q <= 0 or q > 4 for q in r.quantities)):
                raise ResourceGap('invalid recipe or unresolved station')
        if p.require_crafted and p.target not in self.recipes:
            raise ResourceGap('target craft event has no recipe')
        self.recipe_order = tuple(self.recipes)
        self.n = len(p.items)
        self.store_count = 2+len(p.locations)  # hand, attached bag, floor at each location
        self.size = self.n*self.store_count
        self.actions = {}
        for item in p.items:
            self.actions['pick up '+item] = ('pick', item)
            self.actions['drop '+item] = ('drop', item)
            if p.bag_name:
                self.actions[f'store 1 {item} {p.bag_name}'] = ('store', item)
                self.actions[f'take out 1 {item} {p.bag_name}'] = ('take', item)
        if p.bag_name:
            self.actions['inspect '+p.bag_name] = ('inspect', p.bag_name)
        for name in sorted({a for edges in p.routes.values() for a in edges}):
            self.actions['enter '+name] = ('enter', name)
        for recipe in p.recipes:
            for q in recipe.quantities:
                self.actions[f'craft {q} {recipe.output}'] = ('craft', recipe.output, q)
        initial = [0]*self.size
        for store, values in [(0,p.holding), (1,p.bag)] + [(2+self.l[l],p.ground.get(l,{})) for l in p.locations]:
            for item, amount in values.items():
                if item not in self.i or type(amount) is not int or amount < 0:
                    raise ResourceGap('invalid initial quantity')
                initial[self.at(store,item)] = amount
        self.start = State((self.l[p.start_location], 0)+(False,)*len(p.recipes), tuple(initial))
        if not self.allowed(self.start):
            raise ResourceGap('initial state violates declared capacity or protected resources')

    def at(self, store, item):
        return store*self.n+self.i[item]

    def store(self, state, store):
        return state.resources[store*self.n:(store+1)*self.n]

    def total(self, state, item):
        return sum(state.resources[self.at(s,item)] for s in range(self.store_count))

    def allowed(self, state):
        p = self.problem
        return (sum(self.store(state,0))+p.hand_background <= p.hand_capacity
                and sum(self.store(state,1))+p.bag_background <= p.bag_capacity
                and all(r >= 0 for r in state.resources)
                and all(self.total(state,item) >= count for item,count in p.protected_totals))

    def goal(self):
        p = self.problem
        symbols = ((2+self.recipe_order.index(p.target), True),) if p.require_crafted else ()
        row = tuple(int(i == self.at(0,p.target)) for i in range(self.size))
        return Goal(symbols, ((row,p.target_count),))

    def observation(self, state, status, reveal_bag=False):
        # No model ID, hidden bag count, or unobserved remote floor is leaked.
        return (status, self.problem.locations[state.symbols[0]], self.store(state,0),
                self.store(state,2+state.symbols[0]), tuple(state.symbols[2:]),
                self.store(state,1) if reveal_bag else None)

    def transition(self, hypothesis, state, action):
        p = self.problem
        op = self.actions[action]
        resources = list(state.resources)
        symbols = list(state.symbols); symbols[1] += 1
        loc = p.locations[state.symbols[0]]
        floor = 2+state.symbols[0]
        status = 'failure'
        if op[0] == 'enter':
            dest = p.routes.get(loc,{}).get(op[1])
            if dest in self.l:
                symbols[0] = self.l[dest]; status = 'success'
        elif op[0] == 'inspect':
            status = 'success'
        elif op[0] in ('pick','drop','store','take'):
            src,dst = {'pick':(floor,0),'drop':(0,floor),'store':(0,1),'take':(1,0)}[op[0]]
            i,j = self.at(src,op[1]),self.at(dst,op[1])
            cap = (p.hand_capacity-p.hand_background if dst == 0 else
                   p.bag_capacity-p.bag_background if dst == 1 else inf)
            if resources[i] >= UNIT and sum(self.store(state,dst))+UNIT <= cap:
                resources[i] -= UNIT; resources[j] += UNIT; status = 'success'
        elif op[0] == 'craft':
            recipe = self.recipes[op[1]]
            qmode,access = hypothesis[op[1]]
            needs = consumption(recipe,op[2],qmode)
            stores = [0] + ([1] if 'bag' in access and p.bag_name else []) + ([floor] if 'ground' in access else [])
            if loc in recipe.stations and all(sum(resources[self.at(s,item)] for s in stores) >= amount
                                             for item,amount in needs.items()):
                for item,amount in needs.items():
                    for store in stores:
                        idx = self.at(store,item); used = min(resources[idx],amount)
                        resources[idx] -= used; amount -= used
                resources[self.at(floor,recipe.output)] += op[2]*UNIT
                symbols[2+self.recipe_order.index(recipe.output)] = True
                status = 'success'
        successor = State(tuple(symbols),tuple(resources))
        return successor,self.observation(successor,status,op[0] == 'inspect')


@dataclass
class CompiledResources:
    domain: ResourceDomain
    models: list
    hypotheses: dict
    belief: frozenset
    horizon: int
    fingerprint: str
    states: int
    aliases: dict

    def planner(self, use_lp=True):
        return Planner(self.models,self.domain.goal(),self.domain.allowed,use_lp=use_lp)


class OpportunityPlanner(Planner):
    """A shared observable policy; conditional success is required for a fixed set.

    Only models PROVED individually infeasible at the ORIGINAL state/budget may
    be exempt. They remain in every belief and every protected-constraint check.
    Exemption does not make them false and never means real task completion.
    """
    def __init__(self, compiled, exempt):
        super().__init__(compiled.models,compiled.domain.goal(),compiled.domain.allowed)
        self.exempt = frozenset(exempt)

    def initial(self, belief, horizon):
        assert belief
        key = belief,horizon
        if key in self.memo: return self.memo[key]
        if any(not self.allowed(s) for _,s in belief): return Result(inf,inf)
        if all(name in self.exempt or self.goal.holds(s) for name,s in belief):
            return Result(0,0,{'stop':True})
        if horizon == 0: return Result(inf,inf)
        lower = max((self.relax[name].lower(s,horizon) for name,s in belief if name not in self.exempt),default=0)
        return Result(lower,inf)

    def branches(self, belief, action):
        outcomes = {}
        for name,state in sorted(belief,key=lambda w:(w[0],repr(w[1]))):
            successor,obs = self.models[name].step(state,action)
            outcomes.setdefault(obs,set()).add((name,successor))
        # Physical goals are public; exemptions are NOT exposed as observations.
        # Stopping is allowed only when every non-exempt world in the belief has
        # reached the goal. A mixed branch must continue while any obligation remains.
        return {obs:frozenset(worlds) for obs,worlds in outcomes.items()}

    def verify(self, belief, horizon, policy):
        costs = []
        for name,initial in belief:
            state,node,used = initial,policy,0
            while True:
                assert self.allowed(state)
                if node.get('stop'):
                    assert name in self.exempt or self.goal.holds(state)
                    break
                assert used < horizon
                action = node['action']; state,obs = self.models[name].step(state,action)
                used += self.costs[action]; node = node['branches'][obs]
            costs.append(used)
        return max(costs)

    def oracle(self):
        """Independent minimax with the SAME fixed initial success obligations."""
        @lru_cache(None)
        def value(belief,horizon):
            if any(not self.allowed(s) for _,s in belief): return inf
            if all(n in self.exempt or self.goal.holds(s) for n,s in belief): return 0
            if horizon == 0: return inf
            return min(cost+max(value(child,horizon-1) for child in self.branches(belief,a).values())
                       for a,cost in self.costs.items())
        return value


def opportunity_planner(compiled, budget):
    single = compiled.planner()
    proofs,exempt = {},set()
    for name,state in compiled.belief:
        solved = single.solve(frozenset(((name,state),)),compiled.horizon,budget)
        if solved.lower == inf:
            exempt.add(name)
        elif isfinite(solved.upper):
            single.verify(frozenset(((name,state),)),compiled.horizon,solved.policy)
        proofs[name] = {'lower':str(solved.lower),'upper':str(solved.upper),
                        'success_exempt':name in exempt,
                        'reason':'proved individually infeasible within ORIGINAL horizon' if name in exempt else
                                 'verified initially feasible' if isfinite(solved.upper) else
                                 'unresolved; success obligation retained'}
    return OpportunityPlanner(compiled,exempt),proofs


def compile_resources(problem, horizon=8, max_states=30000, max_models=32):
    """Enumerate EVERY reachable transition up to H, or abort with UNKNOWN.

    Elapsed time is part of the finite state. Frontier rows are charged self-loops
    that cannot be executed by a query with the declared remaining horizon. LP
    columns include all transitions usable within H, not merely a proposed plan.
    No bound from a partially enumerated graph is returned.
    """
    if type(horizon) is not int or not 1 <= horizon <= 30:
        raise ResourceGap('finite horizon must be 1..30')
    domain = ResourceDomain(problem)
    options = []
    for recipe in problem.recipes:
        groups = {}
        for quantity,access in product(recipe.quantity_modes,recipe.access_modes):
            canonical_q = ('exact' if all(n % UNIT == 0 for _,n in recipe.needs) else
                           'ceil_batch' if quantity == 'ceil_per_output' and recipe.quantities == (1,) else quantity)
            canonical_a = access if problem.bag_name else access.replace('_bag','')
            groups.setdefault((canonical_q,canonical_a),[]).append((quantity,access))
        options.append(groups)
    count = 1
    for group in options: count *= len(group)
    if count > max_models:
        raise ResourceGap('independent recipe hypothesis product exceeds model bound')
    candidates = {f'm{i}': dict(zip(domain.recipe_order,values)) for i,values in enumerate(product(*options))}
    aliases = {name:{output:options[i][hypothesis[output]] for i,output in enumerate(domain.recipe_order)}
               for name,hypothesis in candidates.items()}
    models, total = [], 0
    domains = (tuple(range(len(problem.locations))),tuple(range(horizon+1))) + ((False,True),)*len(problem.recipes)
    for name,hypothesis in candidates.items():
        queue = deque([domain.start]); seen = {domain.start}; lookup = {}; cases = []
        while queue:
            state = queue.popleft()
            numeric = []
            for i,value in enumerate(state.resources):
                row = tuple(int(j == i) for j in range(domain.size))
                numeric.extend(((row,value),(tuple(-x for x in row),-value)))
            guard = Guard(tuple(enumerate(state.symbols)),tuple(numeric))
            for action in domain.actions:
                if state.symbols[1] == horizon or not domain.allowed(state):
                    successor,obs = state,domain.observation(state,'horizon')
                else:
                    successor,obs = domain.transition(hypothesis,state,action)
                case = Case(action,guard,tuple((i,a,b) for i,(a,b) in enumerate(zip(state.symbols,successor.symbols)) if a != b),
                            tuple(b-a for a,b in zip(state.resources,successor.resources)),obs)
                assert case.apply(state) == successor
                cases.append(case); lookup[state,action] = case
                if successor not in seen:
                    seen.add(successor); queue.append(successor)
                    if total+len(seen) > max_states:
                        raise ResourceGap('reachable state bound exceeded; no partial-model certificate')
        total += len(seen)
        upper = tuple(max(s.resources[i] for s in seen) for i in range(domain.size))
        models.append(Model(name,domains,upper,dict.fromkeys(domain.actions,1),tuple(cases),lookup))
    return CompiledResources(domain,models,candidates,frozenset((m.name,domain.start) for m in models),
                             horizon,digest({'problem':asdict(problem),'horizon':horizon}),total,aliases)


def physical_belief_key(belief):
    return tuple(sorted((name,(state.symbols[0],)+state.symbols[2:],state.resources) for name,state in belief))


def select_experiment(compiled, prefix_depth=3, max_prefixes=120, expansion_budget=2500, max_extra_actions=0,
                      mode='strong'):
    """Choose an informative prefix only with a VERIFIED common suffix per leaf.

    Prefix search stops at its first observation split. It is deliberately bounded,
    so this is not a claim of optimal experiment selection. Baseline and candidates
    use the same AND/OR planner, state abstraction, goal and action costs.
    """
    if not 0 <= max_extra_actions <= 10:
        raise ValueError('additional action allowance must be explicit and bounded')
    if mode not in ('strong','preserve_opportunity'):
        raise ValueError('unknown guarantee mode')
    planner,proofs = opportunity_planner(compiled,expansion_budget) if mode == 'preserve_opportunity' else (compiled.planner(),{})
    belief = compiled.belief; horizon = compiled.horizon
    baseline = planner.solve(belief,horizon,expansion_budget)
    if isfinite(baseline.upper):
        assert planner.verify(belief,horizon,baseline.policy) == baseline.upper
    result = {'fingerprint':compiled.fingerprint, 'scope':'conditional finite local task',
              'guarantee_mode':mode,'initial_individual_feasibility':proofs,
              'success_exempt_models':sorted(planner.exempt) if mode == 'preserve_opportunity' else [],
              'hypotheses':compiled.hypotheses, 'state_count':compiled.states,
              'behaviorally_equivalent_parameter_aliases':compiled.aliases,
              'baseline_lower':str(baseline.lower),'baseline_upper':str(baseline.upper),
              'max_extra_actions':max_extra_actions, 'candidates':[], 'action_override':False,
              'true_model_coverage':'unestablished','assumptions':list(compiled.domain.problem.assumptions)}
    if mode == 'preserve_opportunity' and len(planner.exempt) == len(compiled.models):
        result.update(status='NO_INITIALLY_VIABLE_CANDIDATE',reason='no opportunity has been established; no probe selected')
        return result,None,planner
    queue = deque([(belief,())]); seen = {physical_belief_key(belief)}; visited = 0
    selected = None; best_rank = None
    initial_ids = {name for name,_ in belief}
    while queue and visited < max_prefixes:
        current,prefix = queue.popleft(); visited += 1
        if (len(prefix) >= min(prefix_depth,horizon) or all(planner.goal.holds(s) for _,s in current)
                or mode == 'preserve_opportunity' and all(name in planner.exempt for name,_ in current)):
            continue
        for action in planner.costs:
            actions = prefix+(action,); used = len(actions)
            branches = planner.branches(current,action)
            ids = {obs:{name for name,_ in worlds} for obs,worlds in branches.items()}
            informative = len(branches) >= 2 and all(len(names) < len(initial_ids) for names in ids.values())
            if not informative:
                if len(branches) == 1:
                    nxt = next(iter(branches.values())); key = physical_belief_key(nxt)
                    if key not in seen and all(planner.allowed(s) for _,s in nxt):
                        seen.add(key); queue.append((nxt,actions))
                continue
            candidate = {'prefix':list(actions),'observable_branches':len(branches),
                         'worst_remaining_models':max(map(len,ids.values())), 'leaves':[]}
            candidate['excess_target_production'] = max(max(0,compiled.domain.total(s,compiled.domain.problem.target)
                - max(compiled.domain.problem.target_count,compiled.domain.total(compiled.domain.start,compiled.domain.problem.target)))
                for worlds in branches.values() for _,s in worlds)
            suffixes = {}; valid = True; upper = used; lower = used
            for obs,worlds in branches.items():
                checked = planner.solve(worlds,horizon-used,expansion_budget)
                safe = isfinite(checked.upper)
                if safe:
                    assert planner.verify(worlds,horizon-used,checked.policy) == checked.upper
                    suffixes[obs] = checked.policy
                valid &= safe
                upper = max(upper,used+checked.upper); lower = max(lower,used+checked.lower)
                candidate['leaves'].append({'observation':obs,'models':sorted(ids[obs]),
                    'common_continuation_verified':safe,'lower':str(checked.lower),'upper':str(checked.upper),
                    'status': 'VERIFIED' if safe else 'NO_CONTINUATION_IN_CANDIDATE_MODEL'
                    if checked.lower == inf else 'SEARCH_BUDGET_UNKNOWN'})
            candidate.update(lower=str(lower),upper=str(upper),all_leaves_verified=valid)
            if not valid:
                candidate['decision'] = 'REJECT_UNVERIFIED_CONTINUATION'
            elif isfinite(baseline.upper) and upper > baseline.upper+max_extra_actions:
                candidate['decision'] = 'REJECT_EXTRA_COST'
            else:
                candidate['decision'] = 'ADMISSIBLE'
                rank = (upper,candidate['worst_remaining_models'],candidate['excess_target_production'],len(actions),actions)
                if best_rank is None or rank < best_rank:
                    best_rank = rank
                    selected = (candidate,suffixes)
            result['candidates'].append(candidate)
    result.update(prefix_nodes=visited,prefix_search_exhausted=not queue,
                  search_expansions=planner.expanded,lp_calls=sum(r.calls for r in planner.relax.values()))
    if selected:
        candidate,suffixes = selected
        result.update(status='CONDITIONAL_EXPERIMENT',prefix=candidate['prefix'],
                      worst_total_actions=candidate['upper'],selected_leaves=candidate['leaves'])
        return result, {'prefix':candidate['prefix'],'suffixes':suffixes}, planner
    if isfinite(baseline.upper):
        result.update(status='DIRECT_POLICY',reason='no verified informative prefix within cost/bounds',
                      first_action=baseline.policy.get('action'),worst_total_actions=str(baseline.upper))
        return result, baseline.policy, planner
    result.update(status='NO_VERIFIED_SHARED_CONTINUATION',
                  reason='do not discard hard candidate worlds merely to approve a probe')
    return result,None,planner
