"""Conditional retries, return paths and bounded recovery; no game-specific entities."""
import copy,json,re
try:
    from .feedback_v4_core import Ledger as V4
    from .feedback_v3_core import parts
    from .feedback_v2_core import compact,uid
except ImportError:
    from feedback_v4_core import Ledger as V4
    from feedback_v3_core import parts
    from feedback_v2_core import compact,uid

class ScreenStopped(RuntimeError):pass

class Ledger(V4):
    def __init__(self):
        super().__init__({'hard_repeat'})
        self.repeat_records=[];self.net_states=[];self.written_state={};self.ever_known=set()
        self.best_deficits={};self.last_useful_step=0;self.replan_at=None;self.cycle=None
        self.local_streak=0;self.useful_events=[];self._last_epoch=0;self._last_life=0
        self.target_revisions={};self.seen_transition_notices=set()
    def condition_key(self,action):
        # Health, clock, changing rationale and unrelated visible floor objects cannot reopen a failed action.
        return uid(compact({'action':action,'location':self.location,'hands':self.hands,'equipped':self.equipped,
            'containers':{k:{'items':v['items'],'complete':v['complete']} for k,v in self.containers.items() if k in self.hands or k in self.equipped},
            'visible':self.visibility,'hands_reported':self.hands_observed,'equipment_reported':self.equipment_observed,
            'target_revision':self.target_revisions.get(parts(action)[-1] if parts(action) else '',0),
            'epoch':self.epoch,'life':self.life_generation}))
    def net_key(self):
        total,unknown=self.accessible()
        return uid(compact({'location':self.location,'possessions':total,'inventory_unknown':unknown,'equipped':self.equipped,'epoch':self.epoch,'life':self.life_generation}))
    def evaluate_predicate(self,p):
        if p.get('kind')=='written':
            known=self.written_state.get(p.get('object'))
            if known and known['epoch']==self.epoch and known['text']==p.get('text'):return 'satisfied'
        return super().evaluate_predicate(p)
    def advance(self,text):
        before=copy.deepcopy(self.pending);old_epoch=self.epoch;old_life=self.life_generation
        prior_locations=set(self.world);result=super().advance(text)
        if self.epoch!=old_epoch or self.life_generation!=old_life:
            self.written_state={};self.net_states=[]
        facts={'location:'+self.location}
        facts.update('recipe:'+compact((k,v['ingredients'])) for k,v in self.recipes.items())
        facts.update('public_task:'+compact((k,v['status'])) for k,v in self.tasks.items())
        facts.update('stage:'+x.split('|',1)[-1] for x in self.completed_messages)
        # Only newly observed information counts; repeated errors and rewritten explanations do not.
        facts.update('denial:'+re.sub(r'\d+(?:\.\d+)?','<n>',x) for x in self.current_denials)
        # A public transition involving a previously attempted target can reopen a probe.
        # Repeated notices and changing model explanations cannot do so.
        targets={parts(r['action'])[-1] for r in self.repeat_records if parts(r['action'])}
        if before and parts(before['action']):targets.add(parts(before['action'])[-1])
        for line in text.splitlines():
            if re.search(r'\b(?:unlocked|opened|repaired|cleared|activated|deactivated|removed|restored)\b',line,re.I) and not re.search(r"\b(?:not|cannot|can't|never)\b",line,re.I):
                for target in targets:
                    notice=(self.epoch,target,line.strip())
                    if re.search(r'(?<!\w)'+re.escape(target)+r'(?!\w)',line) and notice not in self.seen_transition_notices:
                        self.seen_transition_notices.add(notice);self.target_revisions[target]=self.target_revisions.get(target,0)+1
                        self.inspection_versions[target]=self.inspection_versions.get(target,0)+1
                        facts.add('target_transition:'+compact(notice))
        for e in self.effects:
            if e['kind']=='written':
                self.written_state[e['object']]={'text':e['text'],'epoch':self.epoch,'step':self.step}
                self.inspection_versions[e['object']]=self.inspection_versions.get(e['object'],0)+1
                facts.add('written:'+compact((e['object'],e['text'])))
            elif e['kind']=='crafted':facts.add('crafted:'+e['object'])
        if before and before['action'].startswith('inspect ') and 'It has nothing written on it.' in text:self.written_state.pop(before['action'][8:],None)
        novel=facts-self.ever_known;self.ever_known.update(facts);progress=bool(novel)
        if before:
            goal=before.get('goal_id');target=before.get('objective_action','');k=(goal,target)
            if k in self.best_deficits:
                current=sum(self.deficit_vector(target).values())
                if current<self.best_deficits[k]:progress=True;self.best_deficits[k]=current
            self.repeat_records.append({'step':before['step'],'action':before['action'],'condition':before.get('repeat_condition'),
                'net':before.get('repeat_net'),'denied':bool(self.current_denials),'progress':progress})
        if progress:self.last_useful_step=self.step;self.replan_at=None;self.useful_events.append({'step':self.step,'novel_count':len(novel)})
        net=self.net_key();prior=[x for x in self.net_states[-24:] if x['key']==net and x['step']>=self.last_useful_step]
        self.cycle={'visits':len(prior)+1,'from_step':prior[0]['step'],'location':self.location} if len(prior)>=2 else None
        self.net_states.append({'step':self.step,'key':net})
        if self.cycle:self.queue=[]
        if self.location not in prior_locations:self.fresh_decision_required=True
        return result
    def choose(self,action,reasoning,goal_id=None,test_id=None,check=None):
        super().choose(action,reasoning,goal_id,test_id,check)
        self.pending['repeat_condition']=self.condition_key(action);self.pending['repeat_net']=self.net_key()
        k=(self.pending.get('goal_id'),self.pending.get('objective_action',''))
        if k not in self.best_deficits:self.best_deficits[k]=sum(self.pending.get('deficit_vector',{}).values())
    def is_return_to_visible(self,action):
        ps=parts(action)
        if len(ps)!=2 or ps[0]!='enter':return False
        threatened=self.visibility is False or bool(re.search(r'I was attacked by .+ and lost \d+ HP',self.current_text))
        if not threatened:return False
        return any(loc.split(', ')[-1]==ps[1] and record.get('epoch')==self.epoch for loc,record in self.world.items())
    def action_check(self,action,goal_id=None,schemas=None):
        c=super().action_check(action,goal_id,schemas)
        c['warnings']=[x for x in c['warnings'] if x['kind'] not in ['repeated_context_action','inspection_has_no_new_question']]
        key=self.condition_key(action);prior=[r for r in self.repeat_records if r['action']==action and r['condition']==key]
        if any(r['denied'] for r in prior):c['blockers'].append({'kind':'unchanged_failed_preconditions','action':action,'reason':'no observed change to load, location, visibility, rule or life context'})
        ps=parts(action)
        if ps and ps[0]=='write' and len(ps)>=3:
            known=self.written_state.get(ps[-1])
            if known and known['epoch']==self.epoch and known['text']==' '.join(ps[1:-1]):c['blockers'].append({'kind':'already_observed_write_effect','observation_step':known['step']})
        if action.startswith('inspect ') and (action[8:],self.inspection_versions.get(action[8:],0)) in self.inspections:
            c['blockers'].append({'kind':'unchanged_inspection','object':action[8:]})
        matched=[r for r in self.repeat_records[-24:] if r['net']==self.net_key() and r['step']>=self.last_useful_step and r['action']==action]
        if self.cycle and len(matched)>=2 and not action.startswith(('attack ','defend','eat ')):
            if self.is_return_to_visible(action):c['warnings'].append({'kind':'allow_exit_from_threat_or_darkness','cycle':self.cycle})
            else:c['blockers'].append({'kind':'net_cycle_without_gain','cycle':self.cycle,'reason':'change an observed prerequisite or choose a new route; changing objective wording is insufficient'})
        return c
    def repeat_status(self):
        age=self.step-self.last_useful_step
        return {'cycle':self.cycle,'steps_without_new_information_or_best_dependency_gain':age,'replan_requested_at':self.replan_at,
                'needs_replan':bool(self.cycle or age>=40),'stop_after_replan_grace_steps':12}
    def packet(self):
        p=super().packet();p['repeat_control']=self.repeat_status();p['persistent_written_effects']=self.written_state;p['recent_repeat_records']=self.repeat_records[-24:]
        return p
    def request_replan_if_needed(self):
        status=self.repeat_status()
        if self.replan_at is not None and self.step-self.replan_at>=12:
            raise ScreenStopped('stagnation_after_one_replan; bounded development screen stopped')
        if status['needs_replan'] and self.replan_at is None:
            self.replan_at=self.step;self.queue=[]
            if self.objective and self.objective['status']=='active':self.objective['status']='requires_replan'
            return True
        return False
    def local_candidate(self,goal):
        # A deterministic step may run before asking the model, at most three times between fresh decisions.
        if self.fresh_decision_required or self.cycle or self.local_streak>=3 or self.current_denials or self.repeat_status()['needs_replan']:return None
        if self.objective and (self.objective['status']!='active' or self.tasks.get(self.objective['goal_id'],{}).get('status')!='open'):return None
        options=[('validated_queue',self.queue[0])] if self.queue else []
        prep=self.preparation()
        if prep:options.append(('validated_preparation',prep))
        for source,action in options:
            c=self.action_check(action,goal,self.schemas);ps=parts(action)
            if c['blockers'] or c['unknown'] or not ps:continue
            known=False
            if ps[0]=='enter' and len(ps)==2:known=ps[1] in self.neighbors
            elif action.startswith('pick up '):known=self.hands_observed and self.nearby.get(action[8:],0)>0
            elif ps[0]=='equip' and len(ps)==2:known=ps[1] in self.hands and ps[1] in self.containers
            elif ps[0]=='craft':known=self.hands_observed and self.visibility is True
            elif ps[0]=='store' and len(ps)==4:known=ps[2] in self.hands and ps[3] in set(self.hands)|set(self.equipped)|set(self.nearby)
            if known:return action,c,{'step':self.step,'selected':action,'source':source,'rejected':[]}
        return None
    def dispatch_fresh(self,candidates,goal):
        rejected=[];self.queue=[]
        for x in candidates[:3]:
            seq=x.get('actions',[]) if isinstance(x,dict) else []
            seq=[a for a in seq[:4] if isinstance(a,str) and a.strip()]
            if not seq:continue
            check=self.action_check(seq[0],goal,self.schemas)
            if check['blockers']:rejected.append({'action':seq[0],'blockers':check['blockers']});continue
            self.queue=seq;record={'step':self.step,'selected':seq[0],'source':'fresh_model','rejected':rejected};self.interventions.append(record)
            return seq[0],check,record
        return None,None,{'step':self.step,'selected':None,'source':'no_admissible_candidate','rejected':rejected}
