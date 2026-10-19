"""v3 plus belief reconciliation; full history, local audit, no paid correction loop."""
import hashlib,json,os,re,sys
from functools import lru_cache
from pathlib import Path
from openai import OpenAI
from agents.long_context_agent import LongContextAgent
from agents.feedback_v3_agent import ACTOR_INSTRUCTION,REVIEW_SYSTEM
from agents.feedback_v3r4_core import Ledger
from agents.feedback_v2_core import schema_error

def refs_only(value):
    if isinstance(value,dict):
        if isinstance(value.get('quote'),str) and isinstance(value.get('step'),int):return {'observation_step':value['step']}
        return {k:refs_only(v) for k,v in value.items() if k not in ['reasoning','trials']}
    if isinstance(value,list):return [refs_only(x) for x in value]
    return value

def projection(s):
    tasks=sorted((t for t in s.tasks.values() if t['status']=='open'),key=lambda t:(t['id']!=s.focus,{'tutorial':0,'main':1,'unspecified':2,'side':3}.get(t['scope'],4),-t['evidence']['step']))[:6]
    p={'step':s.step,'location':s.location,'hands':s.hands,'equipped':s.equipped,'hands_known':s.hands_known,'equipment_known':s.equipment_known,'visibility':s.visibility,
       'nearby':s.nearby,'neighbors':s.neighbors,'tasks':[{'id':t['id'],'text':t['text'],'scope':t['scope']} for t in tasks],
       'objective':refs_only(s.objective),'queue':s.queue[:6],'named_parameters':refs_only(list(s.literals.values())),
       'semantics':'Unreported is not empty. Complete raw observations and executed actions remain in full history. Local interventions are proposals/measurements, not proof of universal rules.'}
    options=[('outcome_contract_and_operation_evidence',s.mechanism_packet()),('execution_authority',s.preparation_authority),('last_location_visits',s.last_visits),('visibility_supports',list(s.enablers.values())),('non_equippable',s.known_non_equippable),('containers',s.containers),('capacity',s.hand_limit),
      ('recipes',s.recipes),('stations',s.stations),('current_deficits',s.deficit_vector(s.objective['action']) if s.objective else {}),
      ('last_dispatch',s.interventions[-1:] if s.interventions else []),('recent_denials',s.current_denials),('guidance',s.guidance),
      ('world',s.world),('net_cycle',s.loop),('steps_without_dependency_progress',s.step-s.last_dependency_progress),('hypotheses',list(s.test_specs.values())[-2:])]
    omitted=[]
    for key,value in options:
        val=refs_only(value)
        if len(json.dumps({**p,key:val},ensure_ascii=False,separators=(',',':')))<=11700:p[key]=val
        else:omitted.append(key)
    p['omitted_fields_read_full_history']=omitted
    # Do not truncate raw text or fabricate a partial task as the full requirement.
    while len(json.dumps(p,ensure_ascii=False,separators=(',',':')))>12000 and len(p['tasks'])>1:p['tasks'].pop();omitted.append('older_task')
    if len(json.dumps(p,ensure_ascii=False,separators=(',',':')))>12000:
        p={'step':s.step,'objective':refs_only(s.objective),'hands':s.hands,'hands_known':s.hands_known,'omitted_fields_read_full_history':['projection exceeds bound; read full raw history']}
    return p

EXTRA='''
Keep reasoning under 60 words, with at most three candidate paths of at most six actions. Return JSON within 768 tokens. Preserve the current MAIN instruction and exact acceptance condition. Set objective.action to one valid, verifiable action rather than a paragraph; following preparations belong in candidates. An observed stage completion advances the task; merely crafting an intermediate or talking without new information does not.
Your first valid candidate has priority. Every action source uses the same prerequisite and failed-strategy checks. Carry an explicitly selected plan through its next outcome test after prerequisites change: an unvisited route need not already have succeeded to merit an attempt. Do not abandon a goal for another preparation once the required preparation has succeeded. A failed action without a tool does not show that it fails with the tool. The last_attempts records bind each execution to its actual BEFORE inventory and subsequent feedback; never claim an unexecuted attempt happened. Unexecuted or rejected candidate paths are not evidence.
Treat an observed held-tool requirement as mandatory. A failed tool-use attempt may consume its tool; check feedback and inventory before retrying. Keep alternative access methods available; knowing one way requires a tool does not prove that this is the only way. Reuse an existing resource before committing to a long manufacture chain. A full task route must be achievable: identify the unresolved frontier instead of repeatedly reacquiring already sufficient materials. If you deliberately release a resource to investigate that frontier, the system will not automatically pick it back up.
Raw observations remain in full history. Unknown container contents are not empty; inspecting resolves that uncertainty. A confirmed equipped inventory is accessible even before its contents have been inspected. A held light source may enable seeing without being required to act on remembered objects. Darkness does not erase possessions. Recipe usage listings are not station capability. Successful crafted products may be on the ground and need pickup; use the task's actual acceptance condition, not an assumed equip requirement.
On failed plans, change a relevant condition, target an unresolved fact, or choose another achievable obligation. Rewording a plan suffix is not a new strategy. A stopped plan needs fresh reasoning, not automatic inverse actions. Compare recent damage with health and the actions still needed before recovery, rather than treating a historically calm room as safe. Do not insert preparatory moves that cannot finish before the next damaging turns. No extra paid correction round is available.
'''

class Model:
    def __init__(self):
        base=os.environ['AO_API_BASE_URL'];assert re.fullmatch(r'http://127\.0\.0\.1:8094/[a-z0-9_-]+/v1',base)
        self.client=OpenAI(base_url=base,api_key='local-proxy',max_retries=0,timeout=150)
    def generate(self,user_prompt,system_prompt,controller=False):
        r=self.client.chat.completions.create(model='deepseek-flash',messages=[{'role':'system','content':system_prompt},{'role':'user','content':user_prompt}],max_tokens=768,temperature=0. if controller else .7,presence_penalty=0. if controller else 1.5)
        return {'response':r.choices[0].message.content,'num_input_tokens':r.usage.prompt_tokens,'num_output_tokens':r.usage.completion_tokens}

class FeedbackV3R4Agent(LongContextAgent):
    def __init__(self,*args,**kw):
        super().__init__(*args,**kw);self.ledger=Ledger();self.schemas=[(a.verb,list(a.params)) for a in self.available_actions];self.ledger.schemas=self.schemas
        self.llm=Model();self.model_calls=0;self.local_steps=0;self.fallbacks=0
        self.audit_path=Path(os.environ['AO_CONTROL_AUDIT']);self.audit_path.parent.mkdir(parents=True,exist_ok=True)
        self.actor_system=self.cfg.system_prompt.replace('exactly these keys','these required keys (additional planning fields are allowed)')
        self.call_limit=int(os.environ['AO_CALL_LIMIT']);assert self.call_limit==502
        self.max_steps=int(os.environ.get('AO_MAX_STEPS','300'));assert self.max_steps==300
        agent_module=FeedbackV3R4Agent.__module__;core_module=type(self.ledger).__module__;dispatch_module=self.ledger.dispatch.__func__.__module__
        assert agent_module=='agents.feedback_v3r4_agent' and core_module==dispatch_module=='agents.feedback_v3r4_core'
        self.emit({'event':'policy_loaded','agent_module':agent_module,'ledger_module':core_module,'dispatch_module':dispatch_module,'max_steps':self.max_steps,'source_sha256':{m:hashlib.sha256(Path(sys.modules[m].__file__).read_bytes()).hexdigest() for m in [agent_module,core_module]}})
    def emit(self,event):
        with self.audit_path.open('a',encoding='utf-8') as f:f.write(json.dumps(event,ensure_ascii=False)+'\n')
    def parse(self,text):
        try:r=self.cfg.json_parser(text)
        except (ValueError,TypeError,KeyError):r={}
        return r if isinstance(r,dict) else {}
    def call(self,prompt,system,controller=False):
        # Leave enough calls for one actor decision at every remaining environment step.
        if self.model_calls>=self.call_limit:raise RuntimeError('Paid call ceiling exhausted unexpectedly')
        r=self.llm.generate(prompt,system,controller=controller);self.model_calls+=1;return r
    def valid_goal(self,g):
        if isinstance(g,str) and g in self.ledger.tasks and self.ledger.tasks[g]['status']=='open':return g
        if self.ledger.focus in self.ledger.tasks and self.ledger.tasks[self.ledger.focus]['status']=='open':return self.ledger.focus
        tasks=self.ledger.packet()['pending_tasks'];return tasks[0]['id'] if tasks else None
    def candidates(self,raw):
        cs=raw.get('candidates',[]);cs=cs[:3] if isinstance(cs,list) else []
        cs=[{'actions':[a for a in x['actions'][:6] if isinstance(a,str) and a.strip()]} for x in cs if isinstance(x,dict) and isinstance(x.get('actions'),list)]
        cs=[x for x in cs if x['actions']]
        a=raw.get('action')
        if isinstance(a,str):cs.sort(key=lambda x:x['actions'][0]!=a)
        if isinstance(a,str) and a.strip() and not any(x['actions'][0]==a for x in cs):cs.insert(0,{'actions':[a]})
        return cs[:3]
    def _act(self,obs):
        text=obs['text'];s=self.ledger;s.advance(text);tin=tout=0;response=None;raw={};source=None
        if s.history:self.emit({'event':'outcome','step':s.step,'outcome':s.history[-1]})
        if s.objective and s.tasks.get(s.objective['goal_id'],{}).get('status')!='open':s.objective['status']='task_replaced_or_completed';s.queue=[]
        goal=self.valid_goal(None);local=None
        required=re.search(r'^\s*Required action:\s*`([^`]+)`',text,re.M)
        if required and not schema_error(required[1],self.schemas):
            a=required[1];local=(a,s.action_check(a,goal,self.schemas),{'step':s.step,'selected':a,'source':'explicit_public_tutorial_instruction','rejected':[]})
        if local is None:local=s.local_action(goal)
        if local:
            action,check,dispatch=local;s.local_streak+=1;self.local_steps+=1
            reason='Execute '+dispatch['source']+' with current observation checks; completion requires subsequent evidence.'
        else:
            trigger=s.trigger();remaining=self.max_steps+1-s.step
            if trigger and self.call_limit-self.model_calls>=remaining+1:
                req={'ledger':projection(s),'recent_observations':[{'step':i,'text':s.observations[i]} for i in range(max(1,s.step-7),s.step+1)],'declared_actions':[{'verb':v,'params':p} for v,p in self.schemas]}
                r=self.call(json.dumps(req,ensure_ascii=False),REVIEW_SYSTEM+'\nBe concise: at most one hypothesis and 768 output tokens.',True);tin+=r['num_input_tokens'];tout+=r['num_output_tokens']
                accepted=s.apply_review(self.parse(r['response']));self.emit({'event':'controller','step':s.step,'trigger':trigger,'response':r['response'],'accepted':accepted})
            prompt=self.construct_user_prompt_long_context(self.memory.get_all_memory(),f'[Observation {s.step}]\n'+text)+ACTOR_INSTRUCTION.format(packet=json.dumps(projection(s),ensure_ascii=False,separators=(',',':')))+EXTRA
            r=self.call(prompt,self.actor_system);tin+=r['num_input_tokens'];tout+=r['num_output_tokens'];response=r['response'];raw=self.parse(response)
            goal=self.valid_goal(raw.get('goal_id'));s.focus=goal;objective=raw.get('objective')
            if isinstance(objective,dict):s.install_objective(objective.get('action'),goal,str(objective.get('reason','')))
            candidates=self.candidates(raw);action,check,dispatch=s.dispatch(candidates,goal)
            if action is None:
                self.fallbacks+=1;action,check,dispatch=s.recover_action(candidates,goal,dispatch['rejected'])
                self.emit({'event':'rejected_batch_recovery','step':s.step,'dispatch':dispatch,'paid_correction_calls':0})
            reason=str(raw.get('reasoning',''))[:480];s.local_streak=0
        executed={'action':action,'reasoning':reason}
        note=''
        if dispatch.get('rejected'):
            note='\nLocal proposal feedback: '+','.join(sorted({b['kind'] for x in dispatch['rejected'] for b in x['blockers']}))[:250]
        if 'recovery' in dispatch['source'] or 'relaxation' in dispatch['source']:note+='\nExecuted local recovery: '+action+'; revise the rejected plan.'
        self.memorize(f'[Observation {s.step}]\n'+text+'\n'+self.cfg.format_response(executed)+note)
        test=raw.get('test_id') if isinstance(raw.get('test_id'),str) and raw.get('action')==action else None
        s.choose(action,reason,goal,test,check)
        self.emit({'event':'decision','step':s.step,'action':action,'response':response,'dispatch':dispatch,'check':check,'packet':s.packet(),'model_calls':self.model_calls,'local_steps':self.local_steps,'fallbacks':self.fallbacks,'reviews':s.reviews})
        return action,tin,tout,json.dumps(executed)
    def observe_final(self,text):
        self.ledger.advance(text);self.emit({'event':'terminal_outcome','step':self.ledger.step,'outcome':self.ledger.history[-1] if self.ledger.history else None})
    def save_memory(self,full_memory_dir):
        super().save_memory(full_memory_dir);(Path(full_memory_dir)/'feedback_v3r4_state.json').write_text(json.dumps(self.ledger.to_dict(),ensure_ascii=False),encoding='utf-8')

@lru_cache(maxsize=None)
def create_feedback_v3r4_agent(Agent):return type('FeedbackV3R4Agent__'+Agent.__module__+'.'+Agent.__name__,(FeedbackV3R4Agent,Agent),{'__module__':Agent.__module__,'__agent__':Agent})
