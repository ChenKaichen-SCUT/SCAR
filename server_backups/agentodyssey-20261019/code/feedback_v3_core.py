"""Observed dependency dispatch and effect-checked recovery; no environment oracle.

All names, recipes, locations and tasks come from public text during this run.
The inherited v2 parser is frozen; overrides below replace its test and recovery logic.
"""
from collections import Counter, deque
import copy, json, re, shlex
try:
    from .feedback_v2_core import Ledger as BaseLedger, counts, compact, uid, DENIAL, schema_error
except ImportError:
    from feedback_v2_core import Ledger as BaseLedger, counts, compact, uid, DENIAL, schema_error

def parts(action):
    try:return shlex.split(action)
    except ValueError:return []

class Ledger(BaseLedger):
    def __init__(self):
        super().__init__()
        self.schemas=[];self.objective=None;self.world={};self.routes={};self.neighbors=[]
        self.visibility=None;self.hand_limit=None;self.container_limits={};self.tool_requirements={}
        self.action_records=[];self.interventions=[];self.test_specs={};self.effects=[]
        self.queue=[];self.epoch=0;self.last_dependency_progress=0;self.last_semantic_key=None
        self.inspections={};self.inspection_versions={};self.observed_roles={};self.current_denials=[]
        self.recovery_generation=0;self.objective_rejections=[];self.max_stagnation=18

    def state_key(self):
        # Time alone is not evidence of a changed rule. Explicit world rewrites are.
        return uid(compact({'location':self.location,'hands':self.hands,'equipped':self.equipped,
          'containers':{k:dict(items=v['items'],complete=v['complete']) for k,v in self.containers.items()},
          'nearby':self.nearby,'visible':self.visibility,'neighbors':self.neighbors,'epoch':self.epoch}))

    def accessible(self):
        total=Counter(self.hands);unknown=[]
        for cid in set(self.hands)|set(self.equipped):
            if cid in self.containers:
                c=self.containers[cid];total.update(c['items'])
                if not c['complete']:unknown.append(cid)
        return dict(total),unknown

    def parse_tasks(self,text):
        super().parse_tasks(text)
        if re.search(r'Tutorial (?:Step .* complete\.|completed|complete!)',text,re.I):
            for t in self.tasks.values():
                if t['scope']=='tutorial' and t['status']=='open':
                    literal=re.search(r'`([^`]+)`',t['text'])
                    if self.pending and literal and self.pending['action']==literal[1]:
                        t['status']='observed_complete';t['completion_evidence']=self.ref(text)

    def advance(self,text):
        before=copy.deepcopy(self.pending);old_location=self.location;old_hands=dict(self.hands)
        old_counts,old_unknown=self.accessible();old_containers=copy.deepcopy(self.containers)
        oldkey=self.state_key();old_plan=self.objective and self.objective['action']
        # Never let the old action-string matcher certify an effect.
        if self.pending:self.pending['test_id']=None
        super().advance(text)
        self.pending=before
        self.current_denials=[l.strip() for l in text.splitlines() if DENIAL.match(l.strip())]
        self.visibility=False if 'too dark to see' in text.lower() else True if 'I see ' in text else None
        if self.visibility is False:self.nearby={}
        m=re.search(r'Neighboring areas:\s*(.*)',text)
        self.neighbors=[x.strip().rstrip('.') for x in m[1].split(',') if x.strip()] if m else []
        if any(x in text for x in ['THE LAWS REWRITE','statutes dissolve','laws rewrite themselves']):
            self.epoch+=1;self.hand_limit=None
        if self.inventory_alias and self.inventory_alias not in self.equipped:self.inventory_alias=None
        # Preserve unrelated known contents after a craft; invalidate only potentially consumed ingredients.
        if before and before['action'].startswith('craft ') and 'successfully crafted' in text:
            ps=parts(before['action']);recipe=self.recipes.get(ps[-1],{})
            if recipe:
                for cid,prior in old_containers.items():
                    if cid not in self.equipped and cid not in self.hands:continue
                    c=self.containers[cid];c['items']={k:v for k,v in prior['items'].items() if k not in recipe['ingredients']}
                    c['complete']=not any(k in prior['items'] for k in recipe['ingredients']) and prior['complete']
        # Store/take/craft changes invalidate an old inspection cache, not all other knowledge.
        for cid,c in self.containers.items():
            if c!=old_containers.get(cid):self.inspection_versions[cid]=self.inspection_versions.get(cid,0)+1
        if before:
            act=before['action'];ps=parts(act)
            if 'not enough space in hand' in text:self.hand_limit={'count':sum(old_hands.values()),'epoch':self.epoch,'step':self.step,'evidence':text}
            if act.startswith('inspect ') and not self.current_denials:
                target=act[8:];cm=re.search(r'capacity:\s*(\d+(?:\.\d+)?)/(\d+(?:\.\d+)?)',text)
                if cm:self.container_limits[self.canonical_container(target)]={'used':float(cm[1]),'limit':float(cm[2]),'step':self.step}
                self.inspections[(target,self.inspection_versions.get(target,0))]=self.step
                # A nullable ingredient-usage listing says nothing about station capability.
                if 'can be used to craft:' in text:self.observed_roles[target]={'craft_listing_semantics':'products using this object as an ingredient, NOT station capabilities','evidence':self.ref(text)}
                if re.search(r'writing (?:tool|implement)|used (?:for|to) (?:writing|write)|(?:pen|stylus).*?(?:inscrib|writ)',text,re.I):
                    self.observed_roles.setdefault(target,{})['possible_writing_tool']=True
            if 'Cannot store' in text and ('capacity' in text.lower() or 'full' in text.lower()) and len(ps)==4:
                cid=self.canonical_container(ps[-1]);self.container_limits[cid]={'full':True,'step':self.step}
            if act.startswith('store ') and 'I stored ' in text and len(ps)==4:
                self.container_limits.pop(self.canonical_container(ps[-1]),None)
            if act.startswith(('take out ','discard ')) and not self.current_denials and len(ps)==4:
                self.container_limits.pop(self.canonical_container(ps[-1]),None)
            if self.location!=old_location and act.startswith('enter '):
                self.routes.setdefault(old_location,{})[act]=self.location
                self.routes.setdefault(self.location,{})
            if act.startswith('write ') and 'No writing tools held in hand' in text:
                self.tool_requirements['write']={'requirement':'a writing tool must be HELD','evidence':self.ref(text)}
            if act.startswith('enter ') and self.visibility is False:
                self.tool_requirements['visibility@'+self.location]={'requirement':'visibility requires an unresolved enabling condition','evidence':self.ref(text)}
        if self.visibility:
            self.world[self.location]={'objects':dict(self.nearby),'step':self.step,'neighbors':list(self.neighbors),'epoch':self.epoch}
        self.effects=[]
        for m in re.finditer(r'I successfully crafted (\d+) ([\w_]+)',text):self.effects.append({'kind':'crafted','object':m[2],'amount':int(m[1])})
        for m in re.finditer(r'I wrote on ([\w_]+):\s*(.*)',text):self.effects.append({'kind':'written','object':m[1],'text':m[2].strip()})
        if before:
            h=self.history[-1];h.pop('hypothesis_test',None)
            key=before.get('context_key',oldkey);unchanged=key==self.state_key()
            h['action_accepted']=not self.current_denials;h['observable_state_changed']=not unchanged
            h['objective_effect_observed']=bool(not self.current_denials and self.target_satisfied(before.get('objective_action','')) and not before.get('target_already_satisfied'))
            h['new_information']=self.new_fact or self.new_task
            self.action_records.append({'step':before['step'],'action':before['action'],'context':key,
                'after_context':self.state_key(),'denied':bool(self.current_denials),'new_information':h['new_information'],
                'objective_effect':h['objective_effect_observed'],'epoch':self.epoch})
            spec=before.get('test_spec')
            if spec:
                pre=before.get('test_preconditions',[]);post=[self.evaluate_predicate(p) for p in spec['expected']]
                unchanged_prediction=before.get('test_expected_before')==post and all(x=='satisfied' for x in post)
                if not pre or not all(x=='satisfied' for x in pre):result='indeterminate_preconditions'
                elif self.current_denials and (before['check']['blockers'] or before['check']['unknown']):result='indeterminate_other_conditions'
                elif unchanged_prediction:result='uninformative_already_true'
                elif any(x=='unknown' for x in post):result='indeterminate_observation'
                elif all(x=='satisfied' for x in post):result='predicted_effect_observed_in_context'
                else:result='prediction_not_observed_in_context'
                h['hypothesis_test']={'id':spec['id'],'outcome':result,'preconditions':pre,'expected_after':post,'action_accepted':not self.current_denials}
                if spec['id'] in self.test_specs:
                    self.test_specs[spec['id']].setdefault('trials',[]).append(h['hypothesis_test']);self.test_specs[spec['id']]['status']='open; context observations only'
            progress=h['objective_effect_observed'] or self.new_task
            if self.objective:
                vector=self.deficit_vector(self.objective['action']);previous=before.get('deficit_vector',{})
                decreased=bool(previous) and sum(vector.values())<sum(previous.values())
                h['dependency_deficits_before']=previous;h['dependency_deficits_after']=vector;h['dependency_deficit_reduced']=decreased
                if progress or decreased:self.last_dependency_progress=self.step
                if h['objective_effect_observed'] and before.get('objective_action')==self.objective['action']:
                    self.objective['status']='effect_observed';self.queue=[]
            if self.current_denials:self.queue=[]
            elif self.queue and self.queue[0]==before['action']:self.queue.pop(0)
        return self.events[-1:]

    def evaluate_predicate(self,p):
        kind=p.get('kind');obj=p.get('object')
        if kind=='visible':return 'unknown' if self.visibility is None else 'satisfied' if (self.visibility if obj is None else self.nearby.get(obj,0)>0) else 'unsatisfied'
        if kind=='crafted':return 'satisfied' if any(e['kind']=='crafted' and e['object']==obj and e['amount']>=p.get('amount',1) for e in self.effects) else 'unsatisfied'
        if kind=='written':return 'satisfied' if any(e['kind']=='written' and e['object']==obj and e['text']==p.get('text') for e in self.effects) else 'unsatisfied'
        if kind=='at_location':return 'satisfied' if self.location==p.get('location') or self.location.split(', ')[-1]==p.get('location') else 'unsatisfied'
        return super().evaluate_predicate(p)

    def target_predicate(self,action):
        p=parts(action)
        if len(p)==3 and p[0]=='craft' and p[1].isdigit():return {'kind':'crafted','object':p[2],'amount':int(p[1])}
        if len(p)==2 and p[0]=='equip':return {'kind':'equipped','object':p[1]}
        if len(p)==3 and p[:2]==['pick','up']:return {'kind':'held','object':p[2]}
        if len(p)>=3 and p[0]=='write':return {'kind':'written','object':p[-1],'text':' '.join(p[1:-1])}
        if len(p)==2 and p[0]=='enter':return {'kind':'at_location','location':p[1]}
        return None

    def target_satisfied(self,action):
        pred=self.target_predicate(action)
        return bool(pred and self.evaluate_predicate(pred)=='satisfied')

    def valid_predicate(self,p):
        if not isinstance(p,dict) or p.get('kind') not in ['held','equipped','quantity','at_location','visible','crafted','written','task_complete']:return False
        if p['kind'] in ['held','equipped','quantity','crafted','written'] and not isinstance(p.get('object'),str):return False
        if p['kind'] in ['quantity','crafted'] and (not isinstance(p.get('amount',1),(int,float)) or p.get('amount',1)<=0):return False
        if p['kind']=='written' and not isinstance(p.get('text'),str):return False
        if p['kind']=='at_location' and not isinstance(p.get('location'),str):return False
        if p['kind']=='task_complete' and p.get('task_id') not in self.tasks:return False
        return True

    def install_objective(self,action,goal,reason='',evidence=None):
        if not isinstance(action,str) or not action.strip() or (self.schemas and schema_error(action,self.schemas)):return False
        if goal not in self.tasks or self.tasks[goal]['status']!='open':return False
        pred=self.target_predicate(action)
        if pred and pred.get('kind')=='crafted' and pred['object'] not in self.recipes:return False
        if self.objective and self.objective['status']=='active':
            old=self.objective
            if old['action']==action:return True
            if old['goal_id']==goal and self.step-self.last_dependency_progress<self.max_stagnation:
                self.objective_rejections.append({'step':self.step,'requested':action,'retained':old['action'],'reason':'keep unfinished target; proposed preparatory actions are not a new terminal objective'})
                return False
        self.objective={'action':action,'goal_id':goal,'reason':reason,'evidence':evidence or [],'installed':self.step,'status':'already_observed' if self.target_satisfied(action) else 'active'}
        self.last_dependency_progress=self.step;self.queue=[];return True

    def needed(self,action):
        p=parts(action);need={}
        if len(p)==3 and p[0]=='craft' and p[-1] in self.recipes:
            n=float(p[1]) if p[1].isdigit() else 1
            need={k:v*n for k,v in self.recipes[p[-1]]['ingredients'].items()}
        elif len(p)==2 and p[0]=='equip':need={p[1]:1}
        elif len(p)==3 and p[:2]==['pick','up']:need={p[2]:1}
        return need

    def deficit_vector(self,action):
        total,_=self.accessible();return {k:max(0,n-total.get(k,0)) for k,n in self.needed(action).items()}

    def dependency_requirements(self,action):
        """Transitive quantity demand for a terminal target, with existing intermediates credited."""
        result=Counter();total,_=self.accessible()
        def visit(obj,n,seen):
            result[obj]+=n
            missing=max(0,n-total.get(obj,0))
            if missing and obj in self.recipes and obj not in seen:
                import math
                for child,qty in self.recipes[obj]['ingredients'].items():visit(child,qty*math.ceil(missing),seen|{obj})
        for obj,n in self.needed(action).items():visit(obj,n,set())
        return dict(result)

    def available_container(self):
        candidates=[c for c in self.containers if c in self.hands or c in self.equipped or c in self.nearby]
        def rank(c):return (c not in self.equipped,c not in self.hands,c)
        for c in sorted(candidates,key=rank):
            cap=self.container_limits.get(c,{})
            if not cap.get('full') and (not cap or cap.get('used',0)<cap.get('limit',float('inf'))):return c
        return None

    def free_hand(self,needed=None):
        needed=needed or {};c=self.available_container()
        # Equipping a held container both frees a hand and exposes its contents.
        for obj in self.hands:
            if obj in self.containers:return 'equip '+obj
        objects=sorted(self.hands,key=lambda obj:(obj in needed,obj))
        if c:
            obj=next((x for x in objects if x!=c),None)
            if obj:return f'store 1 {obj} {c}'
        # Dropping is a last, reversible local preparation; never delete/discard a resource.
        if objects:return 'drop '+objects[0]
        return None

    def pickup(self,obj,needed=None):
        limit=self.hand_limit
        if limit and limit['epoch']==self.epoch and sum(self.hands.values())>=limit['count']:return self.free_hand(needed)
        return 'pick up '+obj

    def route_to(self,location):
        if location==self.location:return None
        q=deque([(self.location,[])]);seen={self.location}
        while q:
            loc,path=q.popleft()
            for action,nxt in self.routes.get(loc,{}).items():
                if nxt==location:return (path+[action])[0]
                if nxt not in seen:seen.add(nxt);q.append((nxt,path+[action]))
        name=location.split(', ')[-1]
        if name in self.neighbors:return 'enter '+name
        return None

    def acquire(self,obj,n,needed,visited=None):
        visited=set(visited or [])
        if obj in visited:return None
        visited.add(obj);total,unknown=self.accessible()
        if total.get(obj,0)>=n:return None
        # Existing contents need an access-mode change before more ingredients are manufactured.
        for cid,c in self.containers.items():
            if c['items'].get(obj,0)>0 and cid in self.nearby and cid not in self.hands and cid not in self.equipped:
                return self.pickup(cid,needed)
        if self.nearby.get(obj,0)>0:return self.pickup(obj,needed)
        for cid in unknown:
            if (cid,self.inspection_versions.get(cid,0)) not in self.inspections:return 'inspect '+cid
        if obj in self.recipes:
            recipe=self.recipes[obj];missing={k:v for k,v in recipe['ingredients'].items() if total.get(k,0)<v}
            for child,amount in missing.items():
                action=self.acquire(child,amount,needed,visited)
                if action:return action
            if not missing:return 'craft 1 '+obj
        for loc,record in sorted(self.world.items(),key=lambda kv:-kv[1]['step']):
            if record['objects'].get(obj,0)>0:
                action=self.route_to(loc)
                if action:return action
        return None

    def preparation(self):
        o=self.objective
        if not o or o['status']!='active':return None
        action=o['action'];p=parts(action);total,unknown=self.accessible();need=self.needed(action)
        if p and p[0]=='equip' and len(p)==2 and p[1] in self.hands:return action
        if p and p[0]=='equip' and len(p)==2 and p[1] in self.containers and p[1] in self.nearby:return self.pickup(p[1],need)
        for obj,n in need.items():
            if total.get(obj,0)<n:
                a=self.acquire(obj,n,need)
                if a:return a
        if any(total.get(k,0)<n for k,n in need.items()):return None
        if p and p[0]=='equip' and len(p)==2 and p[1] not in self.hands:
            for cid,c in self.containers.items():
                if c['items'].get(p[1],0)>0 and cid in set(self.hands)|set(self.equipped):
                    if self.hand_limit and sum(self.hands.values())>=self.hand_limit['count']:return self.free_hand(need)
                    return f'take out {p[1]} {cid}'
        if p and p[0]=='write' and 'write' in self.tool_requirements:
            candidates=[obj for obj,role in self.observed_roles.items() if role.get('possible_writing_tool')]
            if not any(obj in self.hands for obj in candidates):
                for obj in candidates:
                    if obj in self.nearby:return self.pickup(obj)
                    for loc,record in self.world.items():
                        if obj in record['objects']:
                            route=self.route_to(loc)
                            if route:return route
                return None
        if p and p[0]=='craft':
            station=self.stations.get(p[-1])
            if station and any(obj not in self.nearby for obj in station['required']):
                for loc,record in self.world.items():
                    if all(obj in record['objects'] for obj in station['required']):return self.route_to(loc)
                return None
        return action if p and p[0] in ['craft','equip','write'] else None

    def action_check(self,action,goal_id=None,schemas=None):
        c=super().action_check(action,goal_id,schemas)
        # The old generic reserve warning remains advisory; storage preparation must be possible.
        key=self.state_key();prior=[r for r in self.action_records if r['action']==action and r['context']==key]
        combat=action.startswith(('attack ','defend','eat '))
        if not combat and (len(prior)>=2 or any(r['denied'] for r in prior)):
            c['blockers'].append({'kind':'repeated_context_action','action':action,'attempts':len(prior),'reason':'same observed preconditions; supply a new preparation, evidence, or a different task'})
        if action.startswith('inspect '):
            obj=action[8:]
            if (obj,self.inspection_versions.get(obj,0)) in self.inspections:
                c['blockers'].append({'kind':'inspection_has_no_new_question','object':obj,'reason':'this version was already inspected; do not cycle among objects'})
        p=parts(action)
        if self.objective and self.objective['status']=='active' and len(p)==3 and p[0]=='craft' and action!=self.objective['action']:
            need=self.dependency_requirements(self.objective['action']);total,_=self.accessible()
            if p[-1] in need and total.get(p[-1],0)>=need[p[-1]]:
                c['blockers'].append({'kind':'already_satisfied_dependency','object':p[-1],'required':need[p[-1]],'available':total.get(p[-1],0),'target':self.objective['action']})
        if action.startswith('pick up ') and self.hand_limit and self.hand_limit['epoch']==self.epoch and sum(self.hands.values())>=self.hand_limit['count']:
            c['blockers'].append({'kind':'observed_hand_capacity','detail':self.hand_limit})
        if p and p[0]=='store' and len(p)==4:
            cap=self.container_limits.get(self.canonical_container(p[-1]),{})
            if cap.get('full') or (cap and cap.get('used',0)>=cap.get('limit',float('inf'))):c['blockers'].append({'kind':'observed_container_capacity','object':p[-1]})
        return c

    def dispatch(self,candidates,goal_id):
        options=[]
        matching=not self.objective or self.objective['goal_id']==goal_id
        if not matching:self.queue=[]
        if self.queue:options.append({'source':'committed_short_plan','actions':list(self.queue)})
        prep=self.preparation() if matching else None
        if prep:options.append({'source':'dependency_preparation','actions':[prep]})
        for x in candidates:
            if isinstance(x,dict) and isinstance(x.get('actions'),list):
                seq=[a for a in x['actions'][:6] if isinstance(a,str) and a.strip()]
                if seq:options.append({'source':'model_candidate','actions':seq})
        rejected=[]
        for option in options:
            action=option['actions'][0];check=self.action_check(action,goal_id,self.schemas)
            if check['blockers']:
                rejected.append({'action':action,'source':option['source'],'blockers':check['blockers']});continue
            self.queue=option['actions'][:]
            record={'step':self.step,'selected':action,'source':option['source'],'rejected':rejected}
            self.interventions.append(record)
            return action,check,record
        record={'step':self.step,'selected':None,'source':'no_admissible_candidate','rejected':rejected}
        self.interventions.append(record);self.queue=[]
        return None,None,record

    def apply_review(self,r):
        # Do not admit free-form 'expected' as a certified effect or inherit old hypotheses.
        if not isinstance(r,dict):r={}
        cleaned={k:v for k,v in r.items() if k not in ['plans','hypotheses']};event=super().apply_review(cleaned)
        objective=r.get('objective') or {}
        if isinstance(objective,dict):self.install_objective(objective.get('action'),r.get('focus_task_id'),str(objective.get('reason','')),self.refs(objective.get('evidence')))
        for h in r.get('hypotheses',[])[:2] if isinstance(r.get('hypotheses'),list) else []:
            if not isinstance(h,dict):continue
            pre=h.get('preconditions',[]);post=h.get('expected',[]);refs=self.refs(h.get('evidence'))
            if not refs or not pre or not post or not all(self.valid_predicate(p) for p in pre+post):continue
            hid=str(h.get('id') or uid(compact(h)))[:80]
            self.test_specs[hid]={'id':hid,'claim':str(h.get('claim',''))[:600],'test_action':str(h.get('test_action','')),
              'preconditions':pre,'expected':post,'evidence':refs,'created_step':self.step,'trials':[],'status':'open'}
        # Retain a bounded recent set; stable IDs are not a substitute for evidence or validity.
        self.test_specs=dict(list(self.test_specs.items())[-12:]);return event

    def choose(self,action,reasoning,goal_id=None,test_id=None,check=None):
        # Explicit test identity and current applicability, never string-only automatic matching.
        spec=self.test_specs.get(test_id)
        if spec and (spec['test_action']!=action or self.step-spec['created_step']>12):spec=None
        self.pending={'step':self.step,'action':action,'reasoning':reasoning,'goal_id':goal_id or self.focus,'test_id':None,
          'test_spec':copy.deepcopy(spec),'test_preconditions':[self.evaluate_predicate(p) for p in spec['preconditions']] if spec else [],
          'test_expected_before':[self.evaluate_predicate(p) for p in spec['expected']] if spec else [],
          'check':check or self.action_check(action,goal_id),'context_key':self.state_key(),
          'objective_action':self.objective['action'] if self.objective else '',
          'target_already_satisfied':self.target_satisfied(self.objective['action']) if self.objective else False,
          'deficit_vector':self.deficit_vector(self.objective['action']) if self.objective else {}}

    def trigger(self):
        released=min(60,1+self.step*60//500)
        if self.reviews>=released or self.step-self.last_review<5:return None
        if self.new_task:return 'task_changed'
        if self.objective and self.step-self.last_dependency_progress>=self.max_stagnation:return 'objective_stalled_switch_strategy'
        if self.interventions and self.interventions[-1]['rejected']:return 'dispatcher_rejections'
        if self.step-self.last_review>=14:return 'dependency_review'
        return None

    def packet(self):
        p=super().packet();p.pop('plans',None);p.pop('plan_status',None)
        p['hypotheses']=list(self.test_specs.values());p['objective']=self.objective
        p['deficits']=self.deficit_vector(self.objective['action']) if self.objective else {}
        p['next_dependency_action']=self.preparation();p['committed_short_plan']=self.queue
        p['recent_dispatcher_interventions']=self.interventions[-4:];p['objective_change_rejections']=self.objective_rejections[-2:]
        p['observed_hand_limit']=self.hand_limit;p['observed_container_limits']=self.container_limits
        p['tool_conditions']=self.tool_requirements;p['field_semantics']=self.observed_roles
        p['observed_locations']=self.world;p['known_routes']=self.routes;p['current_visibility']=self.visibility
        p['steps_without_dependency_progress']=self.step-self.last_dependency_progress
        p['guidance']=self.guidance
        p['semantics']='Current raw observations override stale location records. Ingredient recipe listings are NOT station capabilities. An accepted action does not establish a predicted effect. Preparing access/space/tools can be necessary even when each individual fact is known. Every candidate and fallback is subject to the same recurrence checks.'
        return p
