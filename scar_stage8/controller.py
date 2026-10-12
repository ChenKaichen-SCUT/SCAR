"""MRR/RCR share small public-evidence execution constraints; no engine imports.

Unknown transfer weights/recipe costs stay UNKNOWN. A first evidence-supported
trial is not a legality guarantee. Rejection and no-progress guards cover both
structured candidates and base fallbacks. Disable safety for exact Stage 7 parity.
"""
import copy
import math
from contextlib import contextmanager
from scar.io import digest
from scar_sequence.planner import q
from scar_sequence.public import ResourceTable
from scar_unknown17.facts import PublicFacts
from scar_unknown17_stage7.controller import Stage7Controller, CONFIGS, FLAGS
from scar_v3.state import parse_action

METHODS=['P0','P1','P2','P3','P4']
HISTORICAL={'P0':'C0','P1':'C1','P2':'C5','P3':'C1','P4':'C5'}

class NoCandidate(Exception):
    """Bounded public planner cannot support a structured action this turn."""

class ReliableController(Stage7Controller):
    MAX_DEPTH=12
    MAX_NODES=64
    MAX_CANDIDATES=48

    def __init__(self, method='P3', safety=True, **flags):
        super().__init__(**(flags or CONFIGS[HISTORICAL[method]]))
        self.method=method; self.safety=safety
        self.failed_actions={};self.no_progress={};self.negative_ground={};self.safety_decision={}
        self.solving=[];self.search_nodes=0;self.candidates=0;self.depth_peak=0
        self.last_public_action_context=None

    @contextmanager
    def solving_node(self,node):
        if not self.safety:
            yield;return
        self.search_nodes+=1
        if node in self.solving or len(self.solving)>=self.MAX_DEPTH or self.search_nodes>self.MAX_NODES:
            self.safety_decision.setdefault('search_limits',[]).append(node)
            raise NoCandidate('repeated dependency or bounded search limit')
        self.solving.append(node);self.depth_peak=max(self.depth_peak,len(self.solving))
        try:yield
        finally:self.solving.pop()

    def _all_needed(self,item,seen=None):
        if not self.safety:return super()._all_needed(item,seen)
        seen=set(seen or ());pending=[item]
        while pending and len(seen)<self.MAX_NODES:
            x=pending.pop()
            if x in seen:continue
            seen.add(x);pending.extend(self.table.recipes.get(x,{}).get('ingredients',[]))
        if pending:self.safety_decision['dependency_truncated']=True
        return seen

    def _location_explore(self):
        t=self.table;now=t.state.get('location');dest=[]
        for x in t.state.get('neighbors') or []:
            if x not in t.places:dest.append(x)
        for loc,data in t.places.items():
            if loc!=now and any(x not in t.inspected and x not in self.probes for x in data['objects']):dest.append(loc)
        for loc in sorted(set(dest),key=lambda x:(len(t.path(x) or [x]),x)):
            path=t.path(loc)
            if path:
                action='enter '+q(path[0])
                if self.admissible(action):return action
        return None

    def _station(self,recipe):
        if not self.safety:return super()._station(recipe)
        with self.solving_node('station:'+recipe):
            t=self.table;stations=t.recipes.get(recipe,{}).get('stations',[])
            if not stations or all((t.state.get('ground') or {}).get(x,0)>0 for x in stations):return None
            for loc,data in sorted(t.places.items()):
                if all(data['objects'].get(s,0)>0 for s in stations):
                    if action:=self._move(loc):return action
            action=self._location_explore()
            if action:return action
            raise NoCandidate('required station location UNKNOWN; independent location frontier exhausted')

    def _explore(self,needed):
        if not self.safety:return super()._explore(needed)
        with self.solving_node('explore:'+','.join(sorted(needed))):return super()._explore(needed)

    def _gap_explore(self,needed):
        if not self.safety:return super()._gap_explore(needed)
        with self.solving_node('gap:'+','.join(sorted(needed))):return super()._gap_explore(needed)

    def _acquire(self,name,amount,protect,use_container=True):
        if not self.safety:return super()._acquire(name,amount,protect,use_container)
        with self.solving_node('acquire:'+name):
            a=self.collection(name,amount) if (self.table.count(name) or 0)<amount else None
            return a or super()._acquire(name,amount,protect,use_container)

    def action_context(self,action):
        """Relevant observable conditions, never time or unrelated feedback."""
        p=parse_action(action);t=self.table;s=t.state;name=p.target
        ckey=(t.inventory if p.args and p.args[-1]=='inventory' else p.args[-1]) if p.verb in {'store','take out'} else None
        c=t.containers.get(ckey,{})
        if p.verb in {'pick up','store','take out'}:
            return {'location':s.get('location'),'target_ground':(s.get('ground') or {}).get(name,0),
                'target_held':(s.get('hands') or {}).get(name,0),'hands_used':sum((s.get('hands') or {}).values()),
                'container':ckey,'accessible':t.access(ckey) if ckey else None,
                'container_target':(c.get('counts') or {}).get(name) if c.get('counts') is not None else None,
                'load':c.get('load'),'capacity':c.get('capacity')}
        if p.verb=='craft':return self.public_context(name)
        return {k:s.get(k) for k in ['location','hands','equipment','ground']}|{'containers':{k:v.get('counts') for k,v in t.containers.items()},
            'recipes':{k:{f:v.get(f) for f in ['ingredients','stations','quantities']} for k,v in t.recipes.items()}}

    def failure_key(self,action):
        p=parse_action(action)
        # Quantity changes cannot evade a failed pickup/transfer.
        return p.verb+':'+p.target+(':'+str(p.args[-1]) if p.verb in {'store','take out'} else '')

    def admissible(self,action):
        if not action:return False
        if self.candidates>=self.MAX_CANDIDATES:
            self.safety_decision['candidate_limit_reached']=True;return False
        self.candidates+=1
        p=parse_action(action);t=self.table;s=t.state;g=s.get('ground') or {};h=s.get('hands') or {}
        if p.verb=='invalid':return False
        neg=self.negative_ground.get(p.target)
        if neg and neg['location']==s.get('location') and neg['ground']==g.get(p.target,0):
            if p.verb=='pick up' or (p.verb=='store' and p.args and p.args[0].isdigit() and int(p.args[0])>h.get(p.target,0)):return False
        ctx=self.action_context(action);old=self.failed_actions.get(self.failure_key(action))
        if old and old['context']==ctx:return False
        if self.no_progress.get(digest([action,ctx]),0)>=2 and p.verb!='wait':return False
        if not self.retry_allowed(action):return False
        if p.verb=='pick up':
            if g.get(p.target,0)<=0 or sum(h.values())>=2:return False
            if p.target==parse_action(self.target).target and (t.count(p.target) or 0)>=self.amount:return False
        elif p.verb in {'store','take out'}:
            name=t.inventory if p.args[-1]=='inventory' else p.args[-1];c=t.containers.get(name,{})
            if not name or not t.access(name):return False
            if p.verb=='take out':
                if sum(h.values())>=2 or not (c.get('counts') or {}).get(p.target,0):return False
            else:
                if not p.args[0].isdigit() or int(p.args[0])<1:return False
                if h.get(p.target,0)+g.get(p.target,0)<int(p.args[0]):return False
                if c.get('capacity') is not None and c.get('load') is not None and c['load']>=c['capacity']:return False
                if p.target==name:return False
        elif p.verb=='enter' and t.enter_status(p.target)=='REJECT':return False
        elif p.verb=='craft':
            if not p.args or not p.args[0].isdigit() or int(p.args[0])<1:return False
            stations=t.recipes.get(p.target,{}).get('stations',[])
            if stations and not all(g.get(x,0)>0 for x in stations):return False
        return True

    def collection(self,name,need,base=None):
        t=self.table;s=t.state;h=s.get('hands') or {};g=s.get('ground') or {};own=t.count(name) or 0
        if own>=need:return None
        options=[]
        # Preserve a base transfer that can collect the full deficit in one action.
        if base:
            p=parse_action(base)
            if p.target==name and p.verb in {'store','pick up','take out'}:options.append(base)
        if g.get(name,0)>0:
            n=int(h.get(name,0)+(min(g[name],max(1,math.ceil(need-own))) if name==parse_action(self.target).target else g[name]))
            if t.inventory:
                c=t.containers.get(t.inventory,{})
                if c.get('load') is not None and c.get('capacity') is not None and c['capacity']>c['load']:
                    options.append(f'store {n} {q(name)} inventory')
            options.append('pick up '+q(name))
        for c,data in sorted(t.containers.items()):
            if not t.carried(c) and t.access(c) and (data.get('counts') or {}).get(name,0):options.append(f'take out {q(name)} {q(c)}')
        def gain(a):
            p=parse_action(a)
            if p.verb=='pick up':return 1
            if p.verb=='take out':return 1
            name_c=t.inventory if p.args[-1]=='inventory' else p.args[-1]
            return max(0,min(g.get(name,0),int(p.args[0])-h.get(name,0))) if t.carried(name_c) else -1
        for a in sorted(dict.fromkeys(options),key=lambda a:(-gain(a),a!=base)):
            if gain(a)>0 and self.admissible(a):return a
        return None

    def _goal_action(self,base):
        if not self.safety:return super()._goal_action(base)
        a=self.collection(parse_action(self.target).target,self.amount,base)
        return a,'shared_public_collection' if a else None

    def ready_nodes(self):
        nodes=super().ready_nodes()
        if not self.safety:return nodes
        t=self.table
        return [x for x in nodes if not (t.state.get('ground') or {}).get(x,0) and not any(
            t.access(c) and (d.get('counts') or {}).get(x,0) for c,d in t.containers.items())]

    def protect_craft(self,action,base):
        p=parse_action(action)
        if p.verb!='craft':return action
        t=self.table;goal=parse_action(self.target).target
        need=self.public_demand(p.target);owned=t.count(p.target) or 0
        if owned>=need:
            self.safety_decision.setdefault('production_blocked',[]).append({'action':action,'reason':'public owned amount sufficient','need':need})
            return None
        if a:=self.collection(p.target,need,base):
            self.safety_decision['collect_before_craft']={'rejected':action,'selected':a};return a
        # Existing copies, but unknown container contents/capacity or full hands:
        # inspect/free capacity before consuming a new batch of raw materials.
        if (t.state.get('ground') or {}).get(p.target,0)>0:
            failed=any(x['target']==p.target for x in self.failed_actions.values())
            if not failed:
                self.safety_decision['existing_copy_unknown_access']=action
                if t.inventory and self.admissible('inspect inventory'):return 'inspect inventory'
                return None
        r=t.recipes.get(p.target,{});deps=r.get('ingredients',[])
        if goal in deps and (t.count(goal) or 0)<=self.amount:
            self.safety_decision['protect_owned_goal']=action;return None
        shared=set(deps)&set(self.reservations(p.target))
        amount=int(p.args[0]);deficit=max(1,math.ceil(need-owned))
        # Exact consumption is UNKNOWN; a single necessary trial is retained.
        # No batch > public demand, and no speculative surplus for shared inputs.
        limit=deficit if self.public_quantity_rules.get(p.target) else (1 if shared else max(2,deficit))
        amount=min(amount,limit)
        if shared:
            weights=self.public_quantity_rules.get(p.target,{}).get('quantities',{})
            reserves=self.reservations(p.target)
            # Explicit nominal weights provide only a conservative ceil bound;
            # never infer a numeric weight from an ingredient name.
            feasible=[n for n in range(1,amount+1) if all(k in weights and t.count(k) is not None and
                t.count(k)-math.ceil(weights[k]*n)>=reserves[k] for k in shared)]
            amount=max(feasible) if feasible else 1
        self.safety_decision['quantity_constraint']={'target':p.target,'shared_inputs':sorted(shared),
            'public_demand':need,'selected':amount,'actual_consumption':'UNKNOWN except exactly scoped past samples'}
        return f'craft {amount} {q(p.target)}'

    def choose(self,obs,base_action):
        if not self.safety:return super().choose(obs,base_action)
        self.solving=[];self.search_nodes=0;self.candidates=0;self.depth_peak=0;self.safety_decision={}
        self.stage7_decision={};self.mechanism_decision={};self.last_ready=[];self.last_choice={}
        self.table.observe(obs)
        goal=parse_action(self.target).target
        immediate=self.collection(goal,self.amount,base_action)
        try:action=immediate or super().choose(obs,base_action)
        except NoCandidate as exc:
            self.safety_decision['safe_fallback']=str(exc);action=None
        action=self.protect_craft(action,base_action) if action else None
        if not self.admissible(action):
            self.safety_decision['rejected_candidate']=action
            action=self.protect_craft(base_action,base_action)
            if not self.admissible(action):action=self._location_explore()
            if not action or not self.admissible(action):
                action='wait';self.safety_decision['no_candidate']=True
        if not self.last_choice:self.last_choice={}
        self.safety_decision.update(search_nodes=self.search_nodes,depth_peak=self.depth_peak,candidates=self.candidates,
            candidate_limit=self.MAX_CANDIDATES,base_preserved=action==base_action,
            transfer_capacity_scope='positive observed capacity checked; unknown item volume not treated as 1; first trial can be rejected')
        self.last_choice.update(action=action,queue=list(self.queue),resource_table=self.table.to_dict(),
            target=self.target,safety=copy.deepcopy(self.safety_decision),stage7=copy.deepcopy(self.stage7_decision))
        self.last_public_action_context=self.action_context(action)
        return action

    def observe(self,before,action,after):
        if not self.safety:return super().observe(before,action,after)
        self.table.observe(before);context=self.action_context(action);p=parse_action(action)
        old=self.flags['resource_goal_guard'];self.flags['resource_goal_guard']=True
        try:super().observe(before,action,after)
        finally:self.flags['resource_goal_guard']=old
        feedback=self.table.state.get('feedback','')
        rejected=any(x in feedback for x in ['Cannot ','Invalid ','cannot ','not found','not see'])
        if rejected and p.verb in {'pick up','store','take out'} and ('not found' in feedback or 'not see' in feedback):
            self.negative_ground[p.target]={'location':context.get('location'),'ground':context.get('target_ground'),'feedback':feedback}
        if p.target in self.negative_ground and (self.table.state.get('location')!=self.negative_ground[p.target]['location'] or (self.table.state.get('ground') or {}).get(p.target,0)!=self.negative_ground[p.target]['ground']):
            self.negative_ground.pop(p.target)
        if rejected:
            self.failed_actions[self.failure_key(action)]={'action':action,'target':p.target,'context':context,'feedback':feedback}
        elif self.failure_key(action) in self.failed_actions:self.failed_actions.pop(self.failure_key(action))
        after_ctx=self.action_context(action)
        signature=digest([action,context])
        if context==after_ctx:self.no_progress[signature]=self.no_progress.get(signature,0)+1
        else:self.no_progress.pop(signature,None)

    @classmethod
    def from_dict(cls,data):
        obj=cls(data.get('method','P3'),data.get('safety',True),**data.get('flags',{}))
        obj.__dict__.update(copy.deepcopy(data));obj.table=ResourceTable(**data['table'])
        obj.quantity_facts=PublicFacts.from_dict(data['quantity_facts']);return obj


def make_controller(method):
    if method in ['P0','P1','P2']:return Stage7Controller(**CONFIGS[HISTORICAL[method]])
    return ReliableController(method)


def restore_controller(data):
    return ReliableController.from_dict(data) if 'safety' in data else Stage7Controller.from_dict(data)
