"""Deterministic public-evidence controller. No oracle or world-file access.

SRP uses a persistent dependency graph; FIFO uses an ordinary rotating work queue.
Recipe quantities absent from observations remain UNKNOWN. Increasing an attempt
quota after ambiguous failure is a bounded exploration heuristic, not a learned
true recipe. Neither baseline claims autonomous effect learning.
"""
from collections import Counter
import re
import shlex
from scar.io import digest
from scar_v3.state import parse_action
from scar_sequence.public import ResourceTable


def q(value):
    return shlex.quote(value)


class Controller:
    def __init__(self, mode='srp'):
        self.mode = mode
        self.table = ResourceTable()
        self.target = ''; self.objective = ''; self.follow_public = False
        self.graph = {}; self.queue = []; self.events = []
        self.quotas = {}; self.attempts = {}; self.visits = {}
        self.last_choice = None; self.generation = 0
        self.amount = 1
        self.queue_needs = {}

    def set_goal(self, action, public_goal, follow_public=False):
        if action != self.target:
            if self.target:
                self.events.append({'event': 'goal_cancelled', 'old': self.target, 'new': action,
                                    'cause': 'explicit_goal_update'})
            self.graph, self.queue, self.quotas, self.visits = {}, [], {}, {}
            self.queue_needs = {}
            self.generation += 1
        self.target, self.objective, self.follow_public = action, public_goal, follow_public
        m=re.search(r'at least (\d+)',public_goal)
        self.amount=int(m[1]) if m else 1

    def observe(self, before, action, after):
        self.table.observe(before)
        self.table.observe(after, action)
        feedback = self.table.state['feedback']
        p = parse_action(action)
        if 'Cannot craft a single' in feedback:
            self.quotas[p.target] = min(4, self.quotas.get(p.target, 1) + 1)
            self.events.append({'event': 'local_repair', 'node': p.target,
                 'cause': 'ambiguous_quantity_failure', 'attempt_quota': self.quotas[p.target],
                 'truth_status': 'UNKNOWN', 'retained_goal': self.target})
        if re.search(r'Cannot |Invalid ', feedback):
            self.events.append({'event': 'prediction_mismatch', 'action': action,
                                'retained_goal': self.target, 'feedback': feedback})
        if 'successfully crafted' in feedback:
            self.events.append({'event': 'intermediate_produced', 'object': p.target,
                                'retained_goal': self.target})
        if self.follow_public and self.table.state.get('public_goal'):
            new = self.table.state['public_goal']
            if new != self.target:
                self.set_goal(new, 'Follow the current publicly announced task.', True)

    def _signature(self):
        t = self.table
        return digest([t.state.get(k) for k in ['location', 'hands', 'equipment', 'ground']] +
            [{n: c['counts'] for n,c in t.containers.items()}])

    def _move(self, destination):
        route = self.table.path(destination)
        if not route:
            return None
        if self.table.enter_status(route[0]) == 'REJECT':
            if self.table.count('key'):
                for name,c in self.table.containers.items():
                    if self.table.access(name) and c['counts'] and c['counts'].get('key'):
                        return f'take out key {q(name)}'
            return self._acquire('key', 1, protect={'key'}, use_container=False)
        return 'enter ' + q(route[0])

    def _container(self):
        t = self.table
        # Inventory identity requires the explicit equip-as-inventory response.
        if t.inventory:
            return None
        for name in sorted(t.containers):
            if name in (t.state.get('hands') or {}):
                return 'equip ' + q(name)
        for name in sorted(t.state.get('ground') or {}):
            if name in t.containers:
                if sum((t.state.get('hands') or {}).values()) < 2:
                    return 'pick up ' + q(name)
            elif any(part in name for part in ['bag', 'pouch', 'satchel', 'pack', 'crate']):
                if name not in t.inspected:
                    return 'inspect ' + q(name)
        return None

    def _acquire(self, name, amount, protect, use_container=True):
        t = self.table
        count = t.count(name)
        if count is not None and count >= amount:
            return None
        if use_container and (a := self._container()):
            return a
        # Resolve unknown carried contents before duplicating transfers.
        for c, data in t.containers.items():
            if t.carried(c) and data['counts'] is None:
                return 'inspect ' + q('inventory' if c == t.inventory else c)
        ground = t.state.get('ground') or {}
        if ground.get(name, 0) > 0:
            if t.inventory and use_container:
                # Collect the observed supply of this relevant material. Its true
                # future recipe quantity is unknown; the engine clips at capacity.
                n = max(1, int(ground[name]))
                return f'store {n} {q(name)} inventory'
            if sum((t.state.get('hands') or {}).values()) < 2:
                return 'pick up ' + q(name)
            for item in sorted(t.state.get('hands') or {}):
                if item not in protect and item not in t.containers:
                    return 'drop ' + q(item)  # remembered, recoverable ground storage
            return None
        for container,c in t.containers.items():
            if c['counts'] and c['counts'].get(name, 0):
                if t.access(container) and not t.carried(container):
                    if sum((t.state.get('hands') or {}).values()) < 2:
                        return 'pick up ' + q(container)
                elif c['location'] != t.state.get('location'):
                    return self._move(c['location'])
        destinations = [loc for loc,data in t.places.items() if data['objects'].get(name,0) > 0
                        and loc != t.state.get('location') and t.path(loc)]
        if destinations:
            return self._move(min(destinations, key=lambda loc: (len(t.path(loc)),loc)))
        return None

    def _all_needed(self, item, seen=None):
        seen = set() if seen is None else seen
        if item in seen:
            return seen
        seen.add(item)
        for dep in self.table.recipes.get(item,{}).get('ingredients',[]):
            self._all_needed(dep, seen)
        return seen

    def _explore(self, needed):
        t = self.table
        # Inspect publicly present ingredients to discover additional recipe edges.
        for item in sorted(set(t.state.get('ground') or {}) | set(t.state.get('hands') or {})):
            if item not in t.inspected and (item in needed or len(needed) == 1):
                return 'inspect ' + q(item)
        for nxt in t.state.get('neighbors') or []:
            if nxt not in t.places:
                return self._move(nxt)
        return None

    def _station(self, recipe):
        stations = self.table.recipes.get(recipe,{}).get('stations', [])
        if not stations:
            return None  # Unknown requirement: a single real attempt can reveal it.
        current = self.table.state.get('ground') or {}
        if all(s in current for s in stations):
            return None
        for loc, data in sorted(self.table.places.items()):
            if all(s in data['objects'] for s in stations):
                return self._move(loc)
        return self._explore(set(stations))

    def _ensure(self, item, amount, needed, ancestors=()):
        if item in ancestors:
            return None
        t = self.table
        node = self.graph.setdefault(item, {'dependencies': [], 'status': 'pending', 'generation': self.generation})
        node['required_lower_bound'] = amount
        count = t.count(item)
        if count is not None and count >= amount:
            if node['status'] != 'complete':
                self.events.append({'event': 'subgoal_complete', 'node': item, 'count': count})
            node['status'] = 'complete'
            return None
        node['status'] = 'pending'
        if a := self._acquire(item, amount, needed):
            node['action'] = a
            return a
        recipe = t.recipes.get(item, {})
        ingredients = recipe.get('ingredients', [])
        node['dependencies'] = list(ingredients)
        quota = self.quotas.get(item,1)
        if ingredients:
            for dep in ingredients:
                required=(recipe.get('quantities') or {}).get(dep,quota)*max(1,amount-(count or 0))
                if (t.count(dep) or 0) < required:
                    a = self._ensure(dep, required, needed, ancestors + (item,))
                    if a:
                        return a
                    # A known unsatisfied dependency is never bypassed.
                    return self._explore(needed)
            if a := self._station(item):
                return a
            import math
            return f'craft {max(1,math.ceil(amount-(count or 0)))} {q(item)}'
        return self._explore(needed)

    def _fifo(self, item):
        t = self.table
        if not self.queue:
            self.queue = [item]
        # Worklist expansion only, no recursive dependency traversal or search.
        for _ in range(len(self.queue) + 1):
            head = self.queue[0]
            requirement=self.amount if head==item else self.queue_needs.get(head,1)
            if (t.count(head) or 0) >= requirement:
                self.queue.pop(0)
                if not self.queue:
                    return None
                continue
            protect = set(self.queue)
            if a := self._acquire(head, requirement, protect):
                return a
            ingredients = t.recipes.get(head,{}).get('ingredients',[])
            quota = self.quotas.get(head,1)
            requirements={x:(t.recipes.get(head,{}).get('quantities') or {}).get(x,quota) for x in ingredients}
            missing = [x for x in ingredients if (t.count(x) or 0) < requirements[x]]
            if missing:
                self.queue.pop(0)
                for dep in missing:
                    self.queue_needs[dep]=max(self.queue_needs.get(dep,1),requirements[dep])
                    if dep not in self.queue:
                        self.queue.append(dep)
                self.queue.append(head)
                continue
            if ingredients:
                return self._station(head) or f'craft 1 {q(head)}'
            return self._explore(set(self.queue))
        return None

    def choose(self, obs, base_action):
        self.table.observe(obs)
        t = self.table
        p = parse_action(self.target)
        action = None
        if self.follow_public:
            action = self.target
        elif p.verb == 'enter':
            action = self._move(p.target)
        elif p.verb in {'craft','pick up'}:
            if (t.count(p.target) or 0) < self.amount:
                action = self._ensure(p.target, self.amount, self._all_needed(p.target)) if self.mode == 'srp' else self._fifo(p.target)
        elif self.follow_public:
            # Official tutorial action is public, not a hidden task identifier.
            action = self.target
        # Stop repeated transfer cycles only in an unchanged observed resource
        # configuration. Legitimate repeated actions after progress are permitted.
        signature = self._signature()
        if action:
            key = digest([signature, action])
            self.visits[key] = self.visits.get(key,0) + 1
            if self.visits[key] > 2:
                self.events.append({'event':'cycle_yield','action':action,'public_resource_signature':signature})
                action = None
        self.last_choice = {'node': p.target, 'action': action or base_action,
            'structured_action': action, 'graph': self.graph, 'queue': list(self.queue),
            'resource_table': t.to_dict(), 'target': self.target,
            'reason': 'dependency_controller' if action else 'base_fallback'}
        return action or base_action

    def to_dict(self):
        return {k: v.to_dict() if k == 'table' else v for k,v in self.__dict__.items()}

    @classmethod
    def from_dict(cls, data):
        obj = cls(data['mode']); obj.__dict__.update(data)
        obj.table = ResourceTable(**data['table'])
        return obj
