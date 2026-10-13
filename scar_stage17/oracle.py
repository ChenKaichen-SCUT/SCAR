"""Dataset-builder-only feasibility witness. NEVER imported by online agents.

Uses hidden recipes and locations solely to test a candidate before freezing.
It never edits a world. Witness success is not an evaluated baseline score.
Unverified candidates are labeled unverified, not proven impossible.
"""
import copy
from collections import deque
import math
import shlex
from scar.environment import AGENT_ID, state_digest
from scar_v3.hard import owned, base_id
from scar.agents.scar.state import feedback_text


class Unverified(RuntimeError):
    pass


class Witness:
    def __init__(self, env, limit=85):
        self.env = env
        self.limit = limit
        self.trace = []

    @property
    def agent(self):
        return self.env.agents[0]

    @property
    def area(self):
        return self.env.world.area_instances[self.env.curr_agents_state['area'][AGENT_ID]]

    def name(self, oid):
        w = self.env.world
        return next((name for name, value in w.auxiliary['obj_name_to_id'].items() if value == oid), w.objects[base_id(self.env, oid)].name)

    def act(self, action):
        if len(self.trace) >= self.limit:
            raise Unverified('witness exceeds conservative 85-action construction limit')
        before = copy.deepcopy(self.env.obs[AGENT_ID])
        obs, reward, done, info = self.env.step({AGENT_ID: action})
        self.env.update_scores(reward)
        after = copy.deepcopy(obs[AGENT_ID]); fb = feedback_text(after['text'])
        self.trace.append({'before': before, 'action': action, 'after': after, 'state_hash': state_digest(self.env),
                           'done': bool(done), 'health': self.agent.hp})
        if done or getattr(reward[AGENT_ID],'death',0) or self.agent.hp <= 0:
            raise Unverified('witness died or reached terminal environment state')
        if 'Cannot ' in fb or 'Invalid ' in fb or 'blocked the way out' in fb:
            raise Unverified('witness action rejected: '+action+' / '+fb[:180])
        return fb

    def path(self, destination):
        queue=deque([(self.area.id, [])]); seen={self.area.id}
        while queue:
            node, path=queue.popleft()
            if node == destination:return path
            for neighbor, edge in self.env.world.area_instances[node].neighbors.items():
                if neighbor not in seen and (not edge.locked or owned(self.env, edge.object_to_unlock or 'obj_key') > 0):
                    seen.add(neighbor);queue.append((neighbor,path+[neighbor]))
        return None

    def move(self, destination):
        path = self.path(destination)
        if path is None:raise Unverified('no traversable known-to-builder route')
        for aid in path:
            edge=self.area.neighbors[aid]
            if edge.locked:
                key=edge.object_to_unlock or 'obj_key'
                if key not in self.agent.items_in_hands:
                    self.free_hand();self.act('take out '+shlex.quote(self.name(key))+' inventory')
            self.act('enter '+shlex.quote(self.env.world.area_instances[aid].name))

    def free_hand(self):
        if sum(self.agent.items_in_hands.values()) < 2:return
        name=next(iter(self.agent.items_in_hands)); count=self.agent.items_in_hands[name]
        if self.agent.inventory.container and name not in self.env.world.container_instances:
            self.act(f'store {int(math.ceil(count))} {shlex.quote(self.name(name))} inventory')
        else:self.act('drop '+shlex.quote(self.name(name)))

    def equip_bag(self):
        if self.agent.inventory.container:return
        options=[]
        for area in self.env.world.area_instances.values():
            path=self.path(area.id)
            if path is None:continue
            for oid in area.objects:
                if oid in self.env.world.container_instances:
                    options.append((len(path), area.id, oid))
        if not options:raise Unverified('no reachable natural container')
        _, area, oid=min(options)
        self.move(area);self.free_hand();self.act('pick up '+shlex.quote(self.name(oid)));self.act('equip '+shlex.quote(self.name(oid)))

    def ensure(self, oid, amount, stack=()):
        if owned(self.env,oid) >= amount:return
        if oid in stack:raise Unverified('cyclic recipe or station prerequisite')
        for _ in range(10):
            shortage=amount-owned(self.env,oid)
            if shortage <= 0:return
            sources=[]
            for area in self.env.world.area_instances.values():
                path=self.path(area.id)
                if path is None:continue
                for instance, count in area.objects.items():
                    if base_id(self.env,instance)==oid and count>0:sources.append((len(path),area.id,instance,count))
            if sources:
                _, area, instance, count=min(sources)
                self.move(area)
                quantity=min(math.ceil(shortage),math.ceil(count))
                if self.agent.inventory.container:
                    self.act(f'store {quantity} {shlex.quote(self.name(instance))} inventory')
                else:
                    self.free_hand();self.act('pick up '+shlex.quote(self.name(instance)))
                continue
            recipe=self.env.world.objects[oid]
            if not recipe.craft_ingredients:raise Unverified('no natural resource source found: '+recipe.name)
            batch=max(1,min(4,math.ceil(shortage)))
            self.stations(recipe.craft_dependencies, stack+(oid,))
            for child, quantity in recipe.craft_ingredients.items():
                self.ensure(child, quantity*batch, stack+(oid,))
            self.stations(recipe.craft_dependencies, stack+(oid,))
            previous=owned(self.env,oid)
            self.act(f'craft {batch} {shlex.quote(recipe.name)}')
            if not any(base_id(self.env,i)==oid and count>0 for i,count in self.area.objects.items()):
                raise Unverified('craft produced no accessible witness product')
        raise Unverified('witness failed to make bounded material progress')

    def stations(self, dependencies, stack):
        if not dependencies:return
        places=[]
        for area in self.env.world.area_instances.values():
            path=self.path(area.id)
            if path is not None and all(area.objects.get(d,0)>0 for d in dependencies):places.append((len(path),area.id))
        if places:self.move(min(places)[1]);return
        # First use a real area containing the largest subset; construct missing
        # stations via their own unchanged recipes and place them there.
        candidates=[(-sum(area.objects.get(d,0)>0 for d in dependencies),len(self.path(area.id)),area.id)
                    for area in self.env.world.area_instances.values() if self.path(area.id) is not None]
        destination=min(candidates)[2]
        for dep in dependencies:
            if self.env.world.area_instances[destination].objects.get(dep,0)>0:continue
            recipe=self.env.world.objects[dep]
            if not recipe.craft_ingredients:raise Unverified('missing uncraftable natural station')
            if dep in stack:raise Unverified('cyclic station prerequisites')
            self.stations(recipe.craft_dependencies,stack+(dep,))
            for child,quantity in recipe.craft_ingredients.items():self.ensure(child,quantity,stack+(dep,))
            self.stations(recipe.craft_dependencies,stack+(dep,))
            self.act('craft 1 '+shlex.quote(recipe.name))
            if self.area.objects.get(dep,0)<=0:raise Unverified('station construction failed')
            destination=self.area.id  # Native stations stay where crafted; never transfer them.
        self.move(destination)

    def solve(self, target, amount=1):
        self.equip_bag();self.ensure(target,amount)
        if owned(self.env,target)<amount:raise Unverified('final possession not reached')
        return self.trace
