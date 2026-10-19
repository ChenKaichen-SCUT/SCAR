"""v3 revision: reconcile partial observations and preserve enabling conditions.

Only public observations and declared action schemas are consumed. No game
names, entity lists, reward, hidden configuration or baseline traces are read.
"""
import copy,json,re
from collections import Counter
try:
    from .feedback_v3_core import Ledger as V3,parts
    from .feedback_v2_core import counts,compact,uid,schema_error
except ImportError:
    from feedback_v3_core import Ledger as V3,parts
    from feedback_v2_core import counts,compact,uid,schema_error

class Ledger(V3):
    def __init__(self):
        super().__init__();self.life=0;self.hands_known=False;self.equipment_known=False
        self.known_non_equippable={};self.enablers={};self.visibility_snapshots={}
        self.reconciliations=[];self.invalidate_plan=False;self.local_streak=0
        self.seen_acquired=set();self.failed_probes={};self.last_rejection=None

    def state_key(self):return uid(compact({'state':super().state_key(),'life':self.life,'hands_known':self.hands_known,'equipment_known':self.equipment_known}))
    def accessible(self):
        total,unknown=super().accessible()
        if not self.hands_known:unknown=list(unknown)+['unreported_or_ambiguous_hand_inventory']
        return total,unknown
    def evaluate_predicate(self,p):
        if p.get('kind')=='held' and not self.hands_known:return 'unknown'
        if p.get('kind')=='equipped' and not self.equipment_known:return 'unknown'
        return super().evaluate_predicate(p)

    def advance(self,text):
        before=copy.deepcopy(self.pending);old_hands=dict(self.hands);old_equipped=dict(self.equipped)
        old_known=self.hands_known;old_eq_known=self.equipment_known;old_location=self.location
        old_visible=self.visibility;old_limit=copy.deepcopy(self.hand_limit);old_epoch=self.epoch
        old_objective=copy.deepcopy(self.objective)
        reset='I revived at the starting point' in text or 'I have died.' in text
        raw_hands=bool(re.search(r'^\s*I am holding ',text,re.M));raw_equipped=bool(re.search(r'^\s*I have equipped ',text,re.M))
        self.hands_known=raw_hands or old_known;self.equipment_known=raw_equipped or old_eq_known
        if reset:self.life+=1
        result=super().advance(text)
        self.invalidate_plan=reset or self.epoch!=old_epoch
        action=before['action'] if before else '';ps=parts(action)
        inferred=Counter(old_hands);eq=Counter(old_equipped)
        known=old_known;eq_known=old_eq_known
        def remove(obj,n=1):
            nonlocal known
            if inferred.get(obj,0)<n:known=False
            inferred[obj]=max(0,inferred.get(obj,0)-n)
        if reset:
            inferred.clear();eq.clear();known=eq_known=True
            self.hand_limit=None;self.container_limits={};self.capacity=None;self.queue=[]
            if self.objective and self.objective['status']=='active':self.objective['status']='requires_revalidation_after_loss'
        elif before and not self.current_denials:
            if action.startswith('pick up ') and 'I picked up ' in text:
                inferred[action[8:]]+=1;self.seen_acquired.add(action[8:])
            elif action.startswith('drop ') and 'I dropped ' in text:remove(action[5:])
            elif len(ps)==4 and ps[0]=='store' and 'I stored ' in text:
                try:remove(ps[2],float(ps[1]))
                except ValueError:known=False
            elif len(ps)==4 and ps[:2]==['take','out'] and 'I took out ' in text:inferred[ps[2]]+=1
            elif len(ps)==2 and ps[0]=='equip' and 'I equipped ' in text:
                remove(ps[1]);eq[ps[1]]+=1;eq_known=False
            elif len(ps)==2 and ps[0]=='unequip' and 'I unequipped ' in text:
                inferred[ps[1]]+=1;eq[ps[1]]=max(0,eq[ps[1]]-1)
            elif len(ps)==2 and ps[0]=='eat' and 'from hand' in text:remove(ps[1])
            elif action.startswith('craft ') and 'successfully crafted' in text:
                recipe=self.recipes.get(ps[-1],{}).get('ingredients')
                carriers=[x for x in set(old_hands)|set(old_equipped) if x in self.containers]
                if recipe and not carriers and len(ps)==3 and ps[1].isdigit():
                    for obj,n in recipe.items():remove(obj,n*int(ps[1]))
                else:
                    known=False
                    for obj in recipe or []:inferred.pop(obj,None)
            elif action.startswith(('sell ','throw ','invoke ','buy ')):known=False
            if 'I used a key to unlock' in text:known=False
        if 'SEIZED!' in text or 'confiscate' in text.lower():inferred.clear();known=False
        if not raw_hands:self.hands={k:v for k,v in inferred.items() if v>0};self.hands_known=known
        if not raw_equipped:self.equipped={k:v for k,v in eq.items() if v>0};self.equipment_known=eq_known
        if reset and not raw_hands:self.hands={};self.hands_known=True
        if reset and not raw_equipped:self.equipped={};self.equipment_known=True
        if self.epoch!=old_epoch:self.known_non_equippable={};self.enablers={};self.visibility_snapshots={};self.hand_limit=None;self.failed_probes={}
        if not reset and self.epoch==old_epoch and 'not enough space in hand' in text:
            if before and old_known and sum(old_hands.values())>0 and old_location==self.location:
                self.hand_limit={'count':sum(old_hands.values()),'hands':old_hands,'equipped':old_equipped,'location':old_location,'life':self.life,'epoch':self.epoch,'action':action,'step':self.step,'evidence':self.ref(text)}
            else:self.hand_limit=old_limit;self.reconciliations.append({'step':self.step,'event':'capacity_refusal_not_identifiable'})
        if before and len(ps)==2 and ps[0]=='equip' and 'not equippable' in text:
            self.known_non_equippable[ps[1]]={'step':self.step,'evidence':self.ref(text),'epoch':self.epoch}
        if before and self.current_denials:
            self.failed_probes[action]={'step':self.step,'context':self.state_key(),'denials':self.current_denials[:2]}
        if self.hands_known:
            self.seen_acquired.update(self.hands)
        # Learn a maintenance condition from a visible->dark intervention in the same room.
        removed=None
        if len(ps)==2 and ps[0]=='drop':removed=ps[1]
        if len(ps)==4 and ps[0]=='store':removed=ps[2]
        if removed and not reset and old_location==self.location and old_visible is True and self.visibility is False and old_hands.get(removed,0)>0 and not self.hands.get(removed):
            self.enablers[(self.location,removed)]={'location':self.location,'object':removed,'kind':'held_visibility_support','evidence':self.ref(text),'confidence':'observed local intervention, revisable','epoch':self.epoch}
            self.invalidate_plan=True
        previous=self.visibility_snapshots.get(self.location)
        if previous and previous['visible'] is False and self.visibility is True and self.hands_known and previous['hands_known']:
            added=[o for o in self.hands if self.hands[o]>previous['hands'].get(o,0)]
            if len(added)==1:
                self.enablers[(self.location,added[0])]={'location':self.location,'object':added[0],'kind':'held_visibility_support','evidence':self.ref(text),'confidence':'paired local observations, not universal proof','epoch':self.epoch}
        if self.visibility is not None:self.visibility_snapshots[self.location]={'visible':self.visibility,'hands':dict(self.hands),'hands_known':self.hands_known,'step':self.step}
        if self.hand_limit and (self.hand_limit.get('life')!=self.life or self.hand_limit.get('epoch')!=self.epoch):self.hand_limit=None
        if self.objective:
            op=parts(self.objective['action'])
            if len(op)==2 and op[0]=='equip' and op[1] in self.known_non_equippable:
                self.objective['status']='contradicted_capability';self.invalidate_plan=True
        if self.invalidate_plan:self.queue=[]
        # Recompute audit conclusions against reconciled state, not a temporarily stale inventory.
        if before and self.history:
            h=self.history[-1];vector=self.deficit_vector(before.get('objective_action',''))
            h['dependency_deficits_after']=vector
            h['dependency_deficit_reduced']=bool(before.get('deficit_vector')) and sum(vector.values())<sum(before['deficit_vector'].values()) and self.hands_known
            h['objective_effect_observed']=bool(not reset and not self.current_denials and self.target_satisfied(before.get('objective_action','')) and not before.get('target_already_satisfied'))
            if old_objective and self.objective and self.objective['status']=='effect_observed' and not h['objective_effect_observed']:self.objective=old_objective
            self.action_records[-1]['after_context']=self.state_key()
            self.action_records[-1]['objective_effect']=h['objective_effect_observed']
        self.reconciliations.append({'step':self.step,'event':'inventory_reconciled','hands_reported':raw_hands,'hands_known':self.hands_known,'reset':reset})
        return result

    def capacity_applies(self,action):
        c=self.hand_limit
        return bool(c and self.hands_known and c.get('count',0)>0 and c.get('action')==action and c.get('life')==self.life and c.get('epoch')==self.epoch and c.get('location')==self.location and c.get('hands')==self.hands and c.get('equipped')==self.equipped)
    def protected_items(self):
        return {o for (loc,o),e in self.enablers.items() if loc==self.location and self.hands.get(o,0)>0 and e['epoch']==self.epoch}
    def free_hand(self,needed=None):
        protected=self.protected_items();needed=needed or {};container=self.available_container()
        for obj in self.hands:
            if obj in self.containers and obj not in self.known_non_equippable:return 'equip '+obj
        objects=sorted((o for o in self.hands if o not in protected),key=lambda o:(o in needed,o))
        if container:
            obj=next((o for o in objects if o!=container),None)
            if obj:return f'store 1 {obj} {container}'
        if objects:return 'drop '+objects[0]
        # Preserve the enabling object; use an observed route to a lit room instead.
        for loc,s in self.visibility_snapshots.items():
            if loc!=self.location and s['visible'] and not s['hands']:
                route=self.route_to(loc)
                if route:return route
        return None
    def pickup(self,obj,needed=None):return self.free_hand(needed) if self.capacity_applies('pick up '+obj) else 'pick up '+obj
    def install_objective(self,action,goal,reason='',evidence=None):
        if isinstance(action,str):
            ps=parts(action)
            if len(ps)==2 and ps[0]=='equip' and ps[1] in self.known_non_equippable:return False
        return super().install_objective(action,goal,reason,evidence)
    def action_check(self,action,goal_id=None,schemas=None):
        check=super().action_check(action,goal_id,schemas);kept=[]
        for b in check['blockers']:
            if b['kind']=='observed_hand_capacity' and not self.capacity_applies(action):continue
            if b['kind']=='station_not_currently_observed' and self.visibility is not True:
                check['unknown'].append(b);continue
            if b['kind']=='repeated_context_action':
                prior=[r for r in self.action_records if r['action']==action and r['context']==self.state_key()]
                if prior and not any(r['denied'] for r in prior):check['warnings'].append(dict(b,reason='successful actions may be necessary again; repetition is not proof of impossibility'));continue
            kept.append(b)
        check['blockers']=kept;ps=parts(action)
        if len(ps)==2 and ps[0]=='equip' and ps[1] in self.known_non_equippable:check['blockers'].append({'kind':'observed_non_equippable','object':ps[1]})
        released=ps[1] if len(ps)==2 and ps[0]=='drop' else ps[2] if len(ps)==4 and ps[0]=='store' else None
        if released in self.protected_items():check['blockers'].append({'kind':'breaks_observed_visibility_support','object':released,'reason':'use a different free-hand preparation or leave the dark room first'})
        return check
    def apply_review(self,r):
        if isinstance(r,dict) and isinstance(r.get('hypotheses'),list):
            r={**r,'hypotheses':[h for h in r['hypotheses'] if isinstance(h,dict) and isinstance(h.get('preconditions',[]),list) and isinstance(h.get('expected',[]),list)]}
        return super().apply_review(r)
    def valid_predicate(self,p):
        if isinstance(p,dict) and p.get('kind')=='task_complete' and not isinstance(p.get('task_id'),str):return False
        if isinstance(p,dict) and p.get('kind')=='visible' and 'object' in p and not isinstance(p['object'],str):return False
        return super().valid_predicate(p)

    def local_action(self,goal):
        if self.local_streak>=3 or self.invalidate_plan or self.new_task or self.current_denials or self.loop:return None
        options=[]
        if self.queue:options.append(('committed_short_plan',self.queue[0]))
        prep=self.preparation()
        if prep:options.append(('dependency_preparation',prep))
        for source,a in options:
            c=self.action_check(a,goal,self.schemas);ps=parts(a)
            if c['blockers'] or c['unknown'] or not ps:continue
            grounded=(len(ps)==2 and ps[0]=='enter' and ps[1] in self.neighbors) or (a.startswith('pick up ') and self.nearby.get(a[8:],0)>0 and self.hands_known) or (ps[0] in ['store','craft','equip'] and self.hands_known and self.visibility is True)
            if grounded:return a,c,{'step':self.step,'selected':a,'source':'local_'+source,'rejected':[]}
        return None
    def recover_action(self,candidates,goal,rejected):
        """Produce a step, never terminate on a rejected batch. No paid retry."""
        options=[];prep=self.preparation()
        if prep:options.append(prep)
        if self.hands_known:
            for obj in self.hands:
                if obj in self.containers:options.append('equip '+obj)
        for x in candidates:
            if isinstance(x,dict) and isinstance(x.get('actions'),list):options.extend(a for a in x['actions'] if isinstance(a,str))
        options += ['enter '+n for n in self.neighbors]
        options += ['inspect '+o for o in sorted(set(self.hands)|set(self.nearby)) if (o,self.inspection_versions.get(o,0)) not in self.inspections]
        seen=set();ranked=[]
        for a in options:
            if a in seen or schema_error(a,self.schemas):continue
            seen.add(a);c=self.action_check(a,goal,self.schemas)
            if c['blockers']:continue
            repeats=sum(r['action']==a and r['context']==self.state_key() for r in self.action_records[-24:])
            ranked.append((repeats,len(c['unknown']),len(ranked),a,c))
        if ranked:
            _,_,_,action,check=min(ranked);source='local_recovery_after_rejected_batch'
        else:
            # A recurrence heuristic cannot permanently seal all physical exits.
            relaxed=[]
            for a in ['enter '+n for n in self.neighbors]+list(seen):
                c=self.action_check(a,goal,self.schemas)
                if c['blockers'] and all(b['kind'] in ['repeated_context_action','inspection_has_no_new_question'] for b in c['blockers']):
                    relaxed.append((sum(r['action']==a for r in self.action_records[-24:]),a,c))
            if relaxed:
                _,action,check=min(relaxed,key=lambda x:(x[0],x[1]));check['warnings']+=check['blockers'];check['blockers']=[];source='explicit_recurrence_heuristic_relaxation'
            else:
                action=next((v for v,p in self.schemas if not p and v in ['defend','wait']),None)
                if action is None:raise RuntimeError('Declared interface has no parameter-free recovery action')
                check=self.action_check(action,goal,self.schemas);source='no_grounded_alternative_recorded'
        self.queue=[];record={'step':self.step,'selected':action,'source':source,'rejected':rejected};self.interventions.append(record);self.last_rejection=record
        return action,check,record
    def packet(self):
        p=super().packet();p['belief_status']={'hands_known':self.hands_known,'equipment_known':self.equipment_known,'life':self.life}
        p['visibility_supports']=list(self.enablers.values());p['non_equippable']=self.known_non_equippable;p['latest_reconciliation']=self.reconciliations[-1:] if self.reconciliations else []
        p['unknown_recipe_frontier']=[{'product':k,'ingredients':v['ingredients'],'new_product_not_acquired':k not in self.seen_acquired} for k,v in self.recipes.items() if k not in self.seen_acquired]
        return p
