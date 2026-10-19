"""Public-text ledger, conservative hypothesis tests, and net-progress audit.

Parsers cover the declared text interface, not game entities, recipes or solutions.
No reward, hidden state, oracle, baseline trajectory or model API is read here.
"""
from __future__ import annotations
from collections import Counter
import hashlib
import json
import re
import shlex

DENIAL=re.compile(r"^(?:Cannot\b|Can't\b|Invalid\b|Failed\b|Not enough\b)",re.I)
STOPS=set('the a an is are was were be been to of on in at by with and or it its this that each one bears'.split())
def words(s):return set(re.findall(r'[a-z_]{3,}',str(s).lower()))-STOPS
def uid(s):return hashlib.sha256(s.encode()).hexdigest()[:12]
def counts(text):
    return {m.group(2).strip():float(m.group(1)) for m in re.finditer(r'(?:^|,\s*)(\d+(?:\.\d+)?)\s+([A-Za-z_][\w-]*)',text)}
def compact(x):return json.dumps(x,sort_keys=True,separators=(',',':'))
def schema_error(action,schemas):
    for verb,params in sorted(schemas,key=lambda x:-len(x[0])):
        if action==verb or action.startswith(verb+' '):
            try:values=shlex.split(action[len(verb):].strip())
            except ValueError:return 'Unbalanced quotation marks'
            free=any(p.lower() in {'text','message','content','query'} for p in params)
            return None if (len(values)>=len(params) if free else len(values)==len(params)) else 'Declared format: '+verb+' '+' '.join('<'+p+'>' for p in params)
    return 'Verb absent from declared action schema'

class Ledger:
    def __init__(self):
        self.step=0;self.observations={};self.hands={};self.equipped={};self.nearby={};self.location=''
        self.containers={};self.inventory_alias=None;self.recipes={};self.stations={};self.tasks={};self.literals={}
        self.pending=None;self.history=[];self.events=[];self.hypotheses={};self.plans={};self.focus=None
        self.reviews=0;self.repairs=0;self.last_review=-100;self.guidance=None;self.last_task_event=0
        self.completed_messages=set();self.diagnostic_signatures=set();self.snapshots=[];self.loop=None
        self.capacity=None;self.last_limit_count=None;self.current_text='';self.new_task=False;self.new_fact=False
        self.quest_owners=set()

    def ref(self,quote):return {'step':self.step,'quote':quote}
    def refs(self,refs):
        if not isinstance(refs,list):return []
        return [r for r in refs[:8] if isinstance(r,dict) and isinstance(r.get('step'),int) and isinstance(r.get('quote'),str) and len(r['quote'])>=8 and r['quote'] in self.observations.get(r['step'],'')]

    def add_task(self,text,source,scope,owner=''):
        tid=uid(owner+'|'+text)
        if tid not in self.tasks:
            self.tasks[tid]={'id':tid,'text':text,'scope':scope,'owner':owner,'status':'open','evidence':self.ref(source),'bindings':[]}
            self.new_task=True
        return tid

    def parse_tasks(self,text):
        lines=text.splitlines();owner='';scope='unspecified';listed=[];list_seen=False
        self.quest_owners.update(re.findall(r'Talk to ([\w_]+) about what to do next',text))
        for index,line in enumerate(lines):
            line=line.strip()
            if not line:continue
            m=re.search(r'([\w_]+) says: (.*)',line)
            if m:
                owner=m[1];scope='side' if 'side quest' in m[2].lower() else 'main' if 'Main goal:' in m[2] else 'unspecified'
                body=m[2]
                direct=bool(re.match(r'(?:Craft|Find|Obtain|Defeat|Search|First, search|Continue your search|Arm yourself|Head to|Go to|Trade with|Record|Write|Bring|Buy|Collect|Equip)\b',body))
                authoritative=owner in self.quest_owners and not body.startswith(('Main goal:',"I'm",'"You seem stuck'))
                if direct or authoritative:
                    if authoritative:
                        tail=[]
                        for following in lines[index+1:]:
                            if not following.strip():break
                            tail.append(following.strip())
                        if tail:body+='\n'+'\n'.join(tail)
                    source=line if not authoritative else line+('\n'+'\n'.join(tail) if tail else '')
                    for t in self.tasks.values():
                        if t.get('single_instruction') and t['owner']==owner and t['text']!=body and t['status']=='open':t['status']='superseded_by_authoritative_instruction'
                    tid=self.add_task(body,source,'main' if authoritative else scope,owner);self.tasks[tid]['single_instruction']=True
            if line.startswith('Chapter goal:'):
                self.add_task(line[len('Chapter goal:'):].strip(),line,'main','chapter')
            if 'Current tasks:' in line:list_seen=True
            m=re.match(r'\[\d+\]\s*(.+)',line)
            if m:
                listed.append(self.add_task(m[1],line,'main',owner))
            m=re.match(r'-\s*(.+\(reward:.*)',line)
            if m:self.add_task(m[1],line,'side',owner)
            if line.startswith('Required action:'):
                for t in self.tasks.values():
                    if t['scope']=='tutorial' and t['status']=='open':t['status']='superseded_by_next_instruction'
                self.add_task(line,line,'tutorial','tutorial')
        if list_seen and listed and owner:
            for tid,t in self.tasks.items():
                if t['owner']==owner and t['scope']=='main' and tid not in listed and t['status']=='open':
                    t['status']='not_in_latest_authoritative_list';t['status_evidence_step']=self.step
        for line in lines:
            line=line.strip()
            if line.startswith(('Stage completed','All sub-tasks done','Tutorial Step')) and ('completed' in line or 'complete.' in line or 'goal achieved:' in line):
                event_key=str(self.step)+'|'+line
                if event_key not in self.completed_messages:
                    self.completed_messages.add(event_key);self.last_task_event=self.step;self.new_task=True
                fragment=re.sub(r'^.*?(?:Stage completed:|goal achieved:)\s*','',line).strip(' .')
                for t in self.tasks.values():
                    if len(fragment)>=20 and (t['text'].lower().startswith(fragment.lower()) or fragment.lower().startswith(t['text'].rstrip('.').lower())):
                        t['status']='observed_complete';t['completion_evidence']=self.ref(line)
        # Named symbolic values remain distinct, with their original relation context.
        for line in lines:
            for m in re.finditer(r'\b[A-Z]{3,}(?:-[A-Z]{3,})+\b',line):
                value=m[0];before=line[:m.start()]
                label=' '.join(re.findall(r'[A-Za-z]+',before)[-6:])
                key=uid(value+'|'+label)
                if key not in self.literals:
                    self.literals[key]={'id':key,'value':value,'label':label,'evidence':self.ref(line.strip())};self.new_fact=True
        for t in self.tasks.values():
            for f in self.literals.values():
                # Generic relation-context matching; no game-specific parameter names.
                common=words(t['text']) & words(f['label'])
                match=len(common)>=2
                if match and f['id'] not in t['bindings']:t['bindings'].append(f['id'])

    def accessible(self):
        total=Counter(self.hands);unknown=[]
        eligible=set(self.hands)|set(self.equipped)
        if self.inventory_alias:eligible.add(self.inventory_alias)
        elif self.equipped and 'inventory' in self.containers:eligible.add('inventory')
        for cid in eligible:
            c=self.containers.get(cid)
            if c:
                total.update(c['items'])
                if not c['complete']:unknown.append(cid)
            elif cid in self.equipped:unknown.append(cid)
        return dict(total),unknown

    def canonical_container(self,name):return self.inventory_alias if name=='inventory' and self.inventory_alias else name
    def track_container(self,cid):
        cid=self.canonical_container(cid)
        return self.containers.setdefault(cid,{'items':{},'complete':False,'evidence_steps':[]})

    def advance(self,text):
        self.step+=1;self.current_text=text;self.observations[self.step]=text;self.new_task=False;self.new_fact=False
        before=self.pending
        lines=[x.strip() for x in text.splitlines() if x.strip()]
        denials=[x for x in lines if DENIAL.match(x)]
        for line in lines:
            if line.startswith('Current Location:'):self.location=line.split(':',1)[1].strip()
            elif line.startswith('I am holding '):self.hands=counts(line[len('I am holding '):])
            elif line.startswith('I have equipped '):self.equipped=counts(line[len('I have equipped '):])
            elif line.startswith('I see ') and line.endswith(' near me.'):self.nearby=counts(line[6:-9])
            for m in re.finditer(r'([\w_]+) \((\d[^()]*)\)',line):
                ingredients=counts(m[2])
                if 'can be used to craft:' in line and ingredients:
                    fact={'item':m[1],'ingredients':ingredients,'evidence':self.ref(line)}
                    if self.recipes.get(m[1],{}).get('ingredients')!=ingredients:self.new_fact=True
                    self.recipes[m[1]]=fact
            m=re.search(r'I am carrying (\d+) items.*?(?:limit here is|limit:)\s*(\d+)',line)
            if not m:m=re.search(r'carrying (\d+) item\(s\), within the legal limit of (\d+)',line)
            if m:self.last_limit_count=int(m[1]);self.capacity={'limit':int(m[2]),'reported_count':int(m[1]),'evidence':self.ref(line)}
        # World resets invalidate unobserved possession, but do not erase known tasks/recipes.
        if 'I revived at the starting point' in text:
            self.inventory_alias=None
            for c in self.containers.values():c['complete']=False;c['items']={}
        if before:
            action=before['action'];parts=action.split();ok=not denials
            if ok and action.startswith('equip ') and ('I equipped ' in text or 'I have equipped ' in text):
                cid=action[6:]
                if cid in self.containers or 'inventory' in text.lower():self.inventory_alias=cid
            if ok and action.startswith('unequip ') and action[8:]==self.inventory_alias:self.inventory_alias=None
            if ok and action.startswith('store ') and 'I stored ' in text and len(parts)==4:
                _,n,obj,cid=parts;c=self.track_container(cid)
                c['items'][obj]=c['items'].get(obj,0)+float(n);c['evidence_steps'].append(self.step)
            if ok and (action.startswith('take out ') or action.startswith('discard ')):
                if action.startswith('take out ') and 'I took out ' in text and len(parts)==4:n=1;obj=parts[2];cid=parts[3]
                elif action.startswith('discard ') and 'I discarded ' in text and len(parts)==4:n=float(parts[1]);obj=parts[2];cid=parts[3]
                else:n=0;obj='';cid=''
                if n:
                    c=self.track_container(cid);c['items'][obj]=max(0,c['items'].get(obj,0)-n);c['evidence_steps'].append(self.step)
            if action.startswith('inspect '):
                m=re.search(r'It contains:\s*(.*?)\s*\(capacity:',text)
                if m:
                    if action=='inspect inventory' and self.inventory_alias is None and len(self.equipped)==1:
                        self.inventory_alias=next(iter(self.equipped))
                    cid=self.canonical_container(action[8:]);c=self.track_container(cid)
                    c.update(items=counts(m[1]),complete=True);c['evidence_steps'].append(self.step)
            if ok and action.startswith('craft ') and 'successfully crafted' in text:
                # Which source supplied consumed ingredients is not observable: invalidate counts.
                for cid,c in self.containers.items():
                    if cid in self.hands or cid in self.equipped or cid==self.inventory_alias:c['items']={};c['complete']=False
            if ok and action.startswith(('eat ','sell ','throw ','invoke ')):
                for cid,c in self.containers.items():
                    if cid in self.hands or cid in self.equipped or cid==self.inventory_alias:c['complete']=False;c['items']={}
            if 'SEIZED!' in text or 'confiscate' in text.lower():
                for c in self.containers.values():c['complete']=False;c['items']={}
            m=re.search(r'Cannot craft ([\w_]+)\. Missing necessary (.+?) in the current area',text)
            if m:
                self.stations[m[1]]={'required':m[2].split(', '),'evidence':self.ref(m[0])};self.new_fact=True
            sig='\n'.join(denials)
            if sig and sig not in self.diagnostic_signatures:self.diagnostic_signatures.add(sig);self.new_fact=True
        self.parse_tasks(text)
        if before:
            trial={'step':before['step'],'after_step':self.step,'action':before['action'],'goal_id':before.get('goal_id'),
                   'denials':denials,'action_success':not denials,'new_task_evidence':self.new_task,
                   'new_information':self.new_fact,'precondition_audit':before['check']}
            if before.get('test_id') in self.hypotheses and self.hypotheses[before['test_id']]['test_action']==before['action']:
                h=self.hypotheses[before['test_id']]
                # Negative feedback never proves a universal negative, even after a clean local test.
                unknown=before['check']['unknown'];blocked=before['check']['blockers']
                outcome='indeterminate' if denials and (unknown or blocked) else 'failure_in_this_context' if denials else 'success_in_this_context'
                trial['hypothesis_test']={'id':before['test_id'],'outcome':outcome,'confounders':blocked,'unknown':unknown}
                h.setdefault('trials',[]).append(trial['hypothesis_test']|{'step':self.step})
                h['status']='open' if denials else 'observed_success_in_one_context'
            if denials and (before['check']['blockers'] or before['check']['unknown']):trial['failure_attribution']='indeterminate; other preconditions failed or unverified'
            trial['predicate_status']=self.evaluate_plan()
            self.history.append(trial)
        self.detect_loop()
        return self.events[-1:] if self.events else []

    def evaluate_predicate(self,p):
        total,unknown=self.accessible();kind=p.get('kind');obj=p.get('object')
        if kind in ['quantity','held','equipped'] and not isinstance(obj,str):return 'unknown'
        if kind=='quantity':
            amount=p.get('amount',1)
            if not isinstance(amount,(int,float)):return 'unknown'
            return 'satisfied' if total.get(obj,0)>=amount else 'unknown' if unknown else 'unsatisfied'
        if kind=='held':return 'satisfied' if self.hands.get(obj,0)>0 else 'unsatisfied'
        if kind=='at_location':return 'satisfied' if self.location==p.get('location') else 'unsatisfied'
        if kind=='equipped':return 'satisfied' if self.equipped.get(obj,0)>0 else 'unsatisfied'
        if kind=='task_complete':
            t=self.tasks.get(p.get('task_id'),{}) if isinstance(p.get('task_id'),str) else {}
            return 'satisfied' if t.get('status')=='observed_complete' else 'unsatisfied'
        return 'unknown'

    def evaluate_plan(self):
        status={}
        for pid,p in self.plans.items():
            preds=[self.evaluate_predicate(x) for x in p.get('expected',[])]
            deps=[self.tasks.get(t,{}).get('status')=='observed_complete' for t in p.get('depends_on_tasks',[])]
            status[pid]={'predicates':preds,'dependencies_satisfied':all(deps),
                'local_observable_satisfied':bool(preds) and all(x=='satisfied' for x in preds),
                'task_confirmed':self.tasks.get(p.get('task_id'),{}).get('status')=='observed_complete'}
        return status

    def detect_loop(self):
        total,_=self.accessible()
        projection={'location':self.location,'possessions':{k:v for k,v in total.items() if v},'equipped':self.equipped,
                    'task_events':len(self.completed_messages),'recipes':{k:v['ingredients'] for k,v in self.recipes.items()}}
        signature=uid(compact(projection));previous=[x for x in self.snapshots[-24:] if x['signature']==signature]
        self.loop=None
        if len(previous)>=2 and self.pending and not self.pending['action'].startswith(('attack ','defend','eat ','wait')):
            start=previous[-2]['step']
            segment=[x for x in self.history if x['after_step']>start]
            if segment and not any(x['new_task_evidence'] or x['new_information'] for x in segment):
                self.loop={'start_step':start,'end_step':self.step,'repeated_state_steps':[x['step'] for x in previous],
                    'reason':'same location and net possessions recur without new task evidence or diagnostic information',
                    'actions':[x['action'] for x in segment],'status':'candidate; combat/time/hidden change may justify it'}
                self.events.append({'event':'net_state_cycle','step':self.step,**self.loop})
        self.snapshots.append({'step':self.step,'signature':signature,'projection':projection})

    def action_check(self,action,goal_id=None,schemas=None):
        blockers=[];unknown=[];warnings=[];facts=[];total,unknown_containers=self.accessible()
        if schemas:
            error=schema_error(action,schemas)
            if error:blockers.append({'kind':'schema','detail':error})
        if action.startswith('craft '):
            p=action.split()
            if len(p)==3:
                recipe=self.recipes.get(p[2]);amount=float(p[1]) if p[1].isdigit() else 1
                if recipe:
                    facts.append(recipe['evidence'])
                    for obj,n in recipe['ingredients'].items():
                        deficit=n*amount-total.get(obj,0)
                        if deficit>0:
                            issue={'kind':'quantity_deficit','object':obj,'required':n*amount,'known_accessible':total.get(obj,0),'missing':deficit,'evidence':recipe['evidence']}
                            (warnings if unknown_containers else blockers).append(issue)
                    if unknown_containers:unknown.append({'kind':'uninspected_container_contents','containers':unknown_containers})
                else:unknown.append({'kind':'recipe_unknown','item':p[2]})
                station=self.stations.get(p[2])
                if station:
                    missing=[x for x in station['required'] if x not in self.nearby]
                    if missing:blockers.append({'kind':'station_not_currently_observed','objects':missing,'evidence':station['evidence'],'certainty':'current public observation; hidden objects remain possible'})
                else:unknown.append({'kind':'station_requirements_not_verified'})
        if action.startswith('write '):
            try:parts=shlex.split(action)
            except ValueError:parts=[]
            if len(parts)>=3:
                value=' '.join(parts[1:-1]);task=self.tasks.get(goal_id or self.focus,{})
                bindings=[self.literals[x] for x in task.get('bindings',[]) if x in self.literals]
                permitted={x['value'] for x in bindings}
                if len(permitted)==1 and value not in permitted:
                    blockers.append({'kind':'task_parameter_mismatch','task_id':task['id'],'task':task['text'],'attempted':value,'observed_parameter':list(permitted),'evidence':[x['evidence'] for x in bindings]})
        if action.startswith('pick up ') and self.capacity:
            if self.capacity['reported_count']>=self.capacity['limit']:
                warnings.append({'kind':'load_constraint','detail':'Last reported carried count is at/above limit; reserve room by releasing a nonrequired item before collecting more. Stored items may still count.','evidence':self.capacity['evidence']})
        if self.loop:
            repeated=Counter(self.loop['actions'])
            if repeated[action]>=2:warnings.append({'kind':'net_cycle_reentry','detail':self.loop})
        # Resource reservation is explicit and advisory if competing task priorities are uncertain.
        if action.startswith(('drop ','discard ')):
            parts=action.split();obj=parts[1] if parts[0]=='drop' else parts[2] if len(parts)>2 else ''
            for plan in self.plans.values():
                if obj in plan.get('reserve_items',[]) and self.tasks.get(plan.get('task_id'),{}).get('status')=='open':
                    warnings.append({'kind':'reserved_task_resource','object':obj,'task_id':plan['task_id'],'detail':'Preserve or explicitly re-plan this pending dependency before releasing it.'})
        return {'blockers':blockers,'unknown':unknown,'warnings':warnings,'evidence':facts}

    def trigger(self):
        # Uniform budget release avoids using all reviews early. No end-of-run cliff.
        released=min(80,1+self.step*80//500)
        if self.reviews>=released or self.reviews>=80 or self.step-self.last_review<3:return None
        if self.new_task:return 'task_or_stage_changed'
        if self.loop:return 'net_state_cycle'
        if self.history and self.history[-1]['denials']:return 'execution_denial'
        if self.step-self.last_review>=10:return 'dependency_checkpoint'
        return None

    def packet(self):
        open_tasks=[t for t in self.tasks.values() if t['status']=='open']
        open_tasks.sort(key=lambda t:({'tutorial':0,'main':1,'unspecified':2,'side':3}.get(t['scope'],4),t['evidence']['step']))
        return {'step':self.step,'focus_task_id':self.focus,'location':self.location,
            'hands':self.hands,'equipped':self.equipped,'nearby':self.nearby,'inventory_alias':self.inventory_alias,
            'containers':self.containers,'accessible_quantities':self.accessible()[0],'unknown_containers':self.accessible()[1],
            'capacity_last_reported':self.capacity,'pending_tasks':open_tasks,'named_parameters':list(self.literals.values()),
            'observed_recipes':list(self.recipes.values()),'observed_station_requirements':self.stations,
            'plans':list(self.plans.values()),'plan_status':self.evaluate_plan(),'hypotheses':list(self.hypotheses.values()),
            'net_cycle':self.loop,'recent_outcomes':self.history[-8:],'guidance':self.guidance if self.guidance and self.step-self.guidance['step']<=12 else None,
            'last_new_task_evidence_step':self.last_task_event,
            'semantics':'All quantities are observation-derived; unknown is not absent. Plans/hypotheses are proposals, not observed facts. No reward is exposed.'}

    def review_input(self):
        return {'ledger':self.packet(),'recent_observations':[{'step':s,'text':self.observations[s]} for s in range(max(1,self.step-7),self.step+1)]}

    def apply_review(self,r):
        self.reviews+=1;self.last_review=self.step;accepted=[];rejected=[]
        if not isinstance(r,dict):r={}
        focus=r.get('focus_task_id')
        if isinstance(focus,str) and focus in self.tasks and self.tasks[focus]['status']=='open':self.focus=focus
        plans=r.get('plans',[])
        if not isinstance(plans,list):plans=[]
        for p in plans[:4]:
            if not isinstance(p,dict):continue
            refs=self.refs(p.get('evidence'))
            if not isinstance(p.get('task_id'),str) or p['task_id'] not in self.tasks or not refs:rejected.append({'kind':'plan','reason':'unknown_task_or_invalid_provenance'});continue
            pid=str(p.get('id',''))[:64] or uid(p['task_id']+str(p.get('description')))
            expected=[x for x in p.get('expected',[])[:6] if isinstance(x,dict)] if isinstance(p.get('expected'),list) else []
            reserve=[x for x in p.get('reserve_items',[])[:8] if isinstance(x,str)] if isinstance(p.get('reserve_items'),list) else []
            deps=[x for x in p.get('depends_on_tasks',[])[:6] if isinstance(x,str) and x in self.tasks] if isinstance(p.get('depends_on_tasks'),list) else []
            self.plans[pid]={'id':pid,'task_id':p['task_id'],'description':str(p.get('description',''))[:600], 'expected':expected,'reserve_items':reserve,'depends_on_tasks':deps,'evidence':refs,'updated_step':self.step}
            older=[(x['updated_step'],k) for k,x in self.plans.items() if x['task_id']==p['task_id'] and k!=pid]
            for _,old_id in sorted(older)[:-1]:del self.plans[old_id]
            accepted.append(pid)
        hs=r.get('hypotheses',[])
        if not isinstance(hs,list):hs=[]
        for h in hs[:3]:
            if not isinstance(h,dict) or not self.refs(h.get('evidence')):continue
            hid=str(h.get('id',''))[:64] or uid(str(h.get('claim')))
            existing=self.hypotheses.get(hid,{})
            self.hypotheses[hid]={'id':hid,'claim':str(h.get('claim',''))[:600],'alternatives':str(h.get('alternatives',''))[:600],
                'test_action':str(h.get('test_action',''))[:200],'evidence':self.refs(h.get('evidence')),
                'status':existing.get('status','open'),'trials':existing.get('trials',[])[-6:]}
            if h.get('status') in ['supported','rejected','false','retired']:
                rejected.append({'kind':'hypothesis_promotion','id':hid,'reason':'model judgment cannot certify a general mechanism; use context-specific observed trials'})
        self.guidance={'step':self.step,'diagnosis':str(r.get('diagnosis',''))[:1000],'next_action_rationale':str(r.get('next_action_rationale',''))[:1000],
                       'status':'proposal; exact ledger facts take precedence; recheck current observation'}
        event={'event':'review_applied','step':self.step,'accepted_plans':accepted,'rejected_claims':rejected}
        self.events.append(event);return event

    def choose(self,action,reasoning,goal_id=None,test_id=None,check=None):
        if test_id not in self.hypotheses:
            test_id=next((k for k,h in self.hypotheses.items() if h['test_action']==action),None)
        self.pending={'step':self.step,'action':action,'reasoning':reasoning,'goal_id':goal_id or self.focus,'test_id':test_id,
                      'check':check or self.action_check(action,goal_id)}

    def to_dict(self):return {'step':self.step,'reviews':self.reviews,'repairs':self.repairs,'ledger':self.packet(),'events':self.events,'outcomes':self.history}
