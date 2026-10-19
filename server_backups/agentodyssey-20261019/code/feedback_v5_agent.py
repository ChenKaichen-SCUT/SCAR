"""Full observed history, bounded projection, local-first execution, one integrated decision."""
import json,os,re
from functools import lru_cache
from pathlib import Path
from openai import OpenAI,APIStatusError
from agents.long_context_agent import LongContextAgent
from agents.feedback_v5_core import Ledger,ScreenStopped
from agents.compact_decision_packet import packet_for

class BudgetStopped(RuntimeError):pass
class GuardedModel:
    def __init__(self):
        base=os.environ['AO_V5_BASE_URL']
        if not re.fullmatch(r'http://127\.0\.0\.1:8094/[a-z0-9_-]+/v1',base):raise ValueError('v5 only uses its metered loopback proxy')
        self.client=OpenAI(base_url=base,api_key='local-proxy',max_retries=0,timeout=150)
    def generate(self,user_prompt,system_prompt):
        try:r=self.client.chat.completions.create(model='deepseek-flash',messages=[{'role':'system','content':system_prompt},{'role':'user','content':user_prompt}],max_tokens=768,temperature=.7,presence_penalty=1.5)
        except APIStatusError as e:
            if e.status_code==429:raise BudgetStopped('pre_request_budget_or_batch_halt') from e
            raise
        return {'response':r.choices[0].message.content,'num_input_tokens':r.usage.prompt_tokens,'num_output_tokens':r.usage.completion_tokens}

INSTRUCTION='''
Current decision projection (omitted details remain in the full observation history):
{packet}
Return JSON: reasoning (at most 80 words), action, goal_id, objective={{"action":"observable terminal action","reason":"brief"}}, candidates=[{{"actions":["next action","at most three following actions"]}}]. At most 3 alternative paths.
Keep the main task and its exact parameters. Change observed prerequisites before retrying a failure. An accepted action is not necessarily progress. Do not rewrite an already recorded text or equip an object explicitly found non-equippable. Return from danger/darkness can be necessary; repeating a whole trip with no new information or net prerequisite gain is different. Historical object locations are not proof they are still present. If recovery is requested, revise the route or the invalid objective; changing the explanation alone is insufficient.
Optional hypotheses (at most one) have id, claim, test_action, preconditions, expected, evidence. Predicate kinds: held/equipped/quantity/crafted/written use object (quantity/crafted also amount; written also text); at_location uses location; visible optionally uses object; task_complete uses task_id. Evidence is a list of {{"step":observation_number,"quote":"short exact observation quote"}}. Only supply test_id for an applicable explicit test. A normal known preparation does not need a hypothesis. This decision also performs recovery review; no separate review call is made.
'''
class FeedbackV5Agent(LongContextAgent):
    def __init__(self,*args,**kw):
        super().__init__(*args,**kw);self.ledger=Ledger();self.ledger.schemas=[(a.verb,list(a.params)) for a in self.available_actions]
        self.llm=GuardedModel();self.audit_path=Path(os.environ['AO_CONTROL_AUDIT']);self.audit_path.parent.mkdir(parents=True,exist_ok=True)
        self.system=self.cfg.system_prompt.replace('exactly these keys','these required keys; additional planning fields are permitted')
        self.model_calls=0;self.repairs=0
    def emit(self,entry):
        with self.audit_path.open('a',encoding='utf-8') as f:f.write(json.dumps(entry,ensure_ascii=False)+'\n')
    def valid_goal(self,g):
        if isinstance(g,str) and g in self.ledger.tasks and self.ledger.tasks[g]['status']=='open':return g
        if self.ledger.focus in self.ledger.tasks and self.ledger.tasks[self.ledger.focus]['status']=='open':return self.ledger.focus
        tasks=packet_for(self.ledger).get('tasks',[]);return tasks[0]['id'] if tasks else None
    def propose(self,prompt):
        result=self.llm.generate(user_prompt=prompt,system_prompt=self.system);self.model_calls+=1
        try:raw=self.cfg.json_parser(result['response'])
        except (ValueError,TypeError):raw={}
        return result,raw if isinstance(raw,dict) else {}
    def select(self,raw):
        goal=self.valid_goal(raw.get('goal_id'));self.ledger.focus=goal
        obj=raw.get('objective',{})
        if isinstance(obj,dict):self.ledger.install_objective(obj.get('action'),goal,str(obj.get('reason','')))
        if isinstance(raw.get('hypotheses'),list) and raw['hypotheses']:
            self.ledger.apply_review({'focus_task_id':goal,'hypotheses':raw['hypotheses'][:1]})
        candidates=raw.get('candidates',[]);candidates=candidates[:3] if isinstance(candidates,list) else []
        candidates=[x for x in candidates if isinstance(x,dict) and isinstance(x.get('actions'),list) and x['actions']]
        if isinstance(raw.get('action'),str):
            matching=[x for x in candidates if x['actions'][0]==raw['action']]
            candidates=(matching[:1] or [{'actions':[raw['action']]}])+[x for x in candidates if x['actions'][0]!=raw['action']]
        action,check,record=self.ledger.dispatch_fresh(candidates,goal);return goal,action,check,record
    def _act(self,obs):
        text=obs['text'];self.ledger.advance(text);s=self.ledger
        if s.history:self.emit({'event':'outcome','step':s.step,'outcome':s.history[-1]})
        if s.objective and s.tasks.get(s.objective['goal_id'],{}).get('status')!='open':s.objective['status']='task_replaced_or_completed';s.queue=[]
        replan=s.request_replan_if_needed();goal=self.valid_goal(s.focus)
        chosen=None if replan else s.local_candidate(goal);tin=tout=0;raw={};response=None
        if chosen:
            action,check,record=chosen;s.local_streak+=1
            if not s.queue or s.queue[0]!=action:s.queue=[action]
            s.interventions.append(record);reason='Execute the next observed-valid preparation or queued action; fresh observation checked.'
        else:
            projection=packet_for(s);projection['recovery_review_now']=replan
            prompt=self.construct_user_prompt_long_context(self.memory.get_all_memory(),f'[Observation {s.step}]\n'+text)+INSTRUCTION.format(packet=json.dumps(projection,ensure_ascii=False,separators=(',',':')))
            result,raw=self.propose(prompt);tin+=result['num_input_tokens'];tout+=result['num_output_tokens'];response=result['response']
            goal,action,check,record=self.select(raw)
            if action is None and self.repairs<2:
                self.repairs+=1
                short=[{'action':x['action'],'reasons':[b['kind'] for b in x['blockers']]} for x in record['rejected']]
                result,raw=self.propose(prompt+'\nLocal checks rejected these proposals before execution: '+json.dumps(short)+'\nPropose a different enabling condition or route.');tin+=result['num_input_tokens'];tout+=result['num_output_tokens'];response=result['response']
                goal,action,check,record=self.select(raw)
            if action is None:raise ScreenStopped('no_admissible_action_after_bounded_correction')
            reason=str(raw.get('reasoning',''))[:480];s.local_streak=0
        executed={'action':action,'reasoning':reason}
        # Full observations and actual decisions are retained; long audit JSON is never appended here.
        note=''
        if record.get('rejected'):note='\nLocal feedback: '+','.join(sorted({b['kind'] for r in record['rejected'] for b in r['blockers']}))[:160]
        self.memorize(f'[Observation {s.step}]\n'+text+'\n'+self.cfg.format_response(executed)+note)
        test=raw.get('test_id') if raw.get('action')==action and isinstance(raw.get('test_id'),str) else None;s.choose(action,reason,goal,test,check)
        self.emit({'event':'decision','step':s.step,'action':action,'response':response,'dispatch':record,'check':check,'full_ledger':s.packet(),'model_calls':self.model_calls,'paid_call_this_step':response is not None})
        return action,tin,tout,json.dumps(executed)
    def observe_final(self,text):
        self.ledger.advance(text);self.emit({'event':'terminal_outcome','step':self.ledger.step,'outcome':self.ledger.history[-1] if self.ledger.history else None})
    def save_memory(self,full_memory_dir):
        super().save_memory(full_memory_dir);(Path(full_memory_dir)/'feedback_v5_state.json').write_text(json.dumps(self.ledger.packet(),ensure_ascii=False),encoding='utf-8')

@lru_cache(maxsize=None)
def create_feedback_v5_agent(Agent):return type('FeedbackV5Agent__'+Agent.__module__+'.'+Agent.__name__,(FeedbackV5Agent,Agent),{'__module__':Agent.__module__,'__agent__':Agent})
