"""Two small public-evidence priorities on frozen Stage10 S1.

No engine, catalogue, task identifier, witness, speculative dependency edge,
resource optimiser, recovery stack or additional model is available here.
Craft quantities and acquisition remain inherited from S1.
"""
import copy
import math

from scar.io import digest
from scar_sequence.planner import q
from scar_sequence.public import ResourceTable
from scar_unknown17.facts import PublicFacts
from scar_stage10.controller import ResourceController, REJECT
from scar_v3.state import parse_action

METHODS = ['E0', 'E1', 'E2', 'E3', 'E4']
PROMPT_REMINDER = ('Prioritize the current task. Explore objects and unknown prerequisites related to it; '
    'inspect newly crafted intermediate products for further recipe information. When a known necessary '
    'subgoal is feasible, execute it promptly instead of unrelated exploration. Preserve useful materials '
    'and leave enough actions to finish and collect the final product. Base decisions on observed evidence; '
    'do not assume an unknown recipe is known.')


class GoalController(ResourceController):
    NODE_LIMIT = 64

    def __init__(self, goal_ranking=False, timely_execution=False):
        super().__init__(opportunistic=False, storage=False)
        self.stage11 = True
        self.goal_ranking = goal_ranking
        self.timely_execution = timely_execution
        self.goal_view = {}
        self.produced11 = {}
        self.decision11 = {}
        self.selected11 = None
        self.ranked11 = []

    def public_goal_view(self, synchronize=False):
        """Finite worklist expansion of observed edges, never inferred edges."""
        t = self.table; goal = parse_action(self.target).target
        known = []; pending = [goal] if goal else []
        while pending and len(known) < self.NODE_LIMIT:
            name = pending.pop(0)
            if name in known: continue
            known.append(name)
            pending.extend(t.recipes.get(name, {}).get('ingredients', []))
        # Only unmet ancestors activate their inputs; owning a completed parent
        # does not justify manufacturing its prerequisites again.
        demands = {goal: self.amount} if goal else {}; active = []
        pending = [goal] if goal else []
        while pending and len(active) < self.NODE_LIMIT:
            name = pending.pop(0)
            if name in active: continue
            active.append(name)
            need = demands[name]
            if self.ownership(name)['lower_bound'] >= need: continue
            recipe = t.recipes.get(name, {})
            for dep in recipe.get('ingredients', []):
                floor = (recipe.get('quantities') or {}).get(dep, self.quotas.get(name, 1))
                demands[dep] = max(demands.get(dep, 0), self.queue_needs.get(dep, 1), floor)
                if dep not in active: pending.append(dep)
        states = {}
        for name in active:
            recipe = t.recipes.get(name, {}); deps = recipe.get('ingredients', [])
            counts = {dep: self.ownership(dep) for dep in deps}
            floors = {dep: (recipe.get('quantities') or {}).get(dep, self.quotas.get(name, 1)) for dep in deps}
            missing = [dep for dep in deps if counts[dep]['lower_bound'] < floors[dep]]
            assessment = self.assess('craft 1 '+q(name))
            enough = self.ownership(name)['lower_bound'] >= demands[name]
            status = ('COMPLETE' if enough else 'BLOCKED' if assessment['status'] == REJECT or
                      any(counts[dep]['exact'] for dep in missing) else 'UNKNOWN' if not deps or missing
                      or not recipe.get('stations') else 'READY')
            states[name] = {'status': status, 'required_floor': demands[name], 'owned': self.ownership(name),
                'known_recipe': bool(deps), 'missing_inputs': missing, 'input_floors': floors,
                'recipe': copy.deepcopy(recipe), 'assessment': assessment,
                'quantity_certainty': 'conditional_observed_sample' if recipe.get('quantities') else 'UNKNOWN',
                'readiness_scope': 'observed conditions and inherited FIFO floor; never native legality guarantee'}
        unresolved = [name for name, state in states.items() if state['status'] != 'COMPLETE' and not state['known_recipe']]
        view = {'goal': goal, 'known_dependency_nodes': known, 'active_nodes': active,
                'unresolved_recipe_nodes': unresolved, 'nodes': states,
                'edges': {n: list(t.recipes.get(n, {}).get('ingredients', [])) for n in known},
                'unknown_scope': 'missing recipe may be a raw material; possible bridges are not graph edges'}
        if synchronize:
            before = list(self.queue)
            needed = [n for n in active if states[n]['status'] != 'COMPLETE']
            self.queue = list(dict.fromkeys([n for n in self.queue if n in needed]+needed))
            for name in needed:
                if name != goal: self.queue_needs[name] = max(self.queue_needs.get(name, 1), demands[name])
            if before != self.queue:
                self.events.append({'event': 'stage11_public_fifo_update', 'step': t.state.get('step'),
                    'before': before, 'after': list(self.queue), 'basis': copy.deepcopy(view['edges'])})
        self.goal_view = view
        return view

    def allowed11(self, action):
        if not action or parse_action(action).verb in {'invalid', 'wait', 'drop', 'discard'}: return False
        return (self.assess(action)['status'] != REJECT
                and self.actual_visits.get(digest([action, self.context(action)]), 0) < 2)

    def candidate(self, action, rank, kind, target, basis, **extra):
        return {'action': action, 'priority': rank, 'kind': kind, 'target': target,
                'basis': basis, 'assessment': self.assess(action) if action else None,
                'eligible': self.allowed11(action), **extra}

    def completion_proposal(self, action, view):
        p = parse_action(action); node = view['nodes'].get(view['goal'], {})
        return (p.target == view['goal'] and node.get('status') != 'COMPLETE'
                and p.verb in {'craft', 'pick up', 'store', 'take out'}
                and self.base_progress(action) and self.allowed11(action))

    def exploration_candidates(self, needed):
        t = self.table; view = self.public_goal_view(); goal = view['goal']
        if not goal or self.exploration_spent >= self.EXPLORATION_LIMIT: return []
        confirmed = set(view['known_dependency_nodes']); unresolved = set(view['unresolved_recipe_nodes'])
        visible = self.visible(); produced = set(self.produced11) | set(self.quantity_facts.produced)
        stations = {s for r in t.recipes.values() for s in r.get('stations', [])}
        material_sources = {x for r in t.recipes.values() for x in r.get('ingredients', [])}
        candidates = []
        for item in sorted(visible):
            if item in t.inspected or item in self.probes: continue
            rank = (0 if item in unresolved or item == goal else 1 if item in confirmed else
                    2 if item in produced else 3 if item in set(needed) | material_sources else 4)
            if item in stations or item in t.containers:
                rank = min(rank, 1) if item in confirmed else 4
            candidates.append(self.candidate('inspect '+q(item), rank, 'inspect_public_object', item,
                {'confirmed_goal_connection': item in confirmed, 'unresolved_node': item in unresolved,
                 'actually_produced': item in produced, 'observed_material_source': item in material_sources,
                 'unknown_downstream_connection': item not in confirmed}, preparation_steps=0))
        supplies = set(visible)
        for data in t.places.values(): supplies.update(n for n, count in data['objects'].items() if count > 0)
        if sum(self.trials.values()) < self.TRIAL_LIMIT:
            for product, recipe in sorted(t.recipes.items()):
                deps = recipe.get('ingredients', [])
                if (not deps or product == goal or product in t.inspected or product in produced
                        or self.trials.get(product, 0) >= 1 or product in supplies): continue
                if not all(n in supplies or self.ownership(n)['lower_bound'] > 0 for n in deps): continue
                # Speculative forward exploration must not consume the retained
                # goal or a completed necessary intermediate. No quantity solver.
                protected = [n for n in deps if n == goal or (n in confirmed and
                    t.recipes.get(n, {}).get('ingredients') and product not in confirmed
                    and self.ownership(n)['lower_bound'] <= view['nodes'].get(n, {}).get('required_floor', 1))]
                if protected: continue
                action = None; preparation = 0
                for dep in deps:
                    if self.ownership(dep)['lower_bound'] < 1:
                        action = self._acquire(dep, 1, confirmed | set(deps)); preparation = 1; break
                if not action and all(self.ownership(dep)['lower_bound'] >= 1 for dep in deps):
                    required_stations = recipe.get('stations', [])
                    if required_stations and not all((t.state.get('ground') or {}).get(s, 0) for s in required_stations):
                        locations = [loc for loc, data in t.places.items() if t.path(loc)
                                     and all(data['objects'].get(s, 0) for s in required_stations)]
                        if locations:
                            action = self._move(min(locations, key=lambda loc: (len(t.path(loc)), loc))); preparation = 1
                    else: action = 'craft 1 '+q(product)
                if action:
                    candidates.append(self.candidate(action, 1 if product in confirmed else 2,
                        'known_forward_bridge', product, {'public_recipe': copy.deepcopy(recipe),
                        'unresolved_nodes': sorted(unresolved), 'confirmed_goal_connection': product in confirmed,
                        'unknown_downstream_connection': product not in confirmed,
                        'claim': 'possible source of further rules, not a known hidden dependency'}, preparation_steps=preparation))
        # Deterministic ordering uses evidence priority, immediate feasibility,
        # then public names. It contains no target-specific vocabulary matches.
        return sorted(candidates, key=lambda c: (c['priority'], c['preparation_steps'], c['target'], c['action']))[:self.MAX_CANDIDATES]

    def _explore(self, needed):
        if not self.goal_ranking: return super()._explore(needed)
        for record in self.retry_records.values():
            p = parse_action(record['action'])
            if p.verb == 'inspect' and record['state'] == 'BLOCKED_BY_PRECONDITION' and self.retry_allowed(record['action']):
                self.probes.pop(p.target, None)
        candidates = self.exploration_candidates(needed)
        self.ranked11 = candidates
        selected = next((c for c in candidates if c['eligible'] and c['priority'] < 4), None)
        if selected:
            self.selected11 = copy.deepcopy(selected)
            return selected['action']
        return super()._explore(needed)

    def execution_candidates(self, view):
        t = self.table; candidates = []; confirmed = set(view['known_dependency_nodes'])
        order = list(dict.fromkeys([view['goal']]+self.queue+view['active_nodes']))
        for item in order:
            node = view['nodes'].get(item)
            if not node or node['status'] == 'COMPLETE': continue
            acquire = self._acquire(item, node['required_floor'], confirmed)
            if acquire:
                verb = parse_action(acquire).verb
                candidates.append(self.candidate(acquire, 0 if item == view['goal'] and verb in {'store', 'pick up', 'take out'} else
                    1 if verb in {'store', 'pick up', 'take out'} else 3,
                    'acquire_necessary', item, {'confirmed_path': view['edges'], 'node': node}, preparation_steps=0))
            if node['known_recipe'] and not node['missing_inputs'] and not (t.state.get('ground') or {}).get(item, 0):
                action = 'craft 1 '+q(item)
                candidates.append(self.candidate(action, 0 if item == view['goal'] else 1,
                    'execute_necessary', item, {'node': node, 'confirmed_path': view['edges']}, preparation_steps=0))
        for item in sorted(set(self.produced11) & confirmed & self.visible()):
            if self.exploration_spent >= self.EXPLORATION_LIMIT: break
            if item not in t.inspected:
                candidates.append(self.candidate('inspect '+q(item), 2, 'inspect_necessary_product', item,
                    {'actually_produced_at': self.produced11[item], 'confirmed_path': view['edges']}, preparation_steps=0))
        return sorted(candidates, key=lambda c: (c['priority'], order.index(c['target']) if c['target'] in order else len(order), c['action']))[:self.MAX_CANDIDATES]

    def choose(self, obs, base_action):
        self.table.observe(obs)
        self.decision11 = {}; self.selected11 = None; self.ranked11 = []
        view = self.public_goal_view(synchronize=self.timely_execution)
        before_probe = {k: copy.deepcopy(getattr(self, k)) for k in ['probes', 'trials', 'exploration_spent']}
        legacy = super().choose(obs, base_action)
        action = legacy; selection = self.selected11; execution = []
        if selection and (parse_action(selection['action']).verb, parse_action(selection['action']).target) != (parse_action(legacy).verb, parse_action(legacy).target):
            selection = None
        if self.timely_execution:
            view = self.public_goal_view(synchronize=True)
            execution = self.execution_candidates(view)
            candidate = next((c for c in execution if c['eligible']), None)
            base_node = view['nodes'].get(parse_action(base_action).target, {})
            legacy_node = view['nodes'].get(parse_action(legacy).target, {})
            if self.completion_proposal(base_action, view):
                action = base_action; selection = {'kind': 'preserve_final_base', 'basis': base_node, 'action': action}
            elif candidate and candidate['priority'] == 0:
                action = candidate['action']; selection = candidate
            elif (base_node and base_node['status'] != 'COMPLETE' and self.base_progress(base_action)
                  and self.allowed11(base_action)):
                action = base_action; selection = {'kind': 'preserve_necessary_base', 'basis': base_node, 'action': action}
            elif (legacy_node and legacy_node['status'] != 'COMPLETE' and self.base_progress(legacy)
                  and self.allowed11(legacy)):
                selection = {'kind': 'preserve_necessary_S1', 'basis': legacy_node, 'action': legacy}
            elif candidate:
                action = candidate['action']; selection = candidate
        # A ranking replacement should never preempt a public final-goal move.
        if self.completion_proposal(base_action, view):
            action = base_action; selection = {'kind': 'preserve_final_base', 'basis': view['nodes'].get(view['goal']), 'action': action}
        if selection and action != legacy:
            for key, value in before_probe.items(): setattr(self, key, value)
            self.pending_probe = None; self.explore_pending = None
        if selection and selection.get('kind') in {'inspect_public_object', 'known_forward_bridge', 'inspect_necessary_product'}:
            p = parse_action(action)
            if p.verb == 'inspect': self.probes[p.target] = {'step': self.table.state.get('step'), 'location': self.table.state.get('location')}
            if p.verb == 'craft' and selection['kind'] == 'known_forward_bridge':
                self.trials[p.target] = self.trials.get(p.target, 0)+1
            action = self._probe(action, 'stage11_'+selection['kind'], selection['basis']) or legacy
        action = self._batch_action(action)
        # Cancel inherited speculative probe bookkeeping when a different
        # actual action was selected; public FIFO and batching remain in force.
        if self.pending_probe and parse_action(self.pending_probe['action']).target != parse_action(action).target:
            self.pending_probe = None; self.explore_pending = None
        self.decision11 = {'switches': {'goal_ranking': self.goal_ranking, 'timely_execution': self.timely_execution},
            'base_action': base_action, 'S1_with_rank_candidate': legacy, 'selected_action': action,
            'exploration_candidates': copy.deepcopy(self.ranked11), 'execution_candidates': execution,
            'selected': copy.deepcopy(selection), 'public_goal_view': copy.deepcopy(view),
            'queue': list(self.queue), 'extra_model_calls': 0, 'inherited_batch_rule': True,
            'candidate_limit': self.MAX_CANDIDATES, 'node_limit': self.NODE_LIMIT}
        self.last_choice.update(action=action, queue=list(self.queue), resource_table=self.table.to_dict(),
            reason=('stage11_'+selection['kind']) if selection else self.last_choice.get('reason'), stage11=copy.deepcopy(self.decision11))
        return action

    def observe(self, before, action, after):
        super().observe(before, action, after)
        p = parse_action(action)
        if p.verb == 'craft' and 'successfully crafted' in self.table.state['feedback']:
            self.produced11[p.target] = after.get('step')
        self.public_goal_view(synchronize=self.timely_execution and self.in_episode)

    @classmethod
    def from_dict(cls, data):
        obj = cls(data.get('goal_ranking', False), data.get('timely_execution', False))
        obj.__dict__.update(copy.deepcopy(data))
        obj.table = ResourceTable(**data['table']); obj.quantity_facts = PublicFacts.from_dict(data['quantity_facts'])
        return obj


def make_controller(method):
    if method not in METHODS: raise ValueError(method)
    if method in {'E0', 'E1'}: return ResourceController(False, False)
    return GoalController(method in {'E2', 'E4'}, method in {'E3', 'E4'})


def restore_controller(data):
    return GoalController.from_dict(data) if data.get('stage11') else ResourceController.from_dict(data)


def adapted(data, method):
    obj = make_controller(method)
    keys = ResourceController(False, False).__dict__
    state = obj.to_dict() | {k: copy.deepcopy(v) for k, v in data.items() if k in keys}
    state.update(opportunistic=False, storage=False, storage_intent=None, selected_meta=None)
    state['flags'] = copy.deepcopy(obj.flags)
    if method not in {'E0', 'E1'}:
        state['produced11'] = {name: None for name in data.get('quantity_facts', {}).get('produced', {})}
        for key in ['produced11', 'goal_view']:
            if key in data: state[key] = copy.deepcopy(data[key])
    return restore_controller(state)
