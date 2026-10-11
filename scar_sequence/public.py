"""Public evidence only. No environment, evaluator, recipe catalogue or snapshots.

Counts are observations, not hallucinated completions of missing fields. Historical
ground contents are remembered locations, not currently accessible inventory.
"""
from collections import Counter, deque
from dataclasses import dataclass, field, asdict
import re
from scar_v3.state import PublicState, parse_action, parse_counts
from scar.io import digest


def room(location):
    return location.rsplit(', ', 1)[-1] if location else None


@dataclass
class ResourceTable:
    state: dict = field(default_factory=dict)
    places: dict = field(default_factory=dict)
    links: dict = field(default_factory=dict)
    containers: dict = field(default_factory=dict)
    inventory: str | None = None
    recipes: dict = field(default_factory=dict)
    inspected: list = field(default_factory=list)
    guards: dict = field(default_factory=dict)
    observations: int = 0
    events: list = field(default_factory=list)
    pending_craft: dict | None = None

    def observe(self, obs, action=None):
        old = self.state
        s = PublicState.observe(obs)
        self.observations += 1
        self.state = {'location': room(s.location), 'location_full': s.location,
                      'hands': s.hands, 'equipment': s.equipment, 'ground': s.ground,
                      'neighbors': s.neighbors, 'step': s.step, 'feedback': s.feedback,
                      'public_goal': s.goal}
        loc = self.state['location']
        if loc and s.ground is not None:
            self.places[loc] = {'objects': s.ground, 'step': s.step,
                                'source': 'public_ground_observation'}
        if loc and s.neighbors is not None:
            self.links[loc] = s.neighbors
        p = parse_action(action or '')
        feedback = s.feedback
        for name, ingredients in re.findall(r'([\w-]+) \(made of ([^)]+)\)', feedback):
            self.recipes.setdefault(name, {'quantities': None}).update(
                {'ingredients': [x.strip() for x in ingredients.split(',')], 'step': s.step,
                 'source': 'public_inspection'})
        equipped = re.search(r'I equipped (\S+) as inventory', feedback)
        if equipped:
            self.inventory = equipped[1].rstrip('.')
        if self.inventory and s.equipment is not None and self.inventory not in s.equipment:
            self.inventory = None
        if p.verb == 'inspect':
            m = re.search(r'It contains: (.*?) \(capacity: ([\d.]+)/([\d.]+)\)', feedback)
            if m and (counts := parse_counts(m[1])) is not None:
                name = self.inventory if p.target == 'inventory' else p.target
                if name:
                    self.containers[name] = {'counts': counts, 'load': float(m[2]),
                         'capacity': float(m[3]), 'location': loc, 'step': s.step,
                         'source': 'public_container_inspection'}
            if 'I inspected ' in feedback and p.target not in self.inspected:
                self.inspected.append(p.target)
        # Update only from explicit success and actual reported transfer amount.
        if p.verb == 'store':
            m = re.search(r'I stored ([\d.]+) (\S+) in (?:my )?([^\n.]+)', feedback)
            if m:
                name = self.inventory if p.args[-1] == 'inventory' else p.args[-1]
                c = self.containers.get(name)
                if c and c['counts'] is not None:
                    c['counts'][m[2]] = c['counts'].get(m[2], 0) + float(m[1])
                    c['load'] = None
        if p.verb in {'take out', 'discard'} and ('I took out ' in feedback or 'I discarded ' in feedback):
            name = self.inventory if p.args[-1] == 'inventory' else p.args[-1]
            c = self.containers.get(name)
            if c:
                c['counts'] = None  # Inspect before making another negative claim.
                c['load'] = None
        if p.verb == 'craft' and 'successfully crafted' in feedback:
            amount_match = re.search(r'successfully crafted (\d+)', feedback)
            before_counts = Counter(old.get('hands') or {}) + Counter(old.get('equipment') or {})
            complete = True
            for name,c in self.containers.items():
                if name in (old.get('hands') or {}) or name in (old.get('equipment') or {}):
                    if c['counts'] is None:
                        complete = False
                    else:
                        before_counts.update(c['counts'])
            self.pending_craft = {'target':p.target,'amount':int(amount_match[1]),
                'before':dict(before_counts),'source_step':s.step} if complete and amount_match else None
            for name, c in self.containers.items():
                if self.carried(name):
                    c['counts'], c['load'] = None, None
        if p.verb == 'inspect' and self.pending_craft:
            current = Counter(s.hands or {}) + Counter(s.equipment or {})
            complete = True
            for name,c in self.containers.items():
                if self.carried(name):
                    if c['counts'] is None: complete = False
                    else: current.update(c['counts'])
            if complete:
                pending = self.pending_craft
                consumed = {k:(v-current.get(k,0))/pending['amount'] for k,v in pending['before'].items() if v>current.get(k,0)}
                if consumed:
                    rec=self.recipes.setdefault(pending['target'], {'ingredients':sorted(consumed)})
                    rec['quantities']=consumed
                    rec['quantity_source']={'kind':'observed_successful_consumption','step':pending['source_step']}
                self.pending_craft=None
        elif p.verb not in {'inspect','craft','invalid'}:
            self.pending_craft=None
        if p.verb in {'buy', 'sell', 'eat', 'disassemble'}:
            for name, c in self.containers.items():
                if self.carried(name):
                    c['counts'], c['load'] = None, None
        for name, c in self.containers.items():
            if self.carried(name) or (s.ground is not None and name in s.ground):
                c['location'] = loc
        # Guard belongs to directed observed edge, not every enter action.
        if p.verb == 'enter' and old.get('location'):
            key = old['location'] + '->' + p.target
            if 'door is locked' in feedback:
                self.guards[key] = {'locked': True, 'required': 'key_in_hand',
                    'expires_on': 'successful_enter_or_explicit_unlock',
                    'source': feedback, 'step': s.step}
            elif loc != old['location'] and re.search(r'I (?:entered|used a key to unlock)', feedback):
                self.guards[key] = {'locked': False, 'required': None,
                    'expires_on': 'explicit_locked_failure', 'source': feedback, 'step': s.step}
        m = re.search(r'Cannot craft (\S+)\. Missing necessary (.+?) in the current area', feedback)
        if m:
            self.recipes.setdefault(m[1], {'ingredients': [], 'quantities': None})['stations'] = m[2].split(', ')
        return self

    def carried(self, name):
        return name in (self.state.get('hands') or {}) or name in (self.state.get('equipment') or {})

    def access(self, name, for_crafting=False):
        if self.carried(name):
            return True
        if for_crafting:
            return False if self.state.get('hands') is not None and self.state.get('equipment') is not None else None
        if self.state.get('ground') is None:
            return None
        return name in self.state['ground']

    def count(self, name):
        h, e = self.state.get('hands'), self.state.get('equipment')
        if h is None or e is None:
            return None
        total = h.get(name, 0) + e.get(name, 0)
        unknown = False
        for container, c in self.containers.items():
            if self.carried(container):
                if c['counts'] is None:
                    unknown = True
                else:
                    total += c['counts'].get(name, 0)
        # Positive count is a certified lower bound when other contents unknown.
        return total if total > 0 or not unknown else None

    def enter_status(self, destination):
        g = self.guards.get(self.state.get('location', '') + '->' + destination)
        if g is None:
            return 'UNKNOWN'
        if not g['locked']:
            return 'UNLOCKED'
        h = self.state.get('hands')
        return 'UNKNOWN' if h is None else 'SUPPORTED' if h.get('key', 0) else 'REJECT'

    def path(self, destination):
        start = self.state.get('location')
        queue = deque([(start, [])]); seen = {start}
        while queue:
            node, route = queue.popleft()
            if node == destination:
                return route
            for nxt in self.links.get(node, []):
                if nxt not in seen:
                    seen.add(nxt); queue.append((nxt, route + [nxt]))
        return None

    def signature(self):
        return digest({k: self.state.get(k) for k in ['location', 'hands', 'equipment', 'ground']} | {
            'containers': self.containers, 'recipes': self.recipes})

    def to_dict(self):
        return asdict(self)
