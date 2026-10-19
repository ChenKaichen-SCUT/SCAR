"""Narrow hypothesis candidate: progress scoped to an observed emergency.

Resource-state identity and resource-loop detection are intentionally unchanged.
Only attack/eat responses to observed threat or injury use a separate progress
record. No reward, entity names, environment internals, model calls or new planner.
"""
import copy,re
try:
    from .feedback_v3r4_core import Ledger as Previous
    from .feedback_v3_core import parts
    from .feedback_v2_core import compact,uid
except ImportError:
    from feedback_v3r4_core import Ledger as Previous
    from feedback_v3_core import parts
    from feedback_v2_core import compact,uid

NO_RESOURCE_PROGRESS='no net contract progress on return to relevant state'
class Ledger(Previous):
    def __init__(self):
        super().__init__();self.init_emergency_fields()

    def init_emergency_fields(self):
        self.threats={};self.observed_max_hp=None;self.emergency_progress=[]
        self.emergency_contract=None;self.emergency_checks=[];self.emergency_streaks={}

    def observe_threats(self,text,old_location,old_life):
        if self.location!=old_location or self.life!=old_life:
            self.threats={};self.emergency_contract=None;self.emergency_streaks={}
        if self.life!=old_life:return
        # These are public feedback formats. Silence alone is not a victory.
        for m in re.finditer(r'^(\w+) (?:has engaged in combat|is attacking|is defending|is waiting)\.',text,re.M):
            self.threats.setdefault(m[1],{}).update(step=self.step,stance=m[0])
        for pattern in [r'I was attacked by (\w+) and lost [\d.]+ HP',r'(\w+) has blocked the way out']:
            for m in re.finditer(pattern,text):self.threats.setdefault(m[1],{}).update(step=self.step)
        for m in re.finditer(r'(\w+) has ([\d.]+) HP remaining',text):
            self.threats.setdefault(m[1],{}).update(step=self.step,hp=float(m[2]))
        for m in re.finditer(r'\bdefeated (\w+)!',text):self.threats.pop(m[1],None)
        if re.search(r'I see .* nearby\.',text):
            self.threats={k:v for k,v in self.threats.items() if k in self.current_npcs}
        for m in re.finditer(r'\bHP:\s*[\d.]+/([\d.]+)',text):self.observed_max_hp=float(m[1])

    def emergency_scope(self,action):
        p=parts(action)
        if len(p)!=2 or p[0] not in ['attack','eat']:return None
        if p[0]=='attack' and p[1] in self.threats:
            return {'kind':'combat','target':p[1],'evidence_step':self.threats[p[1]]['step']}
        if p[0]=='eat':
            injured=self.hp is not None and self.observed_max_hp is not None and self.hp<self.observed_max_hp
            exposed=bool(self.threats) or any(self.area_recent.get(self.location,[]))
            if injured or exposed:return {'kind':'health_recovery','object':p[1],'injury_observed':injured,'threat_observed':exposed}
        return None

    def emergency_key(self,action):
        p=parts(action);threat=self.threats.get(p[1],{})
        # Never add health to the shared resource-loop key. No-effect combat
        # evidence is specific to the observed target stance and equipment.
        relevant={'life':self.life,'epoch':self.epoch,'location':self.location,
          'action':action,'hands':self.hands,'equipment':self.equipped,
          'target_stance':threat.get('stance'),'target_hp':threat.get('hp')}
        if p[0]=='eat':relevant.update(hp=self.hp,max_hp=self.observed_max_hp)
        return uid(compact(relevant))

    def choose(self,action,reasoning,goal_id=None,test_id=None,check=None):
        super().choose(action,reasoning,goal_id,test_id,check)
        scope=self.emergency_scope(action)
        if scope:
            self.pending['emergency_scope']={**scope,'key':self.emergency_key(action),'hp_before':self.hp,
              'parent_action':self.contract and self.contract['action'],'parent_goal':goal_id}
            self.emergency_contract={'action':action,'scope':scope,'parent_action':self.contract and self.contract['action'],
              'parent_goal':goal_id,'status':'awaiting_observed_effect','started':self.step}

    def advance(self,text):
        before=copy.deepcopy(self.pending);scope=before and before.get('emergency_scope')
        old_location=self.location;old_life=self.life;parent=self.contract
        # Suspend only the parent's no-progress accumulator for this executed
        # emergency action. Explicit denials and all physical updates still run.
        suspended=bool(scope and parent and parent['status']=='active' and parts(parent['action'])[0] not in ['attack','eat'])
        if suspended:parent['status']='evaluating_emergency_effect'
        try:result=super().advance(text)
        finally:
            if suspended and self.contract is parent and parent['status']=='evaluating_emergency_effect':parent['status']='active'
        self.observe_threats(text,old_location,old_life)
        if scope:
            a=before['action'];p=parts(a);effect=None;complete=False;quote=None
            if self.life==old_life and not self.current_denials:
                if p[0]=='attack':
                    m=re.search(r'I attacked '+re.escape(p[1])+r' for ([\d.]+) damage',text)
                    if m:effect=float(m[1]);quote=m[0]
                    complete=bool(re.search(r'\bdefeated '+re.escape(p[1])+r'!',text))
                else:
                    m=re.search(r'I ate '+re.escape(p[1])+r'\b[^\n]*?restored ([\d.]+) HP\s*\(HP:\s*([\d.]+)/([\d.]+)\)',text)
                    if m:
                        # Stated healing may be nominal at full health. Use the
                        # post-heal HP before incoming damage when available.
                        effect=min(float(m[1]),max(0,float(m[2])-scope['hp_before'])) if scope['hp_before'] is not None else None
                        quote=m[0];complete=scope['hp_before'] is not None and scope['hp_before']<float(m[3]) and self.hp is not None and self.hp>=float(m[3])
            net=self.hp-scope['hp_before'] if self.life==old_life and self.hp is not None and scope['hp_before'] is not None else None
            status='context_reset' if self.life!=old_life else 'environment_denied' if self.current_denials else 'effect_observed' if complete or effect is not None and effect>0 else 'no_effect_observed' if effect==0 else 'unresolved'
            count=self.emergency_streaks.get(scope['key'],0)
            if status=='no_effect_observed':count+=1
            elif status in ['effect_observed','context_reset']:count=0
            self.emergency_streaks[scope['key']]=count
            record={'step':self.step,'action_step':before['step'],'action':a,'scope':scope['kind'],
              'effect_amount':effect,'net_health_change':net,'status':status,'scope_completed':complete,
              'effect_evidence':quote,'parent_progress_suspended':suspended,'same_condition_no_effect_count':count,
              'losing_health_despite_healing':p[0]=='eat' and effect is not None and effect>0 and net is not None and net<=0}
            self.emergency_progress.append(record)
            if self.emergency_contract:self.emergency_contract.update(status=status,last_outcome=record)
        return result

    def gate(self,seq,goal,source):
        c,v=super().gate(seq,goal,source);a=seq[0];scope=self.emergency_scope(a);released=[]
        if scope:
            keep=[]
            for b in c['blockers']:
                # Only a resource-goal no-progress inference is out of scope.
                # A recorded environment denial never receives this exception.
                if b['kind']=='same_failed_action_context' and b['detail'].get('reason')==[NO_RESOURCE_PROGRESS]:released.append(b)
                else:keep.append(b)
            c['blockers']=keep
            if released:c['warnings'].append({'kind':'parent_progress_not_applicable_to_emergency','scope':scope,'count':len(released)})
            last=self.emergency_progress[-1] if self.emergency_progress else None
            if last and last['action']==a and last['losing_health_despite_healing']:
                c['warnings'].append({'kind':'healing_effect_positive_but_net_health_not_improving','action':a,'reason':'May buy time; reassess escape or threat removal. Not proof healing is impossible.'})
            no_effect=self.emergency_streaks.get(self.emergency_key(a),0)
            if no_effect>=2:c['warnings'].append({'kind':'repeated_emergency_no_effect','count':no_effect,'action':a,'reason':'Require fresh reasoning; do not automatically continue.'})
        if self.control_checks:self.control_checks[-1].update(blockers=copy.deepcopy(c['blockers']),emergency_scope=scope,released_parent_progress_rules=copy.deepcopy(released))
        self.emergency_checks.append({'step':self.step,'action':a,'source':source,'scope':scope,'released':released,'remaining_blockers':copy.deepcopy(c['blockers'])})
        return c,v

    def local_action(self,goal):
        if self.committed and self.emergency_scope(self.committed[0]) and self.emergency_streaks.get(self.emergency_key(self.committed[0]),0)>=2:return None
        return super().local_action(goal)

    def mechanism_packet(self):
        p=super().mechanism_packet();p['emergency_progress_scope']={'contract':self.emergency_contract,'recent_outcomes':self.emergency_progress[-3:],
          'semantics':'Attack/heal effects and net health are separate from resource progress; explicit precondition failures remain binding.'};return p

    def to_dict(self):
        p=super().to_dict();p['v3r5_emergency_audit']={'progress':self.emergency_progress,'checks':self.emergency_checks};return p
