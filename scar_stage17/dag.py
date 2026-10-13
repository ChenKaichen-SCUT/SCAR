"""Independent deterministic public-evidence DAG replanner; no S1/P3 imports."""
import copy
import json
import math
import re
import shlex
from collections import deque,Counter
from pathlib import Path
from scar_stage16.knowledge import PublicTable
from scar.io import digest,atomic_json
from scar_v3.state import parse_action

q=shlex.quote

class DAGPlanner:
    def __init__(self,id,name,cfg):
        super().__init__(id,name);self.cfg=cfg;cfg.available_actions=self.available_actions;cfg.__post_init__()
        self.table=PublicTable();self.target='';self.objective='';self.visits=Counter();self.trials=Counter()
        self.rejected={};self.last={};self.decision={};self.step=0

    def initialize(self,history,target,objective):
        self.target=target;self.objective=objective
        for h in history:
            self.table.observe(h['before']);self.table.observe(h['after'],h['action'])
        self.visits.clear()

    def signature(self):
        t=self.table
        return digest([t.state.get('location'),t.state.get('hands'),t.state.get('ground'),
            {n:c.get('counts') for n,c in t.containers.items()},
            {n:[r.get('quantities'),r.get('stations')] for n,r in t.recipes.items()}])

    def permitted(self,action):return self.rejected.get(action)!=self.signature()

    def route(self,dest):
        t=self.table;start=t.state.get('location');queue=deque([(start,[])]);seen={start}
        while queue:
            node,path=queue.popleft()
            if node==dest:return path
            for neighbor in sorted(t.links.get(node,[])):
                guard=t.guards.get(node+'->'+neighbor,{})
                if neighbor not in seen and (not guard.get('locked') or any('key' in n and v>0 for n,v in (t.state.get('hands') or {}).items())):
                    seen.add(neighbor);queue.append((neighbor,path+[neighbor]))
        return None

    def move_to(self,predicate):
        options=[]
        for place,info in self.table.places.items():
            path=self.route(place)
            if path and predicate(info.get('objects',{})):options.append((len(path),place,path[0]))
        return 'enter '+q(min(options)[2]) if options else None

    def free_hand(self):
        t=self.table;hands=t.state.get('hands') or {}
        if sum(hands.values())<2:return None
        for name in sorted(hands,key=lambda n:(n==self.target,n)):
            if t.inventory and name not in t.containers:
                action=f'store {math.ceil(hands[name])} {q(name)} inventory'
                if self.permitted(action):return action
            action='drop '+q(name)
            if self.permitted(action):return action
        return None

    def collect(self,item,amount):
        t=self.table;ground=t.state.get('ground') or {}
        if ground.get(item,0)>0:
            quantity=min(math.ceil(amount),math.ceil(ground[item]))
            if t.inventory:
                action=f'store {quantity} {q(item)} inventory'
                if self.permitted(action):return action
            return self.free_hand() or 'pick up '+q(item)
        for name,c in sorted(t.containers.items()):
            if not t.carried(name) and t.access(name) and (c.get('counts') or {}).get(item,0)>0:
                return self.free_hand() or f'take out {q(item)} {q(name)}'
        return self.move_to(lambda objects:objects.get(item,0)>0)

    def need(self,item,amount,stack=()):
        t=self.table
        if item in stack or len(stack)>20:return None
        have=t.count(item) or 0
        if have>=amount:return None
        action=self.collect(item,amount-have)
        if action and self.permitted(action):return action
        recipe=t.recipes.get(item,{})
        quantities=recipe.get('quantities')
        self.decision.setdefault('subgoals',[]).append({'item':item,'amount':amount,'held_lower_bound':have,'recipe':copy.deepcopy(recipe)})
        if quantities:
            batch=min(4,max(1,math.ceil(amount-have)))
            # Topological recursion recalculates resource demands after every action.
            for child,weight in sorted(quantities.items()):
                if (t.count(child) or 0)<weight*batch:
                    action=self.need(child,weight*batch,stack+(item,))
                    if action and self.permitted(action):return action
            if any((t.count(c) or 0)<v*batch for c,v in quantities.items()):return None
            stations=recipe.get('stations',[])
            ground=t.state.get('ground') or {}
            if stations and not all(ground.get(s,0)>0 for s in stations):
                action=self.move_to(lambda objects:all(objects.get(s,0)>0 for s in stations))
                if action and self.permitted(action):return action
                for station in stations:
                    if ground.get(station,0)>0:continue
                    if (t.count(station) or 0)>0:
                        if (t.state.get('hands') or {}).get(station,0):return 'drop '+q(station)
                        return self.free_hand() or f'take out {q(station)} inventory'
                    action=self.need(station,1,stack+(item,))
                    if action and self.permitted(action):return action
                return None
            action=f'craft {batch} {q(item)}'
            if self.permitted(action):return action
        else:
            # An ingredient-name relation is useful even before weights are
            # disclosed: acquire one sample of a missing ingredient to trigger
            # native acquisition information, without asserting its recipe weight.
            for child in sorted(recipe.get('ingredients') or []):
                if (t.count(child) or 0)==0:
                    action=self.collect(child,1) or self.need(child,1,stack+(item,))
                    if action and self.permitted(action):return action
            visible=(t.state.get('ground') or {}) | (t.state.get('hands') or {})
            if item in visible and item not in t.inspected:return 'inspect '+q(item)
            action='craft 1 '+q(item)
            if self.trials[item]<4 and self.permitted(action):return action
        return None

    def explore(self):
        t=self.table;ground=t.state.get('ground') or {};hands=t.state.get('hands') or {}
        # Only publicly recognized containers can be equipped.
        if not t.inventory:
            for name in sorted(t.containers):
                if name in hands:return 'equip '+q(name)
                if name in ground:return self.free_hand() or 'pick up '+q(name)
        for name in sorted(ground | hands):
            action='inspect '+q(name)
            if name not in t.inspected and self.permitted(action):return action
        choices=[]
        for neighbor in sorted(t.state.get('neighbors') or []):
            action='enter '+q(neighbor)
            if self.permitted(action) and t.enter_status(neighbor)!='REJECT':choices.append((self.visits[neighbor],neighbor))
        if choices:return 'enter '+q(min(choices)[1])
        # Revisit reachable least-visited frontiers when current exits were blocked.
        for location in sorted(t.links,key=lambda n:(self.visits[n],n)):
            path=self.route(location)
            if path and self.permitted('enter '+q(path[0])):return 'enter '+q(path[0])
        return 'wait'

    def _act(self,obs):
        self.table.observe(obs);self.decision={'step':self.step+1,'target':self.target,'subgoals':[]}
        t=self.table;self.visits[t.state.get('location')]+=1
        # Refresh unknown carried counts before treating missing quantities as zero.
        action=None
        for name,c in sorted(t.containers.items()):
            if t.carried(name) and c.get('counts') is None:
                action='inspect '+q('inventory' if name==t.inventory else name);break
        if not action and not t.inventory:
            for name in sorted(t.containers):
                if name in (t.state.get('hands') or {}):action='equip '+q(name);break
                if name in (t.state.get('ground') or {}):action=self.free_hand() or 'pick up '+q(name);break
        if not action:action=self.need(self.target,1)
        if not action or not self.permitted(action):action=self.explore();self.decision['fallback']='bounded_public_inspection_and_exploration'
        p=parse_action(action)
        if p.verb=='craft' and not t.recipes.get(p.target,{}).get('quantities'):self.trials[p.target]+=1
        self.last={'signature':self.signature(),'action':action};self.decision['selected']=action
        return action,0,0,json.dumps({'action':action,'reasoning':'deterministic public DAG'})

    def observe_transition(self,before,action,after):
        self.table.observe(after,action);self.step+=1
        fb=self.table.state['feedback']
        if re.search(r'Cannot |Invalid |blocked the way out|do not have|not enough|not found',fb,re.I):
            self.rejected[action]=self.signature()

    def export(self):
        return dict(table=self.table.to_dict(),target=self.target,objective=self.objective,visits=dict(self.visits),
            trials=dict(self.trials),rejected=self.rejected,last=self.last,decision=self.decision,step=self.step)

    def save_memory(self,directory):atomic_json(Path(directory)/'dag.json',self.export())
    def load_memory(self,directory):
        state=json.loads((Path(directory)/'dag.json').read_text());self.__dict__.update(state)
        self.table=PublicTable(**state['table']);self.visits=Counter(state['visits']);self.trials=Counter(state['trials'])
