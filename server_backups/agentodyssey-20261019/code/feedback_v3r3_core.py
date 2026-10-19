"""Observation-scoped probes, finite outcome contracts and resource-aware plans.

No game identifiers, hidden state, rewards, saved trajectories or provider calls.
All operation evidence is learned in this episode. Search is local and bounded.
"""
import copy,json,re
from collections import Counter,deque
try:
    from .feedback_v3r2_core import Ledger as Previous
    from .feedback_v3_core import parts
    from .feedback_v2_core import uid,compact,schema_error,DENIAL
except ImportError:
    from feedback_v3r2_core import Ledger as Previous
    from feedback_v3_core import parts
    from feedback_v2_core import uid,compact,schema_error,DENIAL

class Ledger(Previous):
    def __init__(self):
        super().__init__()
        self.receipt=None;self.contract=None;self.contract_events=[];self.committed=[]
        self.operation_evidence={};self.probes={};self.probe_results=[];self.next_probe=None
        self.locks={};self.held_tools={};self.capacity_observations={};self.failed_plans={}
        self.plan_origin=None;self.plan_checks=[];self.execution_choice=None;self.plan_repairs=[]
        self.hp=None;self.area_costs={};self.recent_damage=deque(maxlen=8);self.rule_revision=0
        self.objective_completions=[];self.rejected_objectives=[];self.search_nodes=0

    def operation_receipt(self,action,text):
        if not action or any(DENIAL.match(l.strip()) for l in text.splitlines()):return None
        p=parts(action)
        if not p:return None
        evidence=None
        patterns=[]
        if p[0]=='drop' and len(p)==2:patterns=[rf'^I dropped {re.escape(p[1])}\.']
        elif p[:2]==['take','out'] and len(p)==4:patterns=[rf'^I took out {re.escape(p[2])} from {re.escape(p[3])}\.']
        elif p[0]=='store' and len(p)==4:patterns=[rf'^I stored {re.escape(p[1])} {re.escape(p[2])} in {re.escape(p[3])}\.']
        elif p[0]=='eat' and len(p)==2:patterns=[rf'^I ate (?:\d+ )?{re.escape(p[1])}\b']
        elif action=='defend':patterns=[r'^I am defending\.',r'^I took a defensive stance\.']
        elif action=='wait':patterns=[r'^I waited\b',r'^I wait\b']
        elif p[0]=='unequip' and len(p)==2:patterns=[rf'^I unequipped {re.escape(p[1])}\b']
        elif p[0]=='inspect' and len(p)==2:patterns=[rf'^I inspected {re.escape(p[1])}\b']+[r'^I inspected my inventory\.']*int(p[1]=='inventory')
        elif p[:2]==['talk','to'] and len(p)==3:patterns=[rf'^{re.escape(p[2])} says:']
        elif p[0]=='lockpick' and len(p)==2:patterns=[rf'^.*(?:unlocked|lockpicked|picked the lock).*\b{re.escape(p[1])}\b']
        for line in text.splitlines():
            if any(re.search(pat,line.strip(),re.I) for pat in patterns):evidence=line.strip();break
        return {'action':action,'after_step':self.step+1,'quote':evidence} if evidence else None

    def target_predicate(self,action):
        pred=super().target_predicate(action)
        if pred:return pred
        p=parts(action)
        if p and (p[0] in ['drop','store','eat','defend','wait','unequip','inspect','lockpick'] or p[:2] in [['take','out'],['talk','to']]):
            return {'kind':'operation_observed','action':action}
        return None

    def evaluate_predicate(self,p):
        if p.get('kind')=='operation_observed':
            return 'satisfied' if self.receipt and self.receipt['action']==p.get('action') and self.receipt['after_step']==self.step else 'unsatisfied'
        return super().evaluate_predicate(p)

    def valid_predicate(self,p):
        if isinstance(p,dict) and p.get('kind')=='operation_observed':return isinstance(p.get('action'),str) and not schema_error(p['action'],self.schemas)
        return super().valid_predicate(p)

    def install_objective(self,action,goal,reason='',evidence=None):
        if not isinstance(action,str) or not self.target_predicate(action):
            self.rejected_objectives.append({'step':self.step,'action':action,'reason':'no verifiable completion predicate'});return False
        if (self.schemas and schema_error(action,self.schemas)) or goal not in self.tasks or self.tasks[goal]['status']!='open':return False
        pred=self.target_predicate(action)
        if pred['kind']=='crafted' and pred['object'] not in self.recipes:return False
        old=self.objective
        if old and old['status']=='active' and old['action']==action and old['goal_id']==goal:return True
        # Preparations and emergency actions may execute without replacing a
        # still useful outcome contract. Change the contract after evidence or
        # a bounded period with no net progress, not after every observation.
        if old and old['status']=='active' and old['goal_id']==goal and old['action']!=action:
            terminal=parts(old['action'])[0] in ['craft','write','lockpick','enter']
            if terminal and self.step-self.last_dependency_progress<24:
                self.objective_rejections.append({'step':self.step,'requested':action,'retained':old['action'],'reason':'preparation or interrupt preserves outcome contract'});return False
        event=pred['kind'] in ['operation_observed','crafted','written']
        self.objective={'action':action,'goal_id':goal,'reason':reason,'evidence':evidence or [],'installed':self.step,'status':'already_observed' if not event and self.target_satisfied(action) else 'active'}
        self.last_dependency_progress=self.step;self.queue=[]
        accepted=True
        if accepted:
            self.contract={'action':self.objective['action'],'goal_id':goal,'completion':self.target_predicate(action),'created':self.step,'status':self.objective['status'],'best_deficit':None,'seen':{},'phase':'preparing'}
            self.committed=[];self.plan_origin=None
        return accepted

    def _capacity_key(self,location=None,equipped=None):
        return compact([self.epoch,self.life,location or self.location,sorted((equipped if equipped is not None else self.equipped).items())])

    def capacity_bound(self,location=None,equipped=None):
        return self.capacity_observations.get(self._capacity_key(location,equipped))

    def cost_context(self):
        c=self.area_costs.get(self.location,{});damage=c.get('damage',0)/max(1,c.get('visits',0))
        return {'health':self.hp,'observed_damage_per_step':round(damage,2),'noise_events':c.get('noise',0),'immediate_risk':self.hp is not None and self.hp<=max(1,3*damage)}

    def relevant_context(self):
        needed=self.needed(self.work_action() or '')
        objs=set(needed)|set(self.protected_items())|set(self.containers)
        state={'goal':self.objective and self.objective['action'],'location':self.location,'epoch':self.epoch,'life':self.life,
          'hands':{k:v for k,v in self.hands.items() if k in objs},'occupancy':sum(self.hands.values()),'equipment':self.equipped,
          'containers':{k:v['items'] for k,v in self.containers.items() if k in self.hands or k in self.equipped or k in self.nearby},
          'visible':self.visibility,'ground':{k:v for k,v in self.nearby.items() if k in objs},'rules':self.rule_revision}
        return uid(compact(state))

    def advance(self,text):
        before=copy.deepcopy(self.pending);old_hands=dict(self.hands);old_equipped=dict(self.equipped);old_loc=self.location
        old_vis=self.visibility;old_contract=copy.deepcopy(self.contract);old_queue=list(self.committed)
        old_counts,_=self.accessible();old_epoch=self.epoch;old_life=self.life
        self.receipt=self.operation_receipt(before['action'],text) if before else None
        result=super().advance(text)
        m=re.search(r'My health is at (\d+(?:\.\d+)?)',text);self.hp=float(m[1]) if m else None
        damage=sum(float(x) for x in re.findall(r'lost (\d+(?:\.\d+)?) HP',text));self.recent_damage.append(damage)
        c=self.area_costs.setdefault(self.location,{'visits':0,'damage':0,'noise':0});c['visits']+=1;c['damage']+=damage;c['noise']+=int('Noise draws' in text)
        if self.epoch!=old_epoch:self.locks={};self.held_tools={};self.capacity_observations={};self.operation_evidence={};self.probes={};self.failed_plans={};self.rule_revision+=1
        if before:
            a=before['action'];p=parts(a);denied=bool(self.current_denials)
            if 'not enough space in hand' in text and old_hands and self.life==old_life:
                key=self._capacity_key(old_loc,old_equipped);self.capacity_observations[key]={'count':sum(old_hands.values()),'step':self.step,'scope':'local occupancy estimate; revised by successful transfers'}
            elif not denied and self.hands_known:
                key=self._capacity_key();cap=self.capacity_observations.get(key)
                if cap and sum(self.hands.values())>cap['count']:self.capacity_observations.pop(key);self.rule_revision+=1
            if a.startswith('enter ') and 'door is locked' in text:
                key=compact([self.epoch,old_loc,p[1]]);self.locks[key]={'locked':True,'step':self.step,'tools_at_failure':dict(old_hands)}
            if a.startswith(('enter ','lockpick ')) and not denied and ('unlock' in text.lower() or self.location!=old_loc):
                self.locks.pop(compact([self.epoch,old_loc,p[1]]),None)
            tool=re.search(r'No ([\w_]+) tool in hand',text)
            if tool:
                if self.held_tools.get(p[0],{}).get('object')!=tool[1]:self.rule_revision+=1
                self.held_tools[p[0]]={'object':tool[1],'step':self.step}
            if a.startswith('take out ') and 'not found in ' in text and len(p)==4:
                self.track_container(p[3])['items'].pop(p[2],None)
            if old_vis is False and not denied and a.startswith('pick up ') and 'I picked up ' in text:
                key=compact([self.epoch,old_loc,'dark_pickup',a[8:]])
                if key not in self.operation_evidence:self.rule_revision+=1
                self.operation_evidence[key]={'kind':'dark_pickup','object':a[8:],'location':old_loc,'step':self.step,'support':'confirmed in this context'}
            probe=before.get('probe')
            if probe:
                outcome='supported_in_context' if ('successfully crafted' in text or 'I picked up ' in text) and not denied else 'failure_or_other_precondition' if denied else 'unresolved'
                if denied and 'Missing necessary' in text:outcome='indeterminate_other_precondition'
                if self.life!=old_life or self.epoch!=old_epoch:outcome='indeterminate_context_changed'
                record={**probe,'after_step':self.step,'outcome':outcome,'feedback':self.current_denials[:2]}
                self.probes[probe['signature']]=record;self.probe_results.append(record)
                if outcome=='supported_in_context':self.operation_evidence[probe['signature']]={'kind':probe['kind'],'action':a,'step':self.step,'support':outcome};self.rule_revision+=1
            if self.receipt:
                self.history[-1]['operation_completed']=True;self.history[-1]['operation_receipt']=self.receipt
            # Parent completion runs before partial-inventory reconciliation;
            # re-evaluate the actual result afterwards, never from an action name.
            old_target=before.get('objective_action')
            completed=bool(old_target and before.get('objective_status')=='active' and not denied and self.target_satisfied(old_target) and not before.get('target_already_satisfied'))
            if completed and self.objective and self.objective['action']==old_target:
                self.objective['status']='effect_observed';self.objective_completions.append({'step':self.step,'action':old_target,'receipt':self.receipt,'main_task_completed':False})
                if self.contract:self.contract['status']='effect_observed'
                self.last_dependency_progress=self.step
            if self.life!=old_life or self.epoch!=old_epoch:
                self.committed=[];self.plan_origin=None
                if self.contract:self.contract['status']='requires_revalidation_after_loss'
            elif denied:
                if self.plan_origin:self.failed_plans[self.plan_origin['key']]={'step':self.step,'reason':self.current_denials[:2]}
                self.plan_repairs.append({'step':self.step,'reason':'observed_denial','remaining':old_queue});self.committed=[];self.plan_origin=None
            else:
                self.committed=old_queue
                if self.committed and self.committed[0]==a:self.committed.pop(0)
            # A successful preparatory event need not clear the remaining parent
            # plan. A completed task, changed rules or denial does.
            if self.objective and self.tasks.get(self.objective['goal_id'],{}).get('status')!='open':self.committed=[]
            if self.contract and self.contract['status']=='active':
                context=self.relevant_context();seen=self.contract['seen'];seen[context]=seen.get(context,0)+1
                work=self.work_action() or '';deficit=sum(self.deficit_vector(work).values());best=self.contract['best_deficit']
                # An empty deficit vector is not proof of progress on a non-resource goal.
                if not self.needed(work):deficit=None
                if deficit is not None and (best is None or deficit<best):self.contract['best_deficit']=deficit;self.last_dependency_progress=self.step
                if seen[context]>=3 and self.plan_origin:
                    self.failed_plans[self.plan_origin['key']]={'step':self.step,'reason':['no net contract progress on return to relevant state']}
                    self.committed=[];self.plan_origin=None;self.contract['phase']='needs_repair_or_probe'
        # Tutorial completion may use a different capitalization/wording.
        if re.search(r'Tutorial (?:completed|complete[.!])',text,re.I):
            for task in self.tasks.values():
                if task['scope']=='tutorial':task['status']='observed_complete'
        self.failed_plans=dict(list(self.failed_plans.items())[-64:])
        return result

    def work_action(self):
        if not self.objective or self.objective['status']!='active':return None
        a=self.objective['action'];p=parts(a)
        if len(p)==2 and p[0]=='enter' and compact([self.epoch,self.location,p[1]]) in self.locks:
            if 'lockpick' in self.held_tools and not schema_error('lockpick '+p[1],self.schemas):
                tool=self.held_tools['lockpick']['object'];counts,_=self.accessible()
                if self.hands.get(tool,0)>0:return 'lockpick '+p[1]
                return self.acquire_held(tool) or a
        if p and p[0] in self.held_tools:
            tool=self.held_tools[p[0]]['object'];counts,_=self.accessible()
            if not self.hands.get(tool,0):return self.acquire_held(tool) or a
        return a

    def acquire_held(self,tool):
        for cid,c in self.containers.items():
            if c['items'].get(tool,0)>0 and cid in set(self.hands)|set(self.equipped)|set(self.nearby):return f'take out {tool} {cid}'
        if self.nearby.get(tool,0)>0:return 'pick up '+tool
        # Existing observed tools/intermediates precede another manufacture.
        return self.acquire(tool,1,{tool:1})

    def action_check(self,action,goal_id=None,schemas=None):
        c=super().action_check(action,goal_id,schemas);p=parts(action)
        if len(p)==2 and p[0]=='enter':
            lock=self.locks.get(compact([self.epoch,self.location,p[1]]))
            if lock:
                # A new potential key/tool merits one new observation. Incidental
                # inventory differences do not erase an observed locked edge.
                new_tools={v['object'] for v in self.held_tools.values()}
                new_tools.update(o for o in self.hands if re.search(r'key|lockpick',o,re.I))
                changed=any(self.hands.get(o,0)>lock['tools_at_failure'].get(o,0) for o in new_tools)
                if not changed:c['blockers'].append({'kind':'observed_locked_edge','location':self.location,'target':p[1],'evidence_step':lock['step'],'release':'unlock feedback, relevant tool acquisition or world-rule change'})
        return c

    def choose(self,action,reasoning,goal_id=None,test_id=None,check=None):
        super().choose(action,reasoning,goal_id,test_id,check)
        self.pending['life']=self.life;self.pending['objective_status']=self.objective and self.objective['status']
        pred=self.target_predicate(self.pending['objective_action'])
        if pred and pred['kind'] in ['operation_observed','crafted','written']:self.pending['target_already_satisfied']=False
        self.pending['probe']=self.next_probe if self.next_probe and self.next_probe['action']==action else None
        self.next_probe=None

    def _resource_state(self):
        return {'hands':dict(self.hands),'equipped':dict(self.equipped),'ground':dict(self.nearby),'bags':{k:dict(v['items']) for k,v in self.containers.items()},'loc':self.location}

    @staticmethod
    def _available(st):
        out=Counter(st['hands'])
        for cid in set(st['hands'])|set(st['equipped']):out.update(st['bags'].get(cid,{}))
        return out

    def _transition(self,st,action):
        s=copy.deepcopy(st);p=parts(action);h=s['hands'];g=s['ground'];eq=s['equipped'];bags=s['bags'];reason=None
        cap=self.capacity_bound(s['loc'],eq);limit=cap['count'] if cap else None
        def remove(d,o,n=1):
            if d.get(o,0)<n:return False
            d[o]-=n
            if d[o]<=0:d.pop(o,None)
            return True
        def room():return limit is None or sum(h.values())+1<=limit
        if action.startswith('pick up '):
            o=action[8:]
            if g.get(o,0)<=0:return None,'unobserved_ground_item'
            if not room():return None,'capacity_conflict'
            remove(g,o);h[o]=h.get(o,0)+1
        elif p and p[0]=='drop' and len(p)==2:
            if not remove(h,p[1]):return None,'not_held'
            g[p[1]]=g.get(p[1],0)+1
        elif p and p[0]=='store' and len(p)==4:
            try:n=float(p[1])
            except ValueError:return None,'invalid_amount'
            cid=p[3]
            if cid not in bags or cid not in set(h)|set(eq)|set(g):return None,'container_inaccessible'
            if self.container_limits.get(cid,{}).get('full'):return None,'container_full'
            if p[2] in bags:return None,'container_nesting_unverified'
            if not remove(h,p[2],n):return None,'not_held'
            bags[cid][p[2]]=bags[cid].get(p[2],0)+n
        elif p[:2]==['take','out'] and len(p)==4:
            if p[3] not in set(h)|set(eq)|set(g):return None,'container_inaccessible'
            if not room():return None,'capacity_conflict'
            if not remove(bags.get(p[3],{}),p[2]):return None,'contents_unverified'
            h[p[2]]=h.get(p[2],0)+1
        elif p and p[0]=='equip' and len(p)==2:
            if p[1] not in bags or p[1] in self.known_non_equippable:return None,'equip_unverified_or_refuted'
            if not remove(h,p[1]):return None,'not_held'
            eq[p[1]]=eq.get(p[1],0)+1
        elif p and p[0]=='enter' and len(p)==2:
            dest=self.routes.get(s['loc'],{}).get(action)
            if not dest:return None,'route_outcome_unverified'
            s['loc']=dest;s['ground']=dict(self.world.get(dest,{}).get('objects',{}))
        elif p and p[0]=='craft':
            need=self.needed(action);available=self._available(s)
            if not need:return None,'recipe_unverified'
            if any(available.get(o,0)<n for o,n in need.items()):return None,'joint_material_deficit'
            # Predicted crafting effects are never installed as observed facts.
            return s,'terminal_probe_or_execution'
        else:return None,'requires_feedback'
        return s,reason

    def validate_plan(self,seq):
        st=self._resource_state();validated=0;stop=None
        for i,a in enumerate(seq[:8]):
            if self.schemas and schema_error(a,self.schemas):
                stop={'index':i,'action':a,'reason':'invalid_schema','status':'contradicted'};break
            nxt,issue=self._transition(st,a)
            if nxt is None:
                stop={'index':i,'action':a,'reason':issue,'status':'contradicted' if issue in ['capacity_conflict','not_held','joint_material_deficit','container_inaccessible','container_full'] else 'requires_observation'};break
            st=nxt;validated+=1
            if issue:stop={'index':i,'action':a,'reason':issue,'status':'requires_observation'};break
        return {'validated_prefix':validated,'stop':stop,'length':len(seq)}

    def resource_plan(self,action):
        need=self.needed(action)
        if not need or not self.hands_known:return None
        start=self._resource_state();q=deque([(start,[])]);seen=set();nodes=0
        while q and nodes<240:
            st,path=q.popleft();key=compact(st)
            if key in seen:continue
            seen.add(key);nodes+=1;available=self._available(st)
            if all(available.get(o,0)>=n for o,n in need.items()):self.search_nodes+=nodes;return path
            if len(path)>=5:continue
            h=st['hands'];g=st['ground'];eq=st['equipped'];bags=st['bags'];options=[]
            for cid in sorted(bags):
                if cid in h and cid not in self.known_non_equippable:options.append('equip '+cid)
                if cid in g and any(bags[cid].get(o,0)>0 for o in need):options.append('pick up '+cid)
            for o,n in need.items():
                if available.get(o,0)<n and g.get(o,0)>0:options.append('pick up '+o)
            for cid in sorted(bags):
                if cid not in set(h)|set(eq)|set(g):continue
                if self.container_limits.get(cid,{}).get('full'):continue
                for o in sorted(h):
                    if o not in bags:options.append(f'store 1 {o} {cid}')
            if self.capacity_bound(st['loc'],eq):
                for o in sorted(h,key=lambda x:(x in need,x in self.protected_items())):
                    if o not in need and o not in bags:options.append('drop '+o)
            for a in options:
                if schema_error(a,self.schemas):continue
                nxt,why=self._transition(st,a)
                if nxt is not None:q.append((nxt,path+[a]))
        self.search_nodes+=nodes;return None

    def _probe(self,action,kind):
        sig=uid(compact([self.epoch,self.life,self.location,action,self.hands,self.equipped,{k:v['items'] for k,v in self.containers.items() if k in self.hands or k in self.equipped},self.stations.get(parts(action)[-1],{})]))
        if sig in self.probes or len(self.probes)>=16:return None
        return {'action':action,'kind':kind,'signature':sig,'before_step':self.step,'claim':'Test this unresolved operation condition with current public prerequisites; other failures are indeterminate.'}

    def diagnostic_action(self,goal):
        a=self.work_action()
        if not a or not a.startswith('craft ') or self.cost_context()['immediate_risk']:return None
        need=self.needed(a);total,_=self.accessible()
        if not need or any(total.get(o,0)<n for o,n in need.items()):return None
        check=self.action_check(a,goal,self.schemas)
        if check['blockers']:return None
        probe=self._probe(a,'craft_access_and_station')
        if probe:
            self.next_probe=probe
            return a,check,{'step':self.step,'selected':a,'source':'local_discriminating_probe','probe':probe,'rejected':[]}
        return None

    def _plan_key(self,seq):return uid(compact([self.relevant_context(),seq]))

    def _select_plan(self,seq,goal,source):
        check=self.action_check(seq[0],goal,self.schemas)
        if check['blockers']:return None
        self.committed=list(seq);self.queue=list(seq);key=self._plan_key(seq)
        self.plan_origin={'key':key,'step':self.step,'goal':self.objective and self.objective['action']}
        return seq[0],check,{'step':self.step,'selected':seq[0],'source':source,'rejected':[],'plan_key':key}

    def local_action(self,goal):
        self.preparation_authority=None;self.next_probe=None
        if self.new_task or self.local_streak>=6:return None
        probe=self.diagnostic_action(goal)
        if probe:return probe
        if self.cost_context()['immediate_risk']:return None
        if self.committed and not self.current_denials:
            a=self.committed[0];p=parts(a);check=self.action_check(a,goal,self.schemas)
            stable=(self.pending and self.life==self.pending.get('life',self.life))
            if not check['blockers'] and stable:
                c,reason=self._transition(self._resource_state(),a)
                # Darkness predicted by releasing a light source does not revoke
                # an explicit remembered-pickup probe in a committed plan.
                if a.startswith('pick up ') and self.visibility is False:
                    obj=a[8:];remembered=self.world.get(self.location,{}).get('objects',{}).get(obj,0)>0
                    probe=self._probe(a,'remembered_pickup_without_visibility') if remembered else None
                    if probe and (not self.capacity_bound() or sum(self.hands.values())<self.capacity_bound()['count']):
                        self.next_probe=probe;return a,check,{'step':self.step,'selected':a,'source':'local_committed_probe','probe':probe,'rejected':[]}
                elif c is not None and reason is None:
                    return a,check,{'step':self.step,'selected':a,'source':'local_contract_continuation','rejected':[]}
        work=self.work_action()
        if work and work.startswith('craft '):
            seq=self.resource_plan(work)
            if seq:
                seq=seq+[work]
                if self._plan_key(seq) not in self.failed_plans:
                    return self._select_plan(seq,goal,'local_resource_plan')
        # Retain the higher-level destination while acquiring its observed tool.
        if work and self.objective and work!=self.objective['action'] and not self.cost_context()['immediate_risk']:
            c=self.action_check(work,goal,self.schemas);nxt,reason=self._transition(self._resource_state(),work)
            if not c['blockers'] and nxt is not None and reason is None:
                return self._select_plan([work],goal,'local_contract_dependency')
            if reason=='capacity_conflict':
                prep=self.free_hand({parts(work)[-1]:1});seq=[prep,work] if prep else []
                if seq and self.validate_plan(seq)['stop'] is None and self._plan_key(seq) not in self.failed_plans:
                    return self._select_plan(seq,goal,'local_capacity_repair')
        return None

    def dispatch(self,candidates,goal):
        rejected=[];accepted=[]
        for x in candidates[:3]:
            seq=x.get('actions',[]) if isinstance(x,dict) else []
            seq=[a for a in seq[:8] if isinstance(a,str) and a.strip()]
            if not seq:continue
            check=self.action_check(seq[0],goal,self.schemas);validation=self.validate_plan(seq);key=self._plan_key(seq)
            self.plan_checks.append({'step':self.step,'actions':seq,'validation':validation})
            if key in self.failed_plans:
                rejected.append({'action':seq[0],'source':'failed_strategy','blockers':[{'kind':'same_failed_plan_context','detail':self.failed_plans[key]}]});continue
            if check['blockers']:
                rejected.append({'action':seq[0],'source':'candidate','blockers':check['blockers']});continue
            stop=validation['stop']
            if stop and stop['status']=='contradicted':
                rejected.append({'action':seq[0],'source':'joint_plan_check','blockers':[{'kind':'future_plan_conflict','detail':stop}]});continue
            terminal=self.work_action();need=self.needed(terminal or '')
            # Candidate paths must not immediately destroy usable task inputs
            # when an informative terminal attempt is already available.
            total,_=self.accessible();ready=bool(need) and all(total.get(o,0)>=n for o,n in need.items())
            undo=seq[0].startswith(('drop ','store ','take out ')) and ready and terminal and terminal.startswith('craft ')
            uncertainty=1 if stop else 0;risk=self.cost_context()['observed_damage_per_step']*len(seq)
            accepted.append((int(undo),uncertainty,risk,len(accepted),seq))
        if accepted:
            _,_,_,_,seq=min(accepted,key=lambda x:x[:4]);selection=self._select_plan(seq,goal,'checked_model_plan')
            if selection:
                a,c,d=selection;d['rejected']=rejected;self.interventions.append(d);return a,c,d
        self.committed=[];self.queue=[]
        return None,None,{'step':self.step,'selected':None,'source':'no_jointly_admissible_plan','rejected':rejected}

    def trigger(self):
        if self.reviews>=min(30,1+self.step//12) or self.step-self.last_review<8:return None
        if self.new_task:return 'task_changed'
        if self.current_denials:return 'operation_failure_requires_local_repair'
        if self.contract and self.contract.get('phase')=='needs_repair_or_probe':return 'stalled_strategy_requires_changed_condition'
        if self.step-self.last_review>=18:return 'contract_review'
        return None

    def mechanism_packet(self):
        contract={k:v for k,v in (self.contract or {}).items() if k!='seen'}
        return {'contract':contract,'committed_remaining':self.committed,'operation_receipt':self.receipt,
          'current_work_action':self.work_action(),'local_capacity_estimate':self.capacity_bound(),
          'locked_edges':self.locks,'operation_evidence':list(self.operation_evidence.values())[-6:],
          'last_probe_results':self.probe_results[-3:],'recent_failed_plans':list(self.failed_plans.values())[-3:],
          'last_joint_plan_check':self.plan_checks[-1:] ,'risk':self.cost_context(),
          'completion_count':len(self.objective_completions),'probe_count':len(self.probes),'repair_count':len(self.plan_repairs),'search_nodes':self.search_nodes}

    def packet(self):
        p=super().packet();p['v3r3_mechanisms']=self.mechanism_packet();return p

    def to_dict(self):
        p=super().to_dict();p['v3r3_audit']={'completions':self.objective_completions,'probes':self.probe_results,'evidence':self.operation_evidence,'failed_plans':self.failed_plans,'plan_checks':self.plan_checks,'repairs':self.plan_repairs,'rejected_objectives':self.rejected_objectives};return p
