"""State/control correction of v3r3. Episode observations only, no game oracle.

One action gate for model plans, committed continuations, probes and recovery.
Unverified outcomes do not prohibit a bounded, explicitly planned attempt.
"""
import copy,re
from collections import deque
try:
    from .feedback_v3r3_core import Ledger as Previous
    from .feedback_v3_core import parts
    from .feedback_v2_core import compact,uid,schema_error
except ImportError:
    from feedback_v3r3_core import Ledger as Previous
    from feedback_v3_core import parts
    from feedback_v2_core import compact,uid,schema_error

DIRECT=r'(?:Craft|Find|Obtain|Defeat|Search|First, search|Continue your search|Arm yourself|Head to|Go to|Trade with|Record|Write|Bring|Buy|Collect|Equip|Talk to|Return|Read|Visit|Deliver|Do not|Then|Now)\b'
SYSTEM_LINE=r'(?:I (?:was |am |have |see |entered |lost |revived |died|used |picked |dropped |stored |took |ate |equipped )|My |Current |Neighboring |It is too dark|Sense of |Momentum |Tension |Friction |Noise |Hostile |You (?:are attacked|lost ))'

class Ledger(Previous):
    def __init__(self):
        super().__init__();self.task_corrections=[];self.control_checks=[];self.attempts=[]
        self.area_recent={};self.entry_tools={};self.current_npcs=set();self.pending_contact=None

    def parse_tasks(self,text):
        # The dialogue body ends before unindented narration. Preserve indented
        # lists and imperative continuations; do not change the raw observation.
        lines=text.splitlines();clean=[];speaking=False;utterances=[];owner=None;body=[]
        def finish():
            if owner and body:utterances.append((owner,'\n'.join(body)))
        for line in lines:
            m=re.match(r'\s*([\w_]+) says:\s*(.*)',line)
            if m:
                finish();owner=m[1];body=[m[2].strip()];speaking=True;clean.append(line);continue
            if speaking:
                continuation=bool(line.strip()) and not re.match(SYSTEM_LINE,line.strip(),re.I) and (line[:1].isspace() or re.match(DIRECT,line.strip()) or line.strip().startswith(('\"',"'")))
                if continuation:body.append(line.strip())
                else:
                    finish();owner=None;body=[];speaking=False
                    if line.strip():clean.append('')
            clean.append(line)
        finish()
        previous_focus=self.focus
        super().parse_tasks('\n'.join(clean))
        for npc,statement in utterances:
            if npc not in self.quest_owners:continue
            tid=uid(npc+'|'+statement);task=self.tasks.get(tid)
            if task and task.get('single_instruction'):
                if task['status']!='open':self.task_corrections.append({'step':self.step,'kind':'current_authoritative_instruction_reactivated','task':tid})
                task['status']='open';task['evidence']=self.ref(npc+' says: '+statement)
                for t in self.tasks.values():
                    if t.get('contact_instruction') and t['owner']==npc and t['status']=='open':t['status']='observed_complete'
                if self.pending_contact==npc:self.pending_contact=None
        if re.search(r'Tutorial\s+(?:Finished|completed|complete[.!])',text,re.I):
            for t in self.tasks.values():
                if t['scope']=='tutorial' and t['status']=='open':
                    t['status']='observed_complete';self.task_corrections.append({'step':self.step,'kind':'tutorial_finished','task':t['id']})
        if re.search(r'^\s*Stage completed\b',text,re.M):
            t=self.tasks.get(previous_focus,{})
            if t.get('scope')=='main':t['status']='observed_complete'
        contact=re.search(r'Talk to ([\w_]+) about what to do next',text)
        if contact:
            npc=contact[1];tid=self.add_task(contact[0],contact[0],'main',npc);self.tasks[tid].update(status='open',contact_instruction=True)
            self.pending_contact=npc;self.focus=tid
        if self.tasks.get(self.focus,{}).get('status')!='open':
            mains=[t for t in self.tasks.values() if t['status']=='open' and t['scope']=='main']
            if mains:self.focus=max(mains,key=lambda t:t['evidence']['step'])['id']

    def work_action(self):
        # Keep the selected outcome. Automatic recursion must not undo a release
        # or commit to a speculative unlock/manufacturing route on the model's behalf.
        return self.objective['action'] if self.objective and self.objective['status']=='active' else None

    def advance(self,text):
        before=copy.deepcopy(self.pending);old_hands=dict(self.hands);old_known=self.hands_known;old_life=self.life
        result=super().advance(text)
        damage=sum(float(x) for x in re.findall(r'lost (\d+(?:\.\d+)?) HP',text))
        self.area_recent.setdefault(self.location,deque(maxlen=3)).append(damage)
        self.current_npcs=set()
        for m in re.finditer(r'I see (.+?) nearby\.',text):
            self.current_npcs.update(x.strip() for x in m[1].split(',') if x.strip()!='no one')
        self.current_npcs.update(re.findall(r'^([\w_]+) enters the area\.',text,re.M))
        if before:
            a=before['action'];p=parts(a)
            if a.startswith('equip ') and ' as inventory.' in text and not self.current_denials:self.track_container(p[1])
            used=re.search(r'I used (?:a|an) ([\w_]+) to unlock',text)
            if used:
                self.entry_tools[used[1]]={'step':self.step,'operation':'enter','scope':'successful use here; a candidate elsewhere, not a universal guarantee'}
                if not re.search(r'^\s*I am holding ',text,re.M) and old_known and self.life==old_life:
                    self.hands=dict(old_hands);self.hands[used[1]]=max(0,self.hands.get(used[1],0)-1);self.hands={k:v for k,v in self.hands.items() if v};self.hands_known=True
            attempt_failure=bool(re.search(r'^\s*I failed to\b',text,re.M))
            if attempt_failure:
                self.committed=[];self.queue=[];self.plan_origin=None
                self.history[-1]['action_success']=False;self.history[-1]['attempt_failed']=True
                self.plan_repairs.append({'step':self.step,'reason':'attempt_failed_not_proof_of_impossibility','action':a})
            self.attempts.append({'action_step':before['step'],'after_observation':self.step,'action':a,
                'location_before':before.get('observed_before',{}).get('location'),'hands_before':before.get('observed_before',{}).get('hands',old_hands),
                'feedback':self.current_denials[:2] or [l for l in text.splitlines() if re.match(r'I (?:used |failed |successfully )',l)][:2],
                'attempt_failed':attempt_failure,'denied':bool(self.current_denials),'hands_after':dict(self.hands)})
        return result

    def cost_context(self):
        recent=list(self.area_recent.get(self.location,[]));peak=max(recent,default=0)
        return {'health':self.hp,'recent_damage_here':recent,'observed_damage_per_step':peak,
          'immediate_risk':self.hp is not None and peak>0 and self.hp<=3*peak,
          'semantics':'Recent local damage bounds automatic continuation; not a ranking of task value.'}

    def choose(self,action,reasoning,goal_id=None,test_id=None,check=None):
        super().choose(action,reasoning,goal_id,test_id,check)
        self.pending['observed_before']={'location':self.location,'hands':dict(self.hands),'equipment':dict(self.equipped)}

    def action_check(self,action,goal_id=None,schemas=None):
        c=super().action_check(action,goal_id,schemas);p=parts(action)
        if not p:return c
        tool=self.held_tools.get(p[0])
        if tool and not self.hands.get(tool['object'],0):
            issue={'kind':'observed_held_tool_missing','object':tool['object'],'evidence_step':tool['step']}
            (c['blockers'] if self.hands_known else c['unknown']).append(issue)
        if len(p)==2 and p[0]=='enter':
            if self.neighbors and p[1] not in self.neighbors:c['blockers'].append({'kind':'not_current_neighbor','target':p[1]})
            lock=self.locks.get(compact([self.epoch,self.location,p[1]]))
            if lock and any(n>lock['tools_at_failure'].get(o,0) for o,n in self.hands.items()):
                # A selected attempt after possession changes is admissible once.
                # We do not assert that an arbitrary acquired item unlocks a door.
                released=[b for b in c['blockers'] if b['kind']=='observed_locked_edge']
                c['blockers']=[b for b in c['blockers'] if b['kind']!='observed_locked_edge']
                if released:c['unknown'].append({'kind':'changed_possessions_allow_new_entry_trial','failure_hands':lock['tools_at_failure'],'current_hands':self.hands})
        return c

    def _plan_key(self,seq):
        # Different unexecuted suffixes do not reset a failed first action.
        return uid(compact([self.relevant_context(),seq[0] if seq else None]))

    def _transition(self,st,action):
        p=parts(action)
        if p and p[0]=='store' and len(p)==4:
            cid=self.canonical_container(p[3]);present=cid in set(st['hands'])|set(st['equipped'])|set(st['ground'])
            if present and cid not in st['bags']:return None,'container_capability_unverified'
            if cid!=p[3]:action=f'store {p[1]} {p[2]} {cid}'
        if p[:2]==['take','out'] and len(p)==4:
            cid=self.canonical_container(p[3]);action=f'take out {p[2]} {cid}'
        if not self.hands_known and (action.startswith(('drop ','store ','take out ','equip ','pick up '))):return None,'inventory_unverified'
        if action.startswith('craft ') and len(p)==3:
            total=self._available(st);need=self.needed(action)
            unknown=not self.hands_known or any(not self.containers.get(cid,{}).get('complete',False) for cid in set(st['hands'])|set(st['equipped']) if cid in st['bags'])
            if unknown and any(total.get(o,0)<n for o,n in need.items()):return None,'material_quantity_unverified'
        return super()._transition(st,action)

    def gate(self,seq,goal,source):
        a=seq[0];c=self.action_check(a,goal,self.schemas);validation=self.validate_plan(seq);key=self._plan_key(seq)
        if key in self.failed_plans:c['blockers'].append({'kind':'same_failed_action_context','detail':self.failed_plans[key]})
        stop=validation['stop']
        if stop and stop['status']=='contradicted':c['blockers'].append({'kind':'future_plan_conflict','detail':stop})
        self.control_checks.append({'step':self.step,'source':source,'action':a,'blockers':copy.deepcopy(c['blockers']),'plan_key':key,'validation':validation})
        return c,validation

    def _select_plan(self,seq,goal,source):
        c,v=self.gate(seq,goal,source)
        if c['blockers']:return None
        self.committed=list(seq);self.queue=list(seq);key=self._plan_key(seq)
        self.plan_origin={'key':key,'step':self.step,'goal':self.objective and self.objective['action']}
        if self.contract:self.contract['phase']='executing_checked_plan'
        return seq[0],c,{'step':self.step,'selected':seq[0],'source':source,'rejected':[],'plan_key':key,'validation':v}

    def automatic_witness(self,a):
        p=parts(a)
        if len(p)==2 and p[0]=='enter':return p[1] in self.neighbors
        if a.startswith('pick up '):
            o=a[8:]
            return self.hands_known and (self.nearby.get(o,0)>0 or (self.visibility is False and self.world.get(self.location,{}).get('objects',{}).get(o,0)>0))
        if p and p[0]=='equip':return self.hands_known and self.hands.get(p[1],0)>0
        if p and p[0]=='inspect':return p[1]=='inventory' or p[1] in set(self.hands)|set(self.equipped)|set(self.nearby)
        if p[:2]==['talk','to'] and len(p)==3:return p[2] in self.current_npcs
        if p and p[0]=='eat':return self.hands.get(p[1],0)>0 or self.nearby.get(p[1],0)>0
        if p and p[0] in self.held_tools:return self.hands.get(self.held_tools[p[0]]['object'],0)>0
        if p and p[0]=='craft':
            need=self.needed(a);total,_=self.accessible();return bool(need) and all(total.get(o,0)>=n for o,n in need.items())
        nxt,why=self._transition(self._resource_state(),a)
        return nxt is not None and why is None

    def local_action(self,goal):
        self.preparation_authority=None;self.next_probe=None
        if self.local_streak>=6 or self.cost_context()['immediate_risk']:return None
        if self.pending_contact and self.pending_contact in self.current_npcs:
            return self._select_plan(['talk to '+self.pending_contact],goal,'local_public_next_instruction')
        if self.new_task:return None
        if self.committed and not self.current_denials:
            a=self.committed[0]
            if self.automatic_witness(a):
                selected=self._select_plan(list(self.committed),goal,'local_committed_continuation')
                if selected:return selected
        if self.contract and self.contract.get('phase')=='needs_repair_or_probe':return None
        # No automatic recursive acquisition. A model's resource-release decision
        # remains in force until a newly selected plan explicitly reacquires it.
        work=self.work_action()
        if work and work.startswith('craft ') and not self.committed:
            probe=self.diagnostic_action(goal)
            if probe:
                c,v=self.gate([probe[0]],goal,'local_discriminating_probe')
                if not c['blockers']:return probe[0],c,probe[2]
                self.next_probe=None
            if not self.loop:
                seq=self.resource_plan(work)
                if seq:return self._select_plan(seq+[work],goal,'local_resource_plan')
        return None

    def dispatch(self,candidates,goal):
        rejected=[]
        for x in candidates[:3]:
            seq=[a for a in x.get('actions',[])[:6] if isinstance(a,str) and a.strip()] if isinstance(x,dict) else []
            if not seq:continue
            c,v=self.gate(seq,goal,'model_candidate');self.plan_checks.append({'step':self.step,'actions':seq,'validation':v})
            if c['blockers']:
                rejected.append({'action':seq[0],'source':'unified_action_gate','blockers':c['blockers']});continue
            selected=self._select_plan(seq,goal,'model_priority_preserved')
            if selected:
                a,c,d=selected;d['rejected']=rejected;self.interventions.append(d);return a,c,d
        self.committed=[];self.queue=[]
        return None,None,{'step':self.step,'selected':None,'source':'no_admissible_model_plan','rejected':rejected}

    def recover_action(self,candidates,goal,rejected):
        # The same gate applies even when only a valid prefix of a rejected path
        # can execute. No paid correction call and no cache-bypassing recovery.
        options=[a for c in candidates if isinstance(c,dict) for a in c.get('actions',[]) if isinstance(a,str)]
        options+=['inspect '+o for o in sorted(set(self.hands)|set(self.equipped)|set(self.nearby))]
        options+=['enter '+o for o in self.neighbors]
        options+=['defend','wait'];seen=set()
        for a in options:
            if a in seen or schema_error(a,self.schemas):continue
            seen.add(a);selected=self._select_plan([a],goal,'local_checked_recovery')
            if selected:
                act,c,d=selected;d['rejected']=rejected;self.interventions.append(d);return act,c,d
        # Preserve episode length without treating a heuristic as physical law.
        a=next(v for v,p in self.schemas if not p and v in ['defend','wait']);c=self.action_check(a,goal,self.schemas)
        return a,c,{'step':self.step,'selected':a,'source':'explicit_idle_recovery_after_exhausted_options','rejected':rejected}

    def mechanism_packet(self):
        p=super().mechanism_packet();p.update(last_attempts=self.attempts[-5:],known_held_tool_conditions=self.held_tools,
           next_public_contact=self.pending_contact,last_task_corrections=self.task_corrections[-3:],
           control_policy='Model priority retained unless a common gate rejects it; automatic continuation never recursively reacquires released resources.')
        return p

    def to_dict(self):
        p=super().to_dict();p['v3r4_audit']={**p.pop('v3r3_audit',{}),'task_corrections':self.task_corrections,'control_checks':self.control_checks,'attempts':self.attempts};return p

    def packet(self):
        p=super().packet();p['v3r4_mechanisms']=p.pop('v3r3_mechanisms');return p
