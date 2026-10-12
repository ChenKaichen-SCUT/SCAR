"""Public-observation-only repairs. No game, evaluator or task-catalogue imports.

F1 and F2 share exactly the same conditions, FIFO, quantities and candidates.
F2 alone retains a bounded stack of blocked actions across real transitions.
UNKNOWN permits a scoped trial; it is never silently converted into REJECT.
"""
import copy
import math
import re

from scar.io import digest
from scar_sequence.planner import q
from scar_sequence.public import ResourceTable
from scar_unknown17.facts import PublicFacts
from scar_unknown17_stage7.controller import Stage7Controller, CONFIGS
from scar_stage8.controller import ReliableController, NoCandidate
from scar_v3.state import parse_action

METHODS = ['F0', 'F-Old', 'F1', 'F2']
SUPPORTED, REJECT, UNKNOWN = 'SUPPORTED', 'REJECT', 'UNKNOWN'


class RepairController(ReliableController):
    RECOVERY_ACTIONS = 8
    RECOVERY_DEPTH = 4
    MAX_CANDIDATES = 48
    MAX_PLAN_REBUILDS = 2
    MAX_STAGNANT = 2

    def __init__(self, active=False):
        super().__init__('P3')
        self.active_recovery = active
        self.stage9 = True
        self.condition_log = []
        self.recovery_records = []
        self.recovery = None
        self.rebuilds = {}
        self.pending_recovery = None
        self.actual_trials = {}
        self.decision9 = {}

    def ownership(self, item):
        t = self.table
        known = t.count(item)
        exact = (t.state.get('hands') is not None and t.state.get('equipment') is not None
                 and all(c.get('counts') is not None for n, c in t.containers.items() if t.carried(n)))
        return {'lower_bound': known or 0, 'exact': exact, 'value': known,
                'step': t.state.get('step'), 'scope': 'current carried public evidence'}

    def requirements(self, item):
        # Nominal public numbers are planning targets, not inferred hidden rules.
        weights = self.public_quantity_rules.get(item, {}).get('quantities', {})
        return {x: max(1, math.ceil(weights.get(x, 1)))
                for x in self.table.recipes.get(item, {}).get('ingredients', [])}

    def demand_record(self, item):
        goal = parse_action(self.target).target
        parents = []
        floor = self.amount if item == goal else 1
        for parent in sorted(self.table.recipes):
            req = self.requirements(parent)
            if item not in req or parent == item:
                continue
            needed = self.amount if parent == goal else 1
            if self.ownership(parent)['lower_bound'] < needed:
                parents.append({'parent': parent, 'amount': req[item],
                                'goal_connection': parent in self._all_needed(goal)})
                # Disconnected forward links justify finite exploration, not an
                # unlimited global demand assembled from every possible recipe.
                if parent in self.queue or parent in self._all_needed(goal):
                    floor = max(floor, req[item])
        return {'owned': self.ownership(item), 'minimum_known_demand': floor,
                'unfinished_public_parents': parents,
                'complete_task_demand_known': item == goal,
                'unknown_extra_demand': item != goal,
                'retained_final_requirement': self.amount if item == goal else 0}

    def public_demand(self, item):
        return self.demand_record(item)['minimum_known_demand']

    def action_context(self, action):
        p = parse_action(action)
        if p.verb == 'craft':
            t = self.table
            r = t.recipes.get(p.target, {})
            return {'location': t.state.get('location'),
                    'stations': {s: (t.state.get('ground') or {}).get(s, 0) for s in r.get('stations', [])},
                    'materials': {x: self.ownership(x) | {'step': None} for x in r.get('ingredients', [])},
                    'recipe_names': r.get('ingredients', []),
                    'public_weights': self.public_quantity_rules.get(p.target, {}).get('quantities'),
                    'carried': ({k: t.state.get(k) for k in ['hands', 'equipment']} if not r.get('ingredients') else None),
                    'containers': {n: (c.get('counts') if not r.get('ingredients') or c.get('counts') is None else
                                      {x: c['counts'].get(x, 0) for x in r['ingredients']})
                                   for n, c in t.containers.items() if t.carried(n)}}
        return super().action_context(action)

    def retry_allowed(self, action):
        old = self.failed_actions.get(self.failure_key(action))
        return not old or old['context'] != self.action_context(action)

    def visit_key(self, action):
        return digest([action, self._signature(), {n: r.get('ingredients', []) for n, r in self.table.recipes.items()}])

    def assess(self, action):
        p = parse_action(action or '')
        t, s = self.table, self.table.state
        h, g = s.get('hands'), s.get('ground')
        conditions = []

        def add(kind, value, evidence, **kw):
            conditions.append({'kind': kind, 'status': value, 'evidence': evidence,
                               'observed_step': s.get('step'),
                               'valid_until': 'relevant public conditions change', **kw})

        if p.verb == 'invalid':
            add('syntax', REJECT, 'unparseable action')
        old = self.failed_actions.get(self.failure_key(action or ''))
        if old and old['context'] == self.action_context(action or ''):
            add(old.get('obstacle', 'unchanged_failure'), REJECT, old['feedback'],
                failure_step=old.get('step'), action=old['action'])
        if self.no_progress.get(digest([action, self.action_context(action or '')]), 0) >= 2:
            add('no_progress', REJECT, 'two actual attempts with identical relevant public state')
        if self.visits.get(self.visit_key(action), 0) >= 2 and p.verb != 'wait':
            add('state_cycle', REJECT, 'same actual action executed twice in the same resources/location/recipe knowledge')
        if p.verb in {'pick up', 'take out'}:
            add('hands', UNKNOWN if h is None else SUPPORTED if sum(h.values()) < 2 else REJECT,
                {'observed_hands': h, 'capacity': 2})
        if p.verb == 'pick up':
            add('ground_presence', UNKNOWN if g is None else SUPPORTED if g.get(p.target, 0) > 0 else REJECT,
                {'target': p.target, 'current_ground': g})
        if p.verb in {'store', 'take out'} and p.args:
            name = t.inventory if p.args[-1] == 'inventory' else p.args[-1]
            c = t.containers.get(name, {})
            access = t.access(name) if name else None
            add('container_access', UNKNOWN if access is None else SUPPORTED if access else REJECT,
                {'container': name, 'current_access': access}, container=name)
            if p.verb == 'store':
                available = (h or {}).get(p.target, 0) + (g or {}).get(p.target, 0)
                add('transfer_source', SUPPORTED if available > 0 else UNKNOWN if h is None or g is None else REJECT,
                    {'target': p.target, 'current_held_and_ground': available})
                load, cap = c.get('load'), c.get('capacity')
                add('container_capacity', UNKNOWN if load is None or cap is None else REJECT if load >= cap else UNKNOWN,
                    {'container': name, 'load': load, 'capacity': cap, 'item_volume': UNKNOWN}, container=name)
                if name == p.target:
                    add('self_storage', REJECT, 'container cannot store itself')
            else:
                counts = c.get('counts')
                add('container_contents', UNKNOWN if counts is None else SUPPORTED if counts.get(p.target, 0) > 0 else REJECT,
                    {'container': name, 'last_observed_counts': counts}, container=name)
        if p.verb == 'enter':
            status = t.enter_status(p.target)
            add('route', REJECT if s.get('neighbors') is not None and p.target not in s['neighbors'] else
                REJECT if status == REJECT else SUPPORTED if status in {'UNLOCKED', SUPPORTED} else UNKNOWN,
                {'destination': p.target, 'neighbors': s.get('neighbors'), 'guard': status})
        if p.verb == 'craft':
            r = t.recipes.get(p.target, {})
            stations = r.get('stations')
            add('station', UNKNOWN if not stations or g is None else SUPPORTED if all(g.get(x, 0) for x in stations) else REJECT,
                {'required': stations, 'current_ground': g})
            req = self.requirements(p.target)
            if not req:
                add('recipe', UNKNOWN, 'ingredient names not publicly disclosed; no inferred missing item')
            for item, need in req.items():
                own = self.ownership(item)
                weights_known = item in self.public_quantity_rules.get(p.target, {}).get('quantities', {})
                status = SUPPORTED if own['lower_bound'] >= need else REJECT if own['exact'] and (
                    weights_known or own['lower_bound'] == 0) else UNKNOWN
                add('materials', status, {'item': item, 'owned': own, 'planning_need': need,
                    'nominal_weight_public': weights_known}, item=item, amount=need)
            goal = parse_action(self.target).target
            if goal in req and self.ownership(goal)['lower_bound'] <= self.amount:
                add('goal_reserve', REJECT, {'goal': goal, 'required_possession': self.amount})
            demand = self.demand_record(p.target)
            if p.target == goal and demand['owned']['lower_bound'] >= self.amount:
                add('goal_complete', REJECT, demand)
            # Current lower bound is never interpreted as a permanent upper bound.
            elif p.target != goal and self.actual_trials.get(p.target, 0) >= 2 and not any(
                    demand['owned']['lower_bound'] < x['amount'] for x in demand['unfinished_public_parents']):
                add('speculative_budget', REJECT, {'successful_trials': self.actual_trials[p.target],
                    'reason': 'no currently unfilled public parent justifies more production'})
        negative = self.negative_ground.get(p.target)
        if negative and negative['location'] == s.get('location') and negative['ground'] == (g or {}).get(p.target, 0):
            if p.verb == 'pick up' or (p.verb == 'store' and p.args[0].isdigit() and int(p.args[0]) > (h or {}).get(p.target, 0)):
                add('ground_presence', REJECT, negative['feedback'])
        if not conditions:
            add('public_trial', UNKNOWN, 'no negative condition established; scoped real feedback required')
        status = REJECT if any(x['status'] == REJECT for x in conditions) else UNKNOWN if any(x['status'] == UNKNOWN for x in conditions) else SUPPORTED
        return {'action': action, 'status': status, 'conditions': conditions}

    def admissible(self, action):
        if not action or self.candidates >= self.MAX_CANDIDATES:
            return False
        self.candidates += 1
        result = self.assess(action)
        self.condition_log.append(result)
        return result['status'] != REJECT

    def collection_options(self, name, need, base=None):
        t, s = self.table, self.table.state
        h, g = s.get('hands') or {}, s.get('ground') or {}
        options = []
        deficit = max(0, math.ceil(need - self.ownership(name)['lower_bound']))
        if not deficit:
            return options
        if g.get(name, 0) > 0:
            if t.inventory:
                # Engine store moves held copies first, THEN visible ground copies.
                n = int(h.get(name, 0) + min(g[name], deficit))
                options.append(f'store {n} {q(name)} inventory')
            options.append('pick up ' + q(name))
        for c, data in sorted(t.containers.items()):
            if not t.carried(c) and t.access(c) and (data.get('counts') or {}).get(name, 0):
                options.append(f'take out {q(name)} {q(c)}')
        if base:
            p = parse_action(base)
            if p.target == name and p.verb in {'pick up', 'store', 'take out'}:
                options.append(base)
        def gain(a):
            p = parse_action(a)
            if p.verb != 'store':
                return 1
            c = t.inventory if p.args[-1] == 'inventory' else p.args[-1]
            return max(0, min(g.get(name, 0), int(p.args[0]) - h.get(name, 0))) if t.carried(c) else 0
        return sorted(dict.fromkeys(options), key=lambda a: (-gain(a), a != base))

    def collection(self, name, need, base=None):
        return next((a for a in self.collection_options(name, need, base) if self.admissible(a)), None)

    def free_hands(self, preferred=None):
        t = self.table
        hands = t.state.get('hands') or {}
        goal = parse_action(self.target).target
        options = []
        for name in sorted(hands, key=lambda x: (x != preferred, x == goal, x)):
            if name in t.containers:
                if not t.inventory:
                    options.append('equip ' + q(name))
                continue
            if t.inventory:
                options.append(f'store {int(hands[name])} {q(name)} inventory')
        if not t.inventory:
            for name in sorted(t.containers):
                if t.access(name) and not t.carried(name):
                    for item in sorted(hands):
                        if item != goal and item not in t.containers:
                            options.append(f'store {int(hands[item])} {q(item)} {q(name)}')
        return options

    def acquire_options(self, name, amount):
        t = self.table
        options = self.collection_options(name, amount)
        for c, data in sorted(t.containers.items()):
            if t.carried(c) and data.get('counts') is None:
                options.append('inspect ' + q('inventory' if c == t.inventory else c))
        for loc, data in sorted(t.places.items(), key=lambda kv: (len(t.path(kv[0]) or [0]*99), kv[0])):
            if loc != t.state.get('location') and data['objects'].get(name, 0) and t.path(loc):
                options.append('enter ' + q(t.path(loc)[0]))
        if t.recipes.get(name, {}).get('ingredients'):
            options.append(f'craft {min(4, max(1, math.ceil(amount-self.ownership(name)["lower_bound"])))} {q(name)}')
        return list(dict.fromkeys(options))

    def _acquire(self, name, amount, protect, use_container=True):
        if self.ownership(name)['lower_bound'] >= amount:
            return None
        for a in self.acquire_options(name, amount):
            if parse_action(a).verb != 'craft' and self.admissible(a):
                return a
        if (self.table.state.get('ground') or {}).get(name, 0) and sum((self.table.state.get('hands') or {}).values()) >= 2:
            for a in self.free_hands(name):
                if self.admissible(a):
                    return a
        if a := self._container():
            if self.admissible(a):
                return a
        return None

    def _station(self, recipe):
        t = self.table
        stations = t.recipes.get(recipe, {}).get('stations', [])
        if not stations or all((t.state.get('ground') or {}).get(s, 0) for s in stations):
            return None
        for loc, data in sorted(t.places.items()):
            if all(data['objects'].get(s, 0) for s in stations) and t.path(loc):
                return 'enter ' + q(t.path(loc)[0])
        return self._location_explore()

    def _fifo(self, item):
        # Recalculate active requirements; ambiguous failures are not quotas for
        # every ingredient, nor do completed intermediate nodes stay complete.
        if item not in self.queue:
            self.queue.append(item)
        for _ in range(min(self.MAX_NODES, 2*len(self.queue)+8)):
            if not self.queue:
                return None
            head = self.queue[0]
            need = self.amount if head == item else self.queue_needs.get(head, 1)
            if self.ownership(head)['lower_bound'] >= need:
                self.queue.pop(0)
                continue
            if a := self._acquire(head, need, set(self.queue)):
                return a
            req = self.requirements(head)
            missing = [x for x, n in req.items() if self.ownership(x)['lower_bound'] < n]
            if missing:
                self.queue.pop(0)
                for dep in missing:
                    self.queue_needs[dep] = req[dep]
                    if dep != head and dep not in self.queue:
                        self.queue.append(dep)
                self.queue.append(head)
                continue
            if req:
                return self._station(head) or f'craft {min(4, max(1, math.ceil(need-self.ownership(head)["lower_bound"])))} {q(head)}'
            return self._explore(set(self.queue))
        return None

    def _explore(self, needed):
        if self.exploration_spent >= self.EXPLORATION_LIMIT:
            return None
        t = self.table
        goal = parse_action(self.target).target
        visible = self.visible()
        stations = {x for r in t.recipes.values() for x in r.get('stations', [])}
        for item in sorted(visible, key=lambda x: (x != self.last_produced, x not in needed, x in stations, x in t.containers, x)):
            if item not in t.inspected and item not in self.probes:
                a = 'inspect ' + q(item)
                if self.admissible(a):
                    self.probes[item] = {'step': t.state.get('step'), 'location': t.state.get('location')}
                    return self._probe(a, 'inspect publicly visible entity at unresolved dependency', {'entity': item})
        supplies = set(visible)
        for place in t.places.values():
            supplies.update(place['objects'])
        products = []
        for product, r in t.recipes.items():
            deps = r.get('ingredients', [])
            if not deps or product == goal or goal in deps or self.actual_trials.get(product, 0) >= 2:
                continue
            if self.ownership(product)['lower_bound'] > 0 or any(v['objects'].get(product, 0) for v in t.places.values()):
                continue
            if not all(x in supplies or t.recipes.get(x, {}).get('ingredients') for x in deps):
                continue
            products.append((product not in needed, -len(set(product.split('_')) & set(goal.split('_'))), len(deps), product))
        for *_, product in sorted(products):
            req = self.requirements(product)
            for dep, n in req.items():
                if self.ownership(dep)['lower_bound'] < n:
                    # Return a bounded preparation candidate, even when its own
                    # condition is blocked: caller can repair that condition.
                    options = self.acquire_options(dep, n)
                    if options:
                        return options[0]
                    break
            else:
                return self._station(product) or 'craft 1 ' + q(product)
        return self._location_explore()

    def ready_nodes(self):
        return [x for x in dict.fromkeys(self.queue + [parse_action(self.target).target])
                if self.table.recipes.get(x, {}).get('ingredients')
                and self.assess('craft 1 ' + q(x))['status'] != REJECT]

    def _batch_action(self, action):
        # Same quantity decision in F1/F2; do not apply the older default-two rule.
        return action

    def protect_craft(self, action, base):
        p = parse_action(action or '')
        if p.verb != 'craft':
            return action
        need = self.public_demand(p.target)
        if a := self.collection(p.target, max(need, self.ownership(p.target)['lower_bound']+1), base):
            return a
        amount = min(4, max(1, int(p.args[0])))
        # UNKNOWN future demand permits one justified production attempt, not
        # an unrestricted speculative batch or consumption of the held goal.
        deficit = max(1, math.ceil(need-self.ownership(p.target)['lower_bound']))
        return f'craft {min(amount, deficit)} {q(p.target)}'

    def repairs(self, action, assessment=None):
        a = assessment or self.assess(action)
        p = parse_action(action)
        t = self.table
        options = []
        kinds = {x['kind'] for x in a['conditions'] if x['status'] != SUPPORTED}
        if 'hands' in kinds:
            options += self.collection_options(p.target, self.ownership(p.target)['lower_bound']+1)
            options += self.free_hands(p.target)
        if kinds & {'container_capacity', 'container_contents', 'container_access'}:
            for x in a['conditions']:
                c = x.get('container')
                if c and t.access(c) and (t.containers.get(c, {}).get('counts') is None or t.containers.get(c, {}).get('load') is None):
                    options.append('inspect ' + q('inventory' if c == t.inventory else c))
            if not t.inventory and (candidate := self._container()):
                options.append(candidate)
            options += self.free_hands(p.target)
        if p.verb == 'craft':
            for item, amount in self.requirements(p.target).items():
                if self.ownership(item)['lower_bound'] < amount:
                    options += self.acquire_options(item, amount)
            for c, data in sorted(t.containers.items()):
                if t.carried(c) and data.get('counts') is None:
                    options.append('inspect ' + q('inventory' if c == t.inventory else c))
            if int(p.args[0]) > 1:
                options.append('craft 1 ' + q(p.target))
        # Acquire missing material at its present location before travelling back
        # to a station. Otherwise a material/station pair creates a shuttle loop.
        if 'station' in kinds and p.verb == 'craft':
            if move := self._station(p.target):
                options.append(move)
        if not options or kinds & {'recipe', 'unchanged_failure', 'materials', 'no_progress'}:
            if explore := self._explore({p.target}):
                options.append(explore)
        return [x for x in dict.fromkeys(options) if x != action][:12]

    def start_recovery(self, action, assessment, cause):
        if not self.active_recovery or self.recovery or parse_action(action).verb not in {'craft', 'pick up', 'take out', 'store', 'enter'}:
            return
        key = digest([self.target, action, self.action_context(action)])
        if self.rebuilds.get(key, 0) >= self.MAX_PLAN_REBUILDS:
            return
        self.rebuilds[key] = self.rebuilds.get(key, 0)+1
        record = {'id': len(self.recovery_records)+1, 'original_goal': self.target,
                  'blocked_action': action, 'obstacle_types': sorted({c['kind'] for c in assessment['conditions'] if c['status'] != SUPPORTED}),
                  'public_evidence': copy.deepcopy(assessment), 'origin': cause,
                  'created_step': self.table.state.get('step'), 'remaining_actions': self.RECOVERY_ACTIONS,
                  'stack': [{'action': action, 'conditions': copy.deepcopy(assessment), 'entered_context': self.action_context(action)}],
                  'attempts': [], 'conditions_released': [], 'solver_visits': {}, 'stagnant': 0,
                  'retry_when': 'fresh assessment admits original action after relevant conditions change',
                  'cancel_when': 'goal changes, depth/action budget, repeated solver node, or no-progress limit', 'status': 'active'}
        self.recovery_records.append(record)
        self.recovery = record
        self.events.append({'event': 'gpar_created', 'record': copy.deepcopy(record)})

    def cancel_recovery(self, reason):
        if self.recovery:
            self.recovery.update(status=reason, ended_step=self.table.state.get('step'))
            self.events.append({'event': 'gpar_finished', 'record': copy.deepcopy(self.recovery)})
        self.recovery = None
        self.pending_recovery = None

    def plan_action(self):
        r = self.recovery
        if not r:
            return None
        if r['original_goal'] != self.target or r['remaining_actions'] <= 0 or r['stagnant'] >= self.MAX_STAGNANT:
            self.cancel_recovery('cancelled_goal_budget_or_stagnation')
            return None
        for _ in range(self.RECOVERY_DEPTH):
            node = r['stack'][-1]
            a = node['action']
            assessment = self.assess(a)
            key = digest([a, self.action_context(a)])
            r['solver_visits'][key] = r['solver_visits'].get(key, 0)+1
            if r['solver_visits'][key] > 2:
                self.cancel_recovery('cancelled_repeated_solver_node')
                return None
            node['conditions'] = assessment
            if self.admissible(a):
                self.pending_recovery = {'event_id': r['id'], 'node_action': a, 'action': a,
                                         'retry_original': len(r['stack']) == 1, 'assessment_before': assessment}
                return a
            repairs = self.repairs(a, assessment)
            for candidate in repairs:
                if self.admissible(candidate):
                    self.pending_recovery = {'event_id': r['id'], 'node_action': a, 'action': candidate,
                                             'retry_original': False, 'assessment_before': assessment}
                    return candidate
            blocked = next((x for x in repairs if x not in [n['action'] for n in r['stack']]), None)
            if not blocked or len(r['stack']) >= self.RECOVERY_DEPTH:
                self.cancel_recovery('cancelled_no_public_path_or_depth')
                return None
            r['stack'].append({'action': blocked, 'conditions': self.assess(blocked),
                               'entered_context': self.action_context(blocked)})
            self.events.append({'event': 'gpar_subgoal_created', 'event_id': r['id'], 'action': blocked,
                                'depth': len(r['stack']), 'retained_goal': self.target})
        return None

    def choose(self, obs, base_action):
        self.table.observe(obs)
        self.candidates = self.search_nodes = self.depth_peak = 0
        self.solving = []
        self.condition_log = []
        self.safety_decision = {}
        self.stage7_decision = {}
        self.mechanism_decision = {}
        self.decision9 = {'active_recovery': self.active_recovery, 'rejected': [], 'alternatives': []}
        self.pending_recovery = None
        goal = parse_action(self.target).target
        # Immediate public goal acquisition always outranks planning machinery.
        action = self.collection(goal, self.amount, base_action)
        if action:
            self.decision9['direct_goal_collection'] = True
        if not action and self.active_recovery:
            action = self.plan_action()
        if not action:
            try:
                structured = self._fifo(goal) if self.ownership(goal)['lower_bound'] < self.amount else None
            except NoCandidate:
                structured = None
            for candidate in dict.fromkeys([structured, base_action]):
                if not candidate or candidate == 'wait':
                    continue
                candidate = self.protect_craft(candidate, base_action)
                assessment = self.assess(candidate)
                if self.admissible(candidate):
                    action = candidate
                    break
                self.decision9['rejected'].append(assessment)
                self.start_recovery(candidate, assessment, 'public_condition_veto')
                if self.active_recovery and (action := self.plan_action()):
                    break
                for alternative in self.repairs(candidate, assessment):
                    if self.admissible(alternative):
                        action = alternative
                        self.decision9['alternatives'].append({'blocked': candidate, 'selected': alternative})
                        break
                if action:
                    break
        if not action:
            # Exhausted plans yield to another evidenced frontier; no reason-free
            # wait loop and no arbitrary resource-destroying action as fallback.
            options = self.free_hands() + [self._explore({goal}), self._location_explore(), base_action]
            for candidate in options:
                if candidate and candidate != 'wait' and self.admissible(candidate):
                    action = candidate
                    break
        if not action:
            action = 'wait'
            self.decision9['no_candidate'] = True
            self.decision9['wait_reason'] = 'bounded evidenced alternatives exhausted; no supported progress action'
        self.decision9.update(condition_evaluations=copy.deepcopy(self.condition_log),
                              recovery_selection=copy.deepcopy(self.pending_recovery),
                              recovery=copy.deepcopy(self.recovery), candidate_checks=self.candidates,
                              demand=self.demand_record(parse_action(action).target))
        self.last_choice = {'action': action, 'target': self.target, 'queue': list(self.queue),
                            'resource_table': self.table.to_dict(), 'stage9': copy.deepcopy(self.decision9)}
        self.last_public_action_context = self.action_context(action)
        return action

    @staticmethod
    def obstacle(feedback):
        if 'space in hand' in feedback or 'hands are full' in feedback:
            return 'hands'
        if 'Missing necessary' in feedback:
            return 'station'
        if 'Cannot craft a single' in feedback:
            return 'materials'
        if 'capacity' in feedback or 'space' in feedback:
            return 'container_capacity'
        if 'not found' in feedback or 'not see' in feedback:
            return 'ground_presence'
        return 'unchanged_failure'

    def observe(self, before, action, after):
        self.table.observe(before)
        context = self.action_context(action)
        old_sig = self._signature()
        visit_key = self.visit_key(action)
        pending = copy.deepcopy(self.pending_recovery)
        old_quotas = dict(self.quotas)
        super().observe(before, action, after)
        if self.in_episode:
            self.visits[visit_key] = self.visits.get(visit_key, 0)+1
        # Ambiguous material failure supplies no per-ingredient numeric quota.
        self.quotas = old_quotas
        feedback = self.table.state.get('feedback', '')
        rejected = bool(re.search(r'Cannot |Invalid |cannot |not found|not see', feedback))
        p = parse_action(action)
        if rejected:
            self.failed_actions[self.failure_key(action)] = {'action': action, 'target': p.target,
                'context': context, 'feedback': feedback, 'obstacle': self.obstacle(feedback),
                'step': self.table.state.get('step')}
        if 'successfully crafted' in feedback:
            self.actual_trials[p.target] = self.actual_trials.get(p.target, 0)+1
        if self.recovery and pending and pending['event_id'] == self.recovery['id']:
            r = self.recovery
            after_assessment = self.assess(pending['node_action'])
            changed = self._signature() != old_sig
            old_rejected = {c['kind'] for c in pending['assessment_before']['conditions'] if c['status'] == REJECT}
            new_rejected = {c['kind'] for c in after_assessment['conditions'] if c['status'] == REJECT}
            released = sorted(old_rejected-new_rejected)
            r['conditions_released'] += [{'action': action, 'kinds': released, 'step': self.table.state.get('step')}] if released else []
            r['remaining_actions'] -= 1
            r['stagnant'] = 0 if changed or released else r['stagnant']+1
            attempt = {**pending, 'feedback': feedback, 'rejected': rejected,
                       'after_assessment': after_assessment, 'public_state_changed': changed,
                       'public_released_conditions': released, 'remaining_actions': r['remaining_actions'],
                       'retained_goal': self.target, 'step': self.table.state.get('step')}
            r['attempts'].append(attempt)
            self.events.append({'event': 'gpar_attempt', **copy.deepcopy(attempt)})
            if action == r['stack'][-1]['action'] and not rejected:
                r['stack'].pop()
                if not r['stack']:
                    self.cancel_recovery('original_action_succeeded')
                else:
                    self.events.append({'event': 'gpar_return_to_parent', 'event_id': r['id'],
                                        'parent': r['stack'][-1]['action'], 'retained_goal': self.target})
        if rejected and self.in_episode and not self.recovery:
            self.start_recovery(action, self.assess(action), 'real_feedback_failure')
        if self.ownership(parse_action(self.target).target)['lower_bound'] >= self.amount and self.target:
            self.cancel_recovery('final_goal_publicly_complete')
        self.pending_recovery = None

    @classmethod
    def from_dict(cls, data):
        obj = cls(data.get('active_recovery', False))
        obj.__dict__.update(copy.deepcopy(data))
        obj.table = ResourceTable(**data['table'])
        obj.quantity_facts = PublicFacts.from_dict(data['quantity_facts'])
        # Reconnect the active record after JSON roundtrip (identity is not JSON).
        if obj.recovery:
            obj.recovery = next(r for r in obj.recovery_records if r['id'] == obj.recovery['id'])
        return obj


def make_controller(method):
    if method == 'F0':
        return Stage7Controller(**CONFIGS['C1'])
    if method == 'F-Old':
        return ReliableController('P3')
    if method in {'F1', 'F2'}:
        return RepairController(method == 'F2')
    raise ValueError(method)


def restore_controller(data):
    if data.get('stage9'):
        return RepairController.from_dict(data)
    return ReliableController.from_dict(data) if 'safety' in data else Stage7Controller.from_dict(data)


def adapted(data, active=False):
    """Offline-only transplant: preserve public knowledge, discard old quota guesses."""
    obj = RepairController(active)
    fresh = obj.to_dict()
    fresh.update(copy.deepcopy(data))
    fresh.update(stage9=True, active_recovery=active, method='P3', flags=CONFIGS['C1'],
                 quotas={}, queue_needs={}, failed_actions={}, no_progress={},
                 recovery=None, recovery_records=[], pending_recovery=None)
    return RepairController.from_dict(fresh)
