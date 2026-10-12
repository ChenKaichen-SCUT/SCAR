"""Independent FIFO interventions, exclusively from observed public evidence.

No game IDs, test IDs, world access, witness files or per-item exceptions.
"""
import math
import re
from scar.io import digest
from scar_sequence.planner import Controller, q
from scar_sequence.public import ResourceTable
from scar_unknown17.facts import PublicFacts, carried_counts
from scar_v3.state import parse_action


class SimpleController(Controller):
    EXPLORATION_LIMIT=18
    TRIAL_LIMIT=4

    def __init__(self,directed=False,batch='none'):
        super().__init__('fifo');self.directed=directed;self.batch=batch
        self.exploration_spent=0;self.probes={};self.trials={};self.explore_pending=None
        self.last_produced=None;self.quantity_facts=PublicFacts();self.batch_decisions=[]
        self.mechanism_decision={};self.in_episode=False

    def set_goal(self,action,public_goal,follow_public=False):
        super().set_goal(action,public_goal,follow_public)
        self.quantity_facts.set_goal(action,public_goal);self.in_episode=True

    def observe(self,before,action,after):
        old=set(self.table.recipes);super().observe(before,action,after)
        self.quantity_facts.observe(before,action,after)
        p=parse_action(action);feedback=self.table.state['feedback']
        if 'successfully crafted' in feedback:self.last_produced=p.target
        if self.explore_pending:
            self.events.append({'event':'directed_probe_result','action':action,
                'new_recipes':sorted(set(self.table.recipes)-old),'feedback':feedback,
                'selection':self.explore_pending})
            self.explore_pending=None

    def _probe(self,action,reason,source):
        self.exploration_spent+=1
        self.explore_pending={'reason':reason,'source':source,'spent':self.exploration_spent,
                              'limit':self.EXPLORATION_LIMIT}
        self.mechanism_decision['exploration']=self.explore_pending
        return action

    def _explore(self,needed):
        if not self.directed:return super()._explore(needed)
        if self.exploration_spent>=self.EXPLORATION_LIMIT:return None
        t=self.table;s=t.state;goal=parse_action(self.target).target
        missing=[x for x in needed if not t.recipes.get(x,{}).get('ingredients')]
        visible=set(s.get('ground') or {})|set(s.get('hands') or {})|set(s.get('equipment') or {})
        for c,data in t.containers.items():
            if t.carried(c):visible.update(data['counts'] or {})
        # A produced intermediate may disclose a previously unknown downstream link.
        station_names={x for r in t.recipes.values() for x in r.get('stations',[])}
        ranked=sorted(visible,key=lambda x:(x!=self.last_produced,x not in needed,x in station_names,x in t.containers,x))
        for item in ranked:
            if item not in t.inspected and item not in self.probes:
                self.probes[item]={'step':s.get('step'),'location':s.get('location')}
                return self._probe('inspect '+q(item),'unknown recipe/material link',{'public_entity':item,'missing_nodes':missing})
        # Follow only already observed material->product links. A fixed forward
        # trial may expose the next link when no backward recipe is public yet.
        products=[]
        supplies=set(visible)
        for data in t.places.values():supplies.update(data['objects'])
        for product,r in t.recipes.items():
            deps=r.get('ingredients',[])
            if not deps or product==goal or self.trials.get(product,0)>=1:continue
            if not all(x in supplies or (t.count(x) or 0)>0 for x in deps):continue
            if (t.count(product) or 0)>0 or any(data['objects'].get(product,0)>0 for data in t.places.values()):continue
            overlap=len(set(product.split('_'))&set(goal.split('_')))
            products.append((product not in needed,-overlap,len(deps),product))
        if sum(self.trials.values())<self.TRIAL_LIMIT and products:
            product=min(products)[-1];r=t.recipes[product]
            for dep in r['ingredients']:
                if (t.count(dep) or 0)<1:
                    if a:=self._acquire(dep,1,set(needed)|set(r['ingredients'])):
                        return self._probe(a,'acquire publicly named trial ingredient',{'product':product,'ingredient':dep})
                    return None
            if a:=self._station(product):
                return self._probe(a,'reach publicly disclosed required station',{'product':product})
            self.trials[product]=self.trials.get(product,0)+1
            return self._probe('craft 1 '+q(product),'bounded forward recipe trial',{'recipe':product,'observed':r})
        # Visit previously observed areas for public entities not yet inspected.
        destinations=[]
        for loc,data in t.places.items():
            if loc!=s.get('location') and t.path(loc) and any(x not in t.inspected and x not in self.probes for x in data['objects']):
                destinations.append(loc)
        for loc in s.get('neighbors') or []:
            if loc not in t.places:destinations.append(loc)
        if destinations:
            loc=min(destinations,key=lambda x:(len(t.path(x) or [x]),x))
            if a:=self._move(loc):return self._probe(a,'visit public material frontier',{'location':loc,'missing_nodes':missing})
        return None

    def _batch_action(self,action):
        p=parse_action(action)
        if p.verb!='craft' or self.batch=='none':return action
        t=self.table;goal=parse_action(self.target).target
        need=self.amount if p.target==goal else self.queue_needs.get(p.target,1)
        deficit=max(1,math.ceil(need-(t.count(p.target) or 0)))
        # Fixed comparator: fulfill an observed deficit, otherwise request two
        # intermediate copies. This is intentionally not a hidden perfect quota.
        amount=min(4,max(deficit,2 if p.target!=goal else 1))
        mode='fixed_deficit_or_two';prediction=None;sample=None
        if self.batch=='learned':
            candidates=[x for x in self.quantity_facts.effects if x['target']==p.target]
            counts=carried_counts(self.quantity_facts.table)
            # Only exact public inventory matches support an empirical replay.
            supported=[x for x in candidates if x['before_counts']==counts and x['actual']>=deficit]
            if supported:
                sample=min(supported,key=lambda x:(sum(x['consumed'].values())/max(1,x['actual']),x['requested']))
                amount=min(4,sample['requested']);prediction=sample['consumed'];mode='exact_public_context_sample'
        self.mechanism_decision['batch']={'original_action':action,'target':p.target,'requested':amount,
            'observed_deficit_lower_bound':deficit,'rule':mode,'predicted_consumption':prediction,
            'source_sample_step':sample['source_step'] if sample else None,
            'uncertainty':'UNKNOWN when no matching observed context; quantity samples not universal recipes'}
        return f'craft {amount} {q(p.target)}'

    def choose(self,obs,base_action):
        self.mechanism_decision={}
        action=super().choose(obs,base_action)
        action=self._batch_action(action)
        self.last_choice['action']=action
        self.last_choice['mechanisms']=self.mechanism_decision
        return action

    def to_dict(self):
        return {k:v.to_dict() if k in {'table','quantity_facts'} else v for k,v in self.__dict__.items()}

    @classmethod
    def from_dict(cls,data):
        obj=cls(data['directed'],data['batch']);obj.__dict__.update(data)
        obj.table=ResourceTable(**data['table']);obj.quantity_facts=PublicFacts.from_dict(data['quantity_facts']);return obj
