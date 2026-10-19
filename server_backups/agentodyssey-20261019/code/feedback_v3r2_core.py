"""v3-derived execution authority is conditional on public evidence.

Small revision of v3r: observed effects are not universal action requirements;
existing products precede manufacturing, and fresh decisions are not silently
overridden by speculative preparation. No benchmark entities or oracle state.
"""
import copy,re
try:
    from .feedback_v3r_core import Ledger as Previous
    from .feedback_v3_core import parts
except ImportError:
    from feedback_v3r_core import Ledger as Previous
    from feedback_v3_core import parts

class Ledger(Previous):
    def __init__(self):
        super().__init__();self.last_visits={};self.preparation_authority=None
    def advance(self,text):
        before=copy.deepcopy(self.pending);prior_location=self.location
        result=super().advance(text)
        self.last_visits[self.location]={'step':self.step,'visibility':self.visibility}
        if self.location in self.world:
            record=self.world[self.location]
            record['last_visit_step']=self.step;record['visibility_at_last_visit']=self.visibility
            record['object_list_currently_observed']=self.visibility is True
        # Confirmed local changes update the last observed ground inventory even
        # when the current room no longer provides a complete visual inventory.
        if before and self.visibility is not True and self.location==prior_location:
            action=before['action'];world=self.world.get(self.location)
            if world:
                ground=world['objects']
                if action.startswith('pick up ') and 'I picked up ' in text:
                    obj=action[8:];ground[obj]=max(0,ground.get(obj,0)-1)
                elif action.startswith('drop ') and 'I dropped ' in text:
                    obj=action[5:];ground[obj]=ground.get(obj,0)+1
                elif action.startswith('pick up ') and 'not found in current area' in text:ground.pop(action[8:],None)
                for m in re.finditer(r'I successfully crafted (\d+) ([\w_]+).*?on the ground',text):
                    ground[m[2]]=ground.get(m[2],0)+int(m[1])
        return result
    def action_check(self,action,goal_id=None,schemas=None):
        check=super().action_check(action,goal_id,schemas);kept=[]
        for b in check['blockers']:
            if b['kind']=='breaks_observed_visibility_support':
                check['warnings'].append({**b,'reason':'Observed visibility may be lost. This is not proof that the next planned operation requires visibility; decide the tradeoff and test using actual feedback.'})
            else:kept.append(b)
        check['blockers']=kept
        return check
    def free_hand(self,needed=None):
        # Preserve target ingredients before preserving an unproven operational
        # prerequisite. A model may instead choose a container or another room.
        needed=needed or {};container=self.available_container()
        for obj in self.hands:
            if obj in self.containers and obj not in self.known_non_equippable:return 'equip '+obj
        candidates=sorted(self.hands,key=lambda o:(o in needed,o in self.protected_items(),o))
        if container:
            obj=next((o for o in candidates if o!=container),None)
            if obj:return f'store 1 {obj} {container}'
        return 'drop '+candidates[0] if candidates else None
    def acquire(self,obj,n,needed,visited=None):
        # A known finished/intermediate object elsewhere is a candidate source
        # BEFORE recursively manufacturing it from raw ingredients.
        total,_=self.accessible()
        if total.get(obj,0)>=n:return None
        if obj in set(visited or []):return None
        if self.nearby.get(obj,0)>0:return self.pickup(obj,needed)
        for cid,c in self.containers.items():
            if c['items'].get(obj,0)>0 and cid in self.nearby and cid not in self.hands and cid not in self.equipped:return self.pickup(cid,needed)
        sources=sorted(self.world.items(),key=lambda kv:(kv[0]!=self.location,-kv[1]['step']))
        for loc,record in sources:
            if record['epoch']!=self.epoch or record['objects'].get(obj,0)<=0:continue
            if loc==self.location:return self.pickup(obj,needed) # remembered position; certificate will mark uncertainty
            route=self.route_to(loc)
            if route:return route
        return super().acquire(obj,n,needed,visited)
    def preparation_certificate(self,action,goal,source):
        problems=[];check=self.action_check(action,goal,self.schemas);ps=parts(action)
        if self.invalidate_plan:problems.append('context_reset_or_dependency_changed')
        if self.loop:problems.append('net_state_recurrence_requires_fresh_decision')
        if self.current_denials:problems.append('previous_action_denied')
        if check['blockers']:problems.append('contradicted_precondition')
        if check['unknown']:problems.append('unverified_precondition')
        if check['warnings']:problems.append('tradeoff_requires_fresh_decision')
        grounded=False
        if len(ps)==2 and ps[0]=='enter':
            # Neighboring-room existence proves travel format/path, not that
            # a historic resource is still accessible there.
            grounded=source=='committed_short_plan' and ps[1] in self.neighbors
        elif action.startswith('pick up '):grounded=self.visibility is True and self.nearby.get(action[8:],0)>0 and self.hands_known
        elif ps and ps[0] in ['craft','equip','store']:
            grounded=self.hands_known and self.visibility is True
        if not grounded:problems.append('no_current_execution_witness')
        if self.objective and len(ps)==2 and ps[0]=='drop' and ps[1] in self.dependency_requirements(self.objective['action']):problems.append('removes_required_input_without_joint_plan')
        return {'action':action,'source':source,'authorized':not problems,'reasons':problems,'step':self.step},check
    def local_action(self,goal):
        self.preparation_authority=None
        if self.local_streak>=3 or self.new_task:return None
        options=[]
        if self.queue:options.append(('committed_short_plan',self.queue[0]))
        prep=self.preparation()
        if prep:options.append(('dependency_preparation',prep))
        for source,action in options:
            certificate,check=self.preparation_certificate(action,goal,source);self.preparation_authority=certificate
            if certificate['authorized']:
                return action,check,{'step':self.step,'selected':action,'source':'local_'+source,'rejected':[],'certificate':certificate}
        return None
    def dispatch(self,candidates,goal_id):
        # This path is reached AFTER a fresh model call. Do not pay for a
        # correction and then overwrite it with the speculative plan it corrects.
        rejected=[]
        for x in candidates[:3]:
            seq=x.get('actions',[]) if isinstance(x,dict) else []
            seq=[a for a in seq[:6] if isinstance(a,str) and a.strip()] if isinstance(seq,list) else []
            if not seq:continue
            check=self.action_check(seq[0],goal_id,self.schemas)
            if check['blockers']:
                rejected.append({'action':seq[0],'source':'fresh_model_candidate','blockers':check['blockers']});continue
            self.queue=seq
            record={'step':self.step,'selected':seq[0],'source':'fresh_model_candidate','rejected':rejected};self.interventions.append(record)
            return seq[0],check,record
        # A certified local preparation remains a bounded fallback; unsupported
        # candidates are handled by the inherited non-terminating recovery.
        prep=self.preparation()
        if prep:
            certificate,check=self.preparation_certificate(prep,goal_id,'dependency_preparation');self.preparation_authority=certificate
            if certificate['authorized']:
                self.queue=[prep];record={'step':self.step,'selected':prep,'source':'certified_preparation_after_rejection','rejected':rejected,'certificate':certificate};self.interventions.append(record)
                return prep,check,record
        self.queue=[]
        return None,None,{'step':self.step,'selected':None,'source':'no_admissible_candidate','rejected':rejected}
    def packet(self):
        p=super().packet();p['execution_authority']=self.preparation_authority;p['last_location_visits']=self.last_visits
        return p
