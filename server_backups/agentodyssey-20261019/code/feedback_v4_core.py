"""Evidence-scoped constraints and revisable execution. Public observations only."""
import copy,re
try:
    from .mechanism_study_core import StudyLedger
    from .feedback_v3_core import parts
    from .feedback_v2_core import compact,uid
except ImportError:
    from mechanism_study_core import StudyLedger
    from feedback_v3_core import parts
    from feedback_v2_core import compact,uid

class Ledger(StudyLedger):
    def __init__(self,disabled=None):
        super().__init__(disabled)
        self.life_generation=0;self.hands_observed=False;self.equipment_observed=False
        self.negative_capabilities={};self.constraint_updates=[];self.fresh_decision_required=False

    def state_key(self):
        return uid(compact({'observed_state':super().state_key(),'life':self.life_generation}))

    def accessible(self):
        total,unknown=super().accessible()
        if not self.hands_observed:unknown=list(unknown)+['unreported_current_hand_inventory']
        return total,unknown

    def evaluate_predicate(self,p):
        if p.get('kind')=='held' and not self.hands_observed:return 'unknown'
        if p.get('kind')=='equipped' and not self.equipment_observed:return 'unknown'
        return super().evaluate_predicate(p)

    def capacity_applies(self,action):
        c=self.hand_limit
        return bool(c and self.hands_observed and c.get('count',0)>0 and c.get('epoch')==self.epoch
            and c.get('life')==self.life_generation and c.get('location')==self.location
            and c.get('hands')==self.hands and c.get('equipment')==self.equipped
            and c.get('attempted_action')==action)

    def advance(self,text):
        before=copy.deepcopy(self.pending);prior_location=self.location;old_epoch=self.epoch
        prior_hands=dict(self.hands);prior_equipped=dict(self.equipped)
        prior_fresh=self.hands_observed;prior_limit=copy.deepcopy(self.hand_limit)
        reset='I revived at the starting point' in text or 'I have died.' in text
        self.hands_observed=bool(re.search(r'^\s*I am holding ',text,re.M))
        self.equipment_observed=bool(re.search(r'^\s*I have equipped ',text,re.M))
        if reset:self.life_generation+=1
        result=super().advance(text)
        rewritten=self.epoch!=old_epoch
        if reset or rewritten:
            self.hand_limit=None;self.container_limits={};self.queue=[]
            self.constraint_updates.append({'step':self.step,'kind':'operational_constraints_invalidated','reason':'life_reset' if reset else 'explicit_world_rewrite'})
            if rewritten:self.negative_capabilities={};self.inspections={}
        elif before and 'not enough space in hand' in text:
            # A refusal does not reveal a universal item-count limit, especially in darkness.
            if prior_fresh and self.hands_observed and sum(prior_hands.values())>0 and prior_hands==self.hands and prior_location==self.location:
                self.hand_limit={'count':sum(prior_hands.values()),'hands':prior_hands,'equipment':prior_equipped,
                    'location':self.location,'life':self.life_generation,'epoch':self.epoch,'step':self.step,
                    'attempted_action':before['action'],'scope':'same attempted pickup and observed load/context only','evidence':self.ref(text)}
            else:
                self.hand_limit=prior_limit
                self.constraint_updates.append({'step':self.step,'kind':'capacity_refusal_indeterminate','reason':'hand state unreported, changed, or zero; no capacity inferred'})
        if self.hand_limit and (self.hand_limit.get('location')!=self.location or self.hand_limit.get('hands')!=self.hands or self.hand_limit.get('equipment')!=self.equipped):self.hand_limit=None
        if before:
            ps=parts(before['action'])
            if len(ps)==2 and ps[0]=='equip' and re.search(r'not (?:an? )?equippable',text,re.I):
                self.negative_capabilities[ps[1]]={'operation':'equip','epoch':self.epoch,'evidence':self.ref(text)}
            if before['action'].startswith('pick up ') and 'I picked up ' in text:self.hand_limit=None
        invalid=self.objective and self.objective.get('status')=='active' and self.objective_invalid(self.objective['action'],self.objective['goal_id'])
        if invalid:self.objective['status']='contradicted_by_observation';self.queue=[]
        if reset and self.objective and self.objective['status']=='active':self.objective['status']='requires_revalidation_after_reset'
        # A raw safety change or new task invalidates a committed path, not the task itself.
        self.fresh_decision_required=bool(reset or rewritten or invalid or self.new_task or self.visibility is False or re.search(r'I was attacked by .+ and lost \d+ HP',text))
        if self.fresh_decision_required:self.queue=[]
        return result

    def objective_invalid(self,action,goal):
        if self.target_predicate(action) is None:return True
        p=parts(action)
        if len(p)==2 and p[0]=='equip' and p[1] in self.negative_capabilities:return True
        check=super().action_check(action,goal,self.schemas)
        return any(x['kind']=='task_parameter_mismatch' for x in check['blockers']+check['warnings'])

    def install_objective(self,action,goal,reason='',evidence=None):
        if not isinstance(action,str):return False
        if self.objective_invalid(action,goal):
            self.objective_rejections.append({'step':self.step,'requested':action,'reason':'objective lacks an observable effect predicate or contradicts observed task/capability'})
            return False
        if self.objective and self.objective['status']=='active' and self.objective_invalid(self.objective['action'],self.objective['goal_id']):
            self.objective['status']='contradicted_by_observation';self.queue=[]
        return super().install_objective(action,goal,reason,evidence)

    def pickup(self,obj,needed=None):
        action='pick up '+obj
        if self.capacity_applies(action):return self.free_hand(needed)
        return action

    def action_check(self,action,goal_id=None,schemas=None):
        check=super().action_check(action,goal_id,schemas);kept=[]
        for b in check['blockers']:
            if b['kind']=='observed_hand_capacity' and not self.capacity_applies(action):
                check['unknown'].append(dict(b,reason='conditional capacity evidence does not apply'));continue
            if b['kind'] in ['quantity_deficit','station_not_currently_observed'] and (not self.hands_observed or self.visibility is False):
                check['unknown'].append(dict(b,reason='current prerequisite state is partially unobserved'));continue
            if b['kind']=='repeated_context_action' and action.startswith('enter '):
                prior=[r for r in self.action_records if r['context']==self.state_key() and r['action']==action]
                if prior and not any(r['denied'] for r in prior):
                    check['warnings'].append(dict(b,reason='successful navigation can be reused; evaluate net task progress'));continue
            kept.append(b)
        check['blockers']=kept
        p=parts(action)
        if len(p)==2 and p[0]=='equip' and p[1] in self.negative_capabilities:
            check['blockers'].append({'kind':'observed_non_equippable','object':p[1],'detail':self.negative_capabilities[p[1]]})
        return check

    def dispatch(self,candidates,goal_id):
        if not self.fresh_decision_required:return super().dispatch(candidates,goal_id)
        # Fresh proposals first after safety/task/context changes; automatic preparations remain fallbacks.
        saved=self.disabled;self.disabled=saved|{'dependency_execution'}
        try:result=super().dispatch(candidates,goal_id)
        finally:self.disabled=saved
        if result[0] is None:result=super().dispatch(candidates,goal_id)
        return result

    def packet(self):
        p=super().packet();p['inventory_observation_status']={'hands_reported_now':self.hands_observed,'equipment_reported_now':self.equipment_observed,'life_generation':self.life_generation}
        p['negative_object_capabilities']=self.negative_capabilities;p['recent_constraint_revisions']=self.constraint_updates[-6:]
        p['fresh_decision_required']=self.fresh_decision_required
        p['semantics']+=' Unreported hand inventory is uncertain. A capacity refusal is scoped to its attempted action and observed load, location and life. Successful navigation may be repeated; an unchanged failed action still needs new evidence. Unsupported objectives do not become persistent commitments.'
        return p
