"""Small execution overlay on frozen Stage7 C1, using public observations only.

The FIFO queue, exploration ranking and crafting batch implementation are inherited
from F0. There is no recovery stack, task catalogue, hidden world or quantity oracle.
"""
import copy
import math
import re

from scar.io import digest
from scar_sequence.planner import q
from scar_sequence.public import ResourceTable
from scar_unknown17.facts import PublicFacts
from scar_unknown17_stage7.controller import Stage7Controller, CONFIGS
from scar_v3.state import parse_action

METHODS = ['S0', 'S1', 'S2', 'S3']
SUPPORTED, REJECT, UNKNOWN = 'SUPPORTED', 'REJECT', 'UNKNOWN'


class ResourceController(Stage7Controller):
    MAX_CANDIDATES = 32
    OPPORTUNITY_LIMIT = 6
    STASH_LIMIT = 4

    def __init__(self, opportunistic=False, storage=False):
        super().__init__(**CONFIGS['C1'])
        self.stage10 = True
        self.opportunistic = opportunistic
        self.storage = storage
        self.failures10 = {}
        self.actual_visits = {}
        self.condition_log = []
        self.decision10 = {}
        self.selected_meta = None
        self.stashes = {}
        self.stash_events = []
        self.storage_intent = None
        self.stash_spent = 0
        self.opportunity_spent = 0
        self.loss_locations = {}
        self.explore_depth = 0

    def _all_needed(self, item, seen=None):
        seen, pending = set(seen or ()), [item]
        while pending:
            current = pending.pop()
            if current in seen: continue
            seen.add(current)
            pending.extend(self.table.recipes.get(current, {}).get('ingredients', []))
        return seen

    def ownership(self, item):
        t = self.table
        exact = (t.state.get('hands') is not None and t.state.get('equipment') is not None
                 and all(c.get('counts') is not None for n, c in t.containers.items() if t.carried(n)))
        return {'lower_bound': t.count(item) or 0, 'exact': exact}

    def context(self, action):
        p, t = parse_action(action), self.table
        if p.verb == 'craft':
            recipe = t.recipes.get(p.target, {})
            deps = recipe.get('ingredients', [])
            # Location/time alone cannot release a material failure.
            return {'ingredients': deps, 'materials': {n: self.ownership(n) for n in deps},
                    'stations': {n: (t.state.get('ground') or {}).get(n, 0) for n in recipe.get('stations', [])},
                    'unknown_recipe_carried': None if deps else self.carried_context()}
        if p.verb == 'inspect':
            name = t.inventory if p.target == 'inventory' else p.target
            return {'location': t.state.get('location'), 'access': t.access(name) if name else None,
                    'carried': self.carried_context(), 'ground': t.state.get('ground')}
        return {'location': t.state.get('location'), 'hands': t.state.get('hands'),
                'equipment': t.state.get('equipment'), 'ground': t.state.get('ground'),
                'containers': {n: {k: c.get(k) for k in ['counts', 'load', 'capacity']}
                               for n, c in t.containers.items() if t.access(n)}}

    def carried_context(self):
        t = self.table
        return {'hands': t.state.get('hands'), 'equipment': t.state.get('equipment'),
                'containers': {n: c.get('counts') for n, c in t.containers.items() if t.carried(n)}}

    def retry_allowed(self, action):
        p = parse_action(action)
        old = self.failures10.get(p.verb+':'+p.target)
        if old:
            return old['context'] != self.context(action)
        return super().retry_allowed(action)

    def assess(self, action):
        p, t = parse_action(action or ''), self.table
        s = t.state; h, g = s.get('hands'), s.get('ground'); conditions = []
        def add(kind, status, evidence, **extra):
            conditions.append(dict(kind=kind, status=status, evidence=evidence,
                observed_step=s.get('step'), valid_until='relevant public condition changes', **extra))
        if p.verb == 'invalid': add('syntax', REJECT, 'unparseable action')
        if not self.retry_allowed(action):
            record = self.failures10.get(p.verb+':'+p.target) or self.retry_records.get(p.verb+':'+p.target)
            add('unchanged_failure', REJECT, record)
        if p.verb in {'pick up', 'take out'}:
            add('hands', UNKNOWN if h is None else SUPPORTED if sum(h.values()) < 2 else REJECT, h)
        if p.verb == 'pick up':
            add('ground_presence', UNKNOWN if g is None else SUPPORTED if g.get(p.target, 0) > 0 else REJECT,
                {'target': p.target, 'current_ground': g})
        if p.verb in {'store', 'take out', 'discard'} and p.args:
            name = t.inventory if p.args[-1] == 'inventory' else p.args[-1]
            c = t.containers.get(name, {})
            access = t.access(name) if name else None
            add('container_access', UNKNOWN if access is None else SUPPORTED if access else REJECT,
                {'container': name, 'current_access': access}, container=name)
            if p.verb == 'store':
                available = (h or {}).get(p.target, 0)+(g or {}).get(p.target, 0)
                add('transfer_source', SUPPORTED if available > 0 else UNKNOWN if h is None or g is None else REJECT,
                    {'current_held_and_ground': available})
                load, cap = c.get('load'), c.get('capacity')
                add('container_capacity', REJECT if load is not None and cap is not None and load >= cap else UNKNOWN,
                    {'load': load, 'capacity': cap, 'item_volume': UNKNOWN}, container=name)
                if p.target in t.containers: add('container_nesting', REJECT, 'publicly identified container')
            else:
                counts = c.get('counts')
                # External historical contents require fresh inspection in S3.
                stale = self.storage and not t.carried(name) and c.get('step') != s.get('step')
                add('container_contents', UNKNOWN if counts is None or stale else SUPPORTED if counts.get(p.target, 0) else REJECT,
                    {'last_observed_counts': counts, 'requires_reconfirmation': stale}, container=name)
        if p.verb == 'enter':
            add('route', REJECT if s.get('neighbors') is not None and p.target not in s['neighbors'] else
                REJECT if t.enter_status(p.target) == REJECT else UNKNOWN,
                {'neighbors': s.get('neighbors'), 'guard': t.enter_status(p.target)})
        if p.verb == 'craft':
            recipe = t.recipes.get(p.target, {}); stations = recipe.get('stations')
            add('station', UNKNOWN if not stations or g is None else SUPPORTED if all(g.get(n, 0) for n in stations) else REJECT,
                {'required': stations, 'current_ground': g})
            deps = recipe.get('ingredients', [])
            if not deps: add('recipe', UNKNOWN, 'ingredient names not publicly disclosed')
            for name in deps:
                own = self.ownership(name)
                add('materials', REJECT if own['exact'] and own['lower_bound'] == 0 else UNKNOWN,
                    {'owned': own, 'quantity_rule': UNKNOWN}, item=name, amount=1)
        if self.storage and p.verb in {'drop', 'discard'} and not self.ground_stash_allowed(p.target):
            add('ground_loss_risk', REJECT, {'protected': sorted(n for n in self.protected() if n),
                'reason': 'ground exposure lacks an immediate goal benefit or would risk a scarce/relevant resource'})
        # Do not replace F0's batch or reject an intermediate merely because it
        # already reaches an estimated lower bound. Quantities remain unchanged.
        if not conditions: add('public_trial', UNKNOWN, 'no known negative condition')
        status = REJECT if any(c['status'] == REJECT for c in conditions) else UNKNOWN if any(c['status'] == UNKNOWN for c in conditions) else SUPPORTED
        return {'action': action, 'status': status, 'conditions': conditions}

    def admissible(self, action, avoid_repeat=False):
        if not action or len(self.condition_log) >= self.MAX_CANDIDATES: return False
        value = self.assess(action); self.condition_log.append(value)
        if avoid_repeat and self.actual_visits.get(digest([action, self.context(action)]), 0) >= 2:
            self.decision10.setdefault('cycle_yields', []).append(action)
            return False
        return value['status'] != REJECT

    def _explore(self, needed):
        if self.explore_depth >= 2:
            self.decision10['bounded_exploration_return'] = True
            return None
        self.explore_depth += 1
        try: return super()._explore(needed)
        finally: self.explore_depth -= 1

    def _acquire(self, name, amount, protect, use_container=True):
        if self.storage and (self.table.count(name) or 0) < amount:
            action, meta = self.retrieve(name)
            if action:
                self.decision10.setdefault('candidate_metadata', {})[action] = meta
                return action
        return super()._acquire(name, amount, protect, use_container)

    def protected(self):
        goal = parse_action(self.target).target
        return self._all_needed(goal) | set(self.queue) | set(self.quantity_facts.produced) | {self.last_produced}

    def relevant(self):
        goal = parse_action(self.target).target
        names = self._all_needed(goal) | set(self.queue)
        # A recent public inspection or FIFO forward trial can justify collection
        # before the entire unknown backward dependency chain is disclosed.
        if self.last_produced: names.add(self.last_produced)
        for event in self.attempt_log[-4:]:
            known_material = any(event['target'] in r.get('ingredients', []) for r in self.table.recipes.values())
            if event.get('state') == 'SUCCESS' and (parse_action(event['action']).verb == 'craft' or known_material):
                names.add(event['target'])
        for item in list(names): names.update(self.table.recipes.get(item, {}).get('ingredients', []))
        stations = {n for r in self.table.recipes.values() for n in r.get('stations', [])}
        return names-stations-set(self.table.containers)

    def collection(self, item, all_visible=False):
        t = self.table; h, g = t.state.get('hands') or {}, t.state.get('ground') or {}
        if g.get(item, 0) <= 0: return None
        if t.inventory:
            # Held copies are moved first. A request for the full public supply
            # must include them; it is not clipped to estimated task demand.
            amount = int(h.get(item, 0)+(g[item] if all_visible else 1))
            a = f'store {amount} {q(item)} inventory'
            if self.admissible(a, True): return a
        a = 'pick up '+q(item)
        return a if self.admissible(a, True) else None

    def alternatives(self, blocked):
        t, p = self.table, parse_action(blocked)
        s = t.state; goal = parse_action(self.target).target
        options = []
        if p.verb == 'wait':
            # F0 may exhaust its FIFO because an ambiguous failed trial raised
            # every ingredient quota. Without altering that queue or its batches,
            # permit bounded public acquisition / production for unfinished work.
            blocked_nodes = [r['target'] for r in self.attempt_log[-12:]
                             if parse_action(r['action']).verb == 'craft' and r['state'] == 'BLOCKED_BY_PRECONDITION'
                             and t.recipes.get(r['target'], {}).get('ingredients')]
            fallback_nodes = set(self._all_needed(goal))
            for node in blocked_nodes[-4:]: fallback_nodes.update(self._all_needed(node))
            for node in dict.fromkeys([goal]+self.queue+blocked_nodes[-4:]+sorted(fallback_nodes)):
                if node == goal and self.ownership(node)['lower_bound'] >= self.amount: continue
                if a := self.collection(node, self.opportunistic): options.append(a)
                recipe = t.recipes.get(node, {})
                deps = recipe.get('ingredients', [])
                for item in deps:
                    if a := self.collection(item, self.opportunistic): options.append(a)
                if deps:
                    candidate = 'craft 1 '+q(node)
                    if self.assess(candidate)['status'] != REJECT:
                        options.append(candidate)
                    else:
                        for item in deps:
                            if self.ownership(item)['lower_bound'] > 0: continue
                            for location, data in sorted(t.places.items()):
                                path = t.path(location)
                                if path and data['objects'].get(item, 0): options.append('enter '+q(path[0]))
                        stations = recipe.get('stations', [])
                        for location, data in sorted(t.places.items()):
                            path = t.path(location)
                            if stations and path and all(data['objects'].get(n, 0) for n in stations):
                                options.append('enter '+q(path[0]))
        # A held copy may be safely moved into the equipped inventory, without
        # relinquishing possession, to release a hand for the current operation.
        if sum((s.get('hands') or {}).values()) >= 2 and p.verb in {'pick up', 'take out'}:
            if p.verb == 'pick up' and (a := self.collection(p.target, self.opportunistic)):
                options.append(a)
            for item, amount in sorted((s.get('hands') or {}).items()):
                if item in t.containers:
                    if not t.inventory: options.append('equip '+q(item))
                elif t.inventory: options.append(f'store {int(amount)} {q(item)} inventory')
        if p.verb in {'store', 'take out', 'craft', 'pick up'}:
            for name, c in sorted(t.containers.items()):
                if t.carried(name) and (c.get('counts') is None or c.get('load') is None):
                    options.append('inspect '+q('inventory' if name == t.inventory else name))
        if p.verb == 'craft':
            recipe = t.recipes.get(p.target, {})
            for item in recipe.get('ingredients', []):
                if self.ownership(item)['lower_bound'] > 0: continue
                if a := self.collection(item, self.opportunistic): options.append(a)
                for location, data in sorted(t.places.items()):
                    path = t.path(location)
                    if path and data['objects'].get(item, 0): options.append('enter '+q(path[0]))
            stations = recipe.get('stations', [])
            for location, data in sorted(t.places.items()):
                path = t.path(location)
                if stations and path and all(data['objects'].get(n, 0) for n in stations): options.append('enter '+q(path[0]))
        # Only current public uninspected objects, then an unvisited neighbor.
        for name in sorted(self.visible(), key=lambda n: (n not in self.relevant(), n)):
            if name not in t.inspected: options.append('inspect '+q(name))
        for destination in s.get('neighbors') or []:
            if destination not in t.places: options.append('enter '+q(destination))
        return list(dict.fromkeys(options))[:self.MAX_CANDIDATES]

    def base_progress(self, action):
        p, t = parse_action(action), self.table
        if p.target not in self._all_needed(parse_action(self.target).target): return False
        if p.verb in {'pick up', 'store', 'take out'}:
            if p.verb == 'store' and p.args[-1] != 'inventory': return False
            return self.assess(action)['status'] != REJECT
        if p.verb == 'craft':
            r = t.recipes.get(p.target, {})
            return bool(r.get('ingredients')) and all(self.ownership(n)['lower_bound'] > 0 for n in r['ingredients']) and self.assess(action)['status'] != REJECT
        return False

    def opportunity(self, action):
        if not self.opportunistic: return None, None
        p, t = parse_action(action), self.table
        g, h = t.state.get('ground') or {}, t.state.get('hands') or {}
        if not t.inventory: return None, None
        # Improve an already selected collection at zero extra action cost.
        if p.verb in {'pick up', 'store'} and p.target in self.relevant() and g.get(p.target, 0):
            if p.verb == 'store' and p.args[-1] != 'inventory': return None, None
            candidate = self.collection(p.target, True)
            if candidate and parse_action(candidate).verb == 'store' and candidate != action:
                return candidate, {'kind': 'bulk_collection', 'item': p.target, 'ground': g[p.target],
                    'held_first': h.get(p.target, 0), 'capacity': copy.deepcopy(t.containers.get(t.inventory)),
                    'volume': UNKNOWN, 'basis': 'same relevant collection; capacity clipping is a bounded real trial'}
        if self.opportunity_spent >= self.OPPORTUNITY_LIMIT or p.verb not in {'enter', 'wait'}: return None, None
        for item in sorted(set(g)&self.relevant(), key=lambda n: (n != parse_action(self.target).target, n)):
            if item in t.containers: continue
            c = t.containers.get(t.inventory, {})
            if c.get('load') is None or c.get('capacity') is None:
                inspect = 'inspect inventory'
                if self.admissible(inspect, True): return inspect, {'kind': 'opportunity_capacity_check', 'item': item}
            if c.get('load') is not None and c.get('capacity') is not None and c['load'] >= c['capacity']: continue
            candidate = self.collection(item, True)
            if candidate and parse_action(candidate).verb == 'store':
                return candidate, {'kind': 'opportunistic_collection', 'item': item, 'ground': g[item],
                    'public_relevance': sorted(self.relevant()), 'volume': UNKNOWN,
                    'basis': 'collect visible relevant supply before leaving; bounded by six extra actions'}
        return None, None

    def stash_option(self, blocked):
        if not self.storage or self.stash_spent >= self.STASH_LIMIT: return None, None
        t, p = self.table, parse_action(blocked); h = t.state.get('hands') or {}
        if p.verb not in {'store', 'pick up', 'take out'}: return None, None
        reasons = {c['kind'] for c in self.assess(blocked)['conditions'] if c['status'] == REJECT}
        if not reasons & {'hands', 'container_capacity'}: return None, None
        protected = self.protected() | {p.target}
        containers = [n for n in sorted(t.containers) if not t.carried(n) and t.access(n)]
        for container in containers:
            data = t.containers[container]
            if data.get('load') is None or data.get('step') != t.state.get('step'):
                a = 'inspect '+q(container)
                if self.admissible(a, True): return a, {'kind': 'stash_capacity_check', 'container': container}
            if data.get('load') is not None and data.get('capacity') is not None and data['load'] >= data['capacity']: continue
            for item in sorted(h):
                if item in protected or item in t.containers: continue
                a = f'store {int(h[item])} {q(item)} {q(container)}'
                if self.admissible(a, True):
                    return a, {'kind': 'stash', 'item': item, 'container': container, 'blocked': blocked,
                        'risk': 'external container, future presence must be reconfirmed'}
            if sum(h.values()) < 2 and t.inventory:
                for item in sorted((t.containers.get(t.inventory, {}).get('counts') or {})):
                    if item in protected or item in t.containers: continue
                    a = f'take out {q(item)} inventory'
                    if self.admissible(a, True):
                        return a, {'kind': 'prepare_stash', 'item': item, 'container': container,
                            'location': t.state.get('location'), 'blocked': blocked, 'remaining': 1}
        # Ground is a last resort, only for an inspected surplus with no known
        # recipe role, to acquire a visible final goal immediately. Keep a copy.
        known_inputs = {n for r in t.recipes.values() for n in r.get('ingredients', [])}
        goal = parse_action(self.target).target
        if p.target != goal or not (t.state.get('ground') or {}).get(goal) or containers or t.state.get('location') in self.loss_locations:
            return None, None
        for item in sorted(h):
            if item not in protected | known_inputs and item in t.inspected and self.ownership(item)['lower_bound'] >= 2:
                a = 'drop '+q(item)
                if self.admissible(a, True): return a, {'kind': 'ground_stash', 'item': item,
                    'risk': 'UNKNOWN; duplicate retained, immediate final-goal benefit, no accessible container'}
        return None, None

    def ground_stash_allowed(self, item):
        t = self.table
        goal = parse_action(self.target).target
        inputs = {n for r in t.recipes.values() for n in r.get('ingredients', [])}
        return (item not in self.protected() | inputs and item in t.inspected
                and self.ownership(item)['lower_bound'] >= 2
                and bool((t.state.get('ground') or {}).get(goal))
                and t.state.get('location') not in self.loss_locations
                and not any(t.access(n) and not t.carried(n) for n in t.containers))

    def retrieve(self, item):
        t = self.table
        for record in self.stashes.values():
            if record['item'] != item or record['status'] in {'missing', 'retrieved'}: continue
            path = t.path(record['location'])
            if record['location'] != t.state.get('location'):
                if path: return 'enter '+q(path[0]), {'kind': 'return_to_stash', 'record': copy.deepcopy(record)}
                continue
            container = record['container']
            if container is None:
                if (t.state.get('ground') or {}).get(item, 0):
                    a = self.collection(item, self.opportunistic)
                    if a: return a, {'kind': 'retrieve_stash', 'record': copy.deepcopy(record), 'fresh_evidence': t.state.get('ground')}
            elif t.access(container):
                if record['status'] != 'confirmed' or record['confirmed_step'] != t.state.get('step'):
                    return 'inspect '+q(container), {'kind': 'reconfirm_stash', 'record': copy.deepcopy(record)}
                if (t.containers.get(container, {}).get('counts') or {}).get(item, 0):
                    return f'take out {q(item)} {q(container)}', {'kind': 'retrieve_stash', 'record': copy.deepcopy(record)}
        return None, None

    def choose(self, obs, base_action):
        self.condition_log, self.decision10, self.selected_meta = [], {}, None
        legacy = super().choose(obs, base_action)
        self.refresh_stashes()
        action, reason = legacy, 'retain_F0'
        # A clearly useful public base action wins over unrelated exploration;
        # any craft still passes the identical inherited F0 batching function.
        if self.base_progress(base_action) and (parse_action(legacy).verb in {'inspect', 'enter', 'wait'} or self.assess(legacy)['status'] == REJECT):
            action = self._batch_action(base_action); reason = 'preserve_supported_base_progress'
        if self.storage and self.storage_intent:
            intent = self.storage_intent; self.storage_intent = None
            candidate = f'store 1 {q(intent["item"])} {q(intent["container"])}'
            if intent['location'] == self.table.state.get('location') and (self.table.state.get('hands') or {}).get(intent['item']) and self.admissible(candidate, True):
                action, reason = candidate, 'complete_single_stash_transfer'
                self.selected_meta = dict(intent, kind='stash')
        valid = self.admissible(action)
        if not valid or action == 'wait':
            blocked = action
            stash, meta = self.stash_option(blocked)
            if stash: action, reason, self.selected_meta = stash, meta['kind'], meta
            else:
                choices = ([base_action] if base_action != blocked and base_action != 'wait' else [])+self.alternatives(blocked)
                action = next((a for a in choices if self.admissible(a, True)), 'wait')
                reason = 'public_alternative' if action != 'wait' else 'no_public_candidate'
        if not self.selected_meta:
            candidate, meta = self.opportunity(action)
            if candidate: action, reason, self.selected_meta = candidate, meta['kind'], meta
        if self.selected_meta is None:
            self.selected_meta = self.decision10.get('candidate_metadata', {}).get(action)
        action = self._batch_action(action)
        if self.selected_meta and self.selected_meta['kind'] == 'prepare_stash':
            self.storage_intent = copy.deepcopy(self.selected_meta)
        # Discard a speculative F0 probe when a different action was selected.
        if self.pending_probe and (parse_action(self.pending_probe['action']).verb, parse_action(self.pending_probe['action']).target) != (parse_action(action).verb, parse_action(action).target):
            self.pending_probe = None; self.explore_pending = None
        self.decision10.update(frozen_F0_candidate=legacy, base_action=base_action, selected_action=action,
            reason=reason, override=action != base_action, overlay_changed_F0=action != legacy,
            conditions=copy.deepcopy(self.condition_log), selected_meta=copy.deepcopy(self.selected_meta),
            stash_memory=copy.deepcopy(self.stashes), batch_rule='inherited_F0_unchanged', candidate_limit=self.MAX_CANDIDATES)
        self.last_choice.update(action=action, reason=reason, stage10=copy.deepcopy(self.decision10))
        return action

    def refresh_stashes(self):
        if not self.storage: return
        t, s = self.table, self.table.state
        for record in self.stashes.values():
            if record['status'] == 'retrieved': continue
            if record['location'] != s.get('location'):
                if record['status'] != 'missing': record['status'] = 'historical'
                continue
            container = record['container']
            if container is None and s.get('ground') is not None:
                quantity = s['ground'].get(record['item'], 0)
            elif container is not None and t.access(container) and t.containers.get(container, {}).get('step') == s.get('step'):
                counts = t.containers[container].get('counts')
                if counts is None: continue
                quantity = counts.get(record['item'], 0)
            elif container is not None and t.access(container) is False:
                quantity = 0
            else: continue
            previous = record['status']
            record.update(status='confirmed' if quantity > 0 else 'missing', last_confirmed_quantity=quantity, confirmed_step=s.get('step'))
            if previous != 'missing' and not quantity:
                self.stash_events.append({'event': 'stash_missing_on_reconfirmation', 'record': copy.deepcopy(record)})

    def observe(self, before, action, after):
        self.table.observe(before)
        context = self.context(action); p = parse_action(action); old = copy.deepcopy(self.table.state)
        meta = copy.deepcopy(self.selected_meta)
        super().observe(before, action, after)
        feedback = self.table.state['feedback']
        key = p.verb+':'+p.target
        rejected = bool(re.search(r'Cannot |Invalid ', feedback))
        if rejected:
            self.failures10[key] = {'action': action, 'context': self.context(action), 'feedback': feedback, 'step': after.get('step')}
        else: self.failures10.pop(key, None)
        visit = digest([action, context]); self.actual_visits[visit] = self.actual_visits.get(visit, 0)+1
        if meta and meta['kind'] in {'opportunistic_collection', 'opportunity_capacity_check'}: self.opportunity_spent += 1
        if meta and meta['kind'] in {'stash', 'ground_stash', 'prepare_stash'}: self.stash_spent += 1
        if self.storage:
            container, amount = None, 0
            if p.verb == 'store' and p.args[-1] != 'inventory' and not self.table.carried(p.args[-1]):
                m = re.search(r'I stored ([\d.]+) ', feedback)
                if m: container, amount = p.args[-1], float(m[1])
            elif p.verb == 'drop' and 'I dropped ' in feedback: amount = 1
            elif p.verb == 'discard':
                m = re.search(r'I discarded ([\d.]+) ', feedback)
                if m: amount = float(m[1])
            if amount:
                ident = digest([p.target, old.get('location'), container])[:16]
                record = {'item': p.target, 'quantity': amount, 'location': old.get('location'), 'container': container,
                    'stored_step': after.get('step'), 'confirmed_step': after.get('step'), 'status': 'confirmed',
                    'last_confirmed_quantity': amount, 'evidence': feedback, 'risk': 'future presence UNKNOWN'}
                self.stashes[ident] = record
                self.stash_events.append({'event': 'stash_recorded', 'record': copy.deepcopy(record), 'controller_selected': bool(meta)})
                if container in self.table.containers:
                    # Store success certifies the moved amount, not all old contents.
                    self.table.containers[container]['step'] = after.get('step')
            if meta and meta['kind'] == 'retrieve_stash' and not rejected:
                self.stash_events.append({'event': 'stash_retrieved', 'action': action, 'feedback': feedback, 'record': meta['record']})
                rec = meta['record']
                ident = digest([rec['item'], rec['location'], rec['container']])[:16]
                if ident in self.stashes:
                    remaining = max(0, rec['last_confirmed_quantity']-1)
                    self.stashes[ident].update(last_confirmed_quantity=remaining,
                        status='retrieved' if remaining == 0 else 'historical')
            new = self.table.state
            if old.get('location') == new.get('location') and p.verb not in {'store', 'pick up', 'craft', 'discard', 'drop', 'take out'}:
                lost = {n: v-(new.get('ground') or {}).get(n, 0) for n, v in (old.get('ground') or {}).items() if v > (new.get('ground') or {}).get(n, 0)}
                if lost: self.loss_locations[new.get('location')] = {'observed_step': after.get('step'), 'public_ground_loss': lost}
            self.refresh_stashes()
        self.selected_meta = None

    @classmethod
    def from_dict(cls, data):
        obj = cls(data.get('opportunistic', False), data.get('storage', False))
        obj.__dict__.update(copy.deepcopy(data))
        obj.table = ResourceTable(**data['table']); obj.quantity_facts = PublicFacts.from_dict(data['quantity_facts'])
        return obj


def make_controller(method):
    if method == 'S0': return Stage7Controller(**CONFIGS['C1'])
    if method not in METHODS: raise ValueError(method)
    return ResourceController(method in {'S2', 'S3'}, method == 'S3')


def restore_controller(data):
    return ResourceController.from_dict(data) if data.get('stage10') else Stage7Controller.from_dict(data)


def adapted(data, method):
    """Historical zero-API probe: copy only frozen F0 public state fields."""
    ctrl = make_controller(method)
    keys = Stage7Controller(**CONFIGS['C1']).__dict__
    base = {k: copy.deepcopy(v) for k, v in data.items() if k in keys}
    base['flags'] = dict(CONFIGS['C1'])
    merged = ctrl.to_dict() | base
    if method == 'S0': return Stage7Controller.from_dict(merged)
    return ResourceController.from_dict(merged)
