"""Full-history ReAct with observed dependency dispatch; isolated from v2."""
import json, os
from functools import lru_cache
from pathlib import Path
from agents.long_context_agent import LongContextAgent
from agents.feedback_v3_core import Ledger
from providers.deepseek_adapter import DeepSeekLanguageModel

REVIEW_SYSTEM='''You control an interactive agent using only public observations, declared actions and its own history.
Choose a concrete terminal action for the CURRENT MAIN obligation (e.g. equip a particular observed item, craft a required item, write the required exact text). An ingredient preparation is not the terminal objective. Keep distinct tasks and their exact parameters separate. Prefer an independently achievable main task if the current route repeatedly stalls.
The ledger dispatches short preparation steps through observed recipes, containers, routes and capacities. Explain the missing enabling condition: available vs inaccessible contents, sufficient quantities, hand occupancy, station, held tool or visibility. A recipe listing on inspecting an object lists products made FROM that object, not the capabilities of a station. 'None' does not mean a station cannot craft. Nearby observations have locations and timestamps; historical presence is not current presence.
Recent dispatcher interventions are real feedback: a vetoed action was NOT executed. Repeating the veto cannot test the environment. Change preparation or route. Never call repeated inspection or creating surplus ingredients progress. If a terminal effect already happened, choose the next necessary action (e.g. pick up/equip the crafted object).
Optional hypotheses must name explicit preconditions and predicted observable effects. Accepted movement does not establish visibility. Do not create a hypothesis when a direct known preparation suffices. Quote observations exactly; no game rules or entities may be invented.
Return JSON: {"diagnosis":"...","focus_task_id":"existing pending id","next_action_rationale":"...","objective":{"action":"terminal action in declared format","reason":"how it satisfies the main task","evidence":[{"step":1,"quote":"exact source >=8 chars"}]},"hypotheses":[{"id":"stable id","claim":"...","test_action":"...","preconditions":[{"kind":"held","object":"observed object"}],"expected":[{"kind":"visible"}],"evidence":[{"step":1,"quote":"..."}]}]}.
At most two hypotheses. Predicate kinds: held/equipped(object), quantity(object,amount), at_location(location), visible(optional object; absent object means room visibility), crafted(object,amount), written(object,text), task_complete(task_id). A predicate must specify the EFFECT being tested, not repeat already satisfied prerequisites. All proposed results remain unverified until observation.'''

ACTOR_INSTRUCTION='''
Observed dependency and recovery state:
{packet}
Return JSON with reasoning, action, goal_id, objective, candidates, and optional test_id.
objective={{"action":"one concrete terminal action tied to the selected task","reason":"why"}}.
candidates=[{{"actions":["next action","following preparation", "... up to six actions"],"purpose":"what missing condition changes"}}, ... up to three ALTERNATIVE paths].
Put action equal to the first action in your preferred path. Every action must use the declared original interface. The dispatcher can execute a known necessary preparation before your proposal, or reject it; read prior interventions. Each path is short and will be rechecked against fresh observation after each action.
Preserve the unfinished terminal objective while obtaining its prerequisites. If the ledger reports prolonged stagnation, change the route or choose another independent main obligation. Do not endlessly make a resource already sufficient for the target. A tool for writing must be held. A stored ingredient must be in an accessible container; if it is on the ground, plan how to carry/equip that container while freeing hand space. Do not replace the objective with an easy substep to claim recovery.
When visibility is false, a historical NPC sighting does not establish current accessibility: obtain the enabling condition or change route. Inspect only to resolve a stated unknown; repeated unchanged inspection is rejected. Identical observations do not make a different explanation a new experiment. For causal tests, supply an explicit valid test_id only when the test's preconditions hold and its expected effect is observable. Otherwise perform a preparation without a test label.
Do not infer station capability from the ingredient-usage field. Keep parameters tied to their own tasks. Brief reasoning should identify the specific missing dependency and the expected observable change.
'''

class NoAdmissibleAction(RuntimeError):pass

class FeedbackV3Agent(LongContextAgent):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.ledger=Ledger();self.schemas=[(a.verb,list(a.params)) for a in self.available_actions];self.ledger.schemas=self.schemas
        self.actor_system=self.cfg.system_prompt.replace('exactly these keys','these required keys (additional planning fields are allowed)')+'\nAlso include goal_id, objective and candidates as described in the current decision request; test_id is optional. They do not change the original action interface.'
        self.controller_llm=DeepSeekLanguageModel(llm_name=self.cfg.llm_name,max_new_tokens=4096,temperature=0.,presence_penalty=0.)
        base=os.environ['AO_API_BASE_URL'];assert base.endswith('/v1')
        self.controller_llm.client.base_url=base[:-3]+'__controller/v1'
        self.audit_path=Path(os.environ['AO_CONTROL_AUDIT']);self.audit_path.parent.mkdir(parents=True,exist_ok=True)
    def emit(self,entry):
        with self.audit_path.open('a',encoding='utf-8') as f:f.write(json.dumps(entry,ensure_ascii=False)+'\n')
    def valid_goal(self,g):
        if isinstance(g,str) and g in self.ledger.tasks and self.ledger.tasks[g]['status']=='open':return g
        g=self.ledger.focus
        if g in self.ledger.tasks and self.ledger.tasks[g]['status']=='open':return g
        ts=self.ledger.packet()['pending_tasks'];return ts[0]['id'] if ts else None
    def candidates(self,raw):
        raw=raw if isinstance(raw,dict) else {};cs=raw.get('candidates',[])
        cs=cs[:3] if isinstance(cs,list) else []
        action=raw.get('action')
        if isinstance(action,str) and action.strip() and not any(isinstance(x,dict) and x.get('actions',[None])[0:1]==[action] for x in cs):cs.append({'actions':[action]})
        return cs
    def _act(self,obs):
        text=obs['text'];self.ledger.advance(text);tin=tout=0
        if self.ledger.history:self.emit({'event':'outcome','step':self.ledger.step,'outcome':self.ledger.history[-1],'net_cycle':self.ledger.loop})
        if self.ledger.objective and self.ledger.tasks.get(self.ledger.objective['goal_id'],{}).get('status')!='open':
            self.ledger.objective['status']='task_replaced_or_completed';self.ledger.queue=[]
        trigger=self.ledger.trigger()
        if trigger:
            req=self.ledger.review_input();req['declared_actions']=[{'verb':v,'params':p} for v,p in self.schemas]
            result=self.controller_llm.generate(user_prompt=json.dumps(req,ensure_ascii=False),system_prompt=REVIEW_SYSTEM)
            tin+=result['num_input_tokens'];tout+=result['num_output_tokens']
            parsed=self.cfg.json_parser(result['response']);accepted=self.ledger.apply_review(parsed)
            self.emit({'event':'controller','step':self.ledger.step,'trigger':trigger,'response':result['response'],'accepted':accepted})
        packet=self.ledger.packet()
        prompt=self.construct_user_prompt_long_context(self.memory.get_all_memory(),text)+ACTOR_INSTRUCTION.format(packet=json.dumps(packet,ensure_ascii=False))
        result=self.llm.generate(user_prompt=prompt,system_prompt=self.actor_system);tin+=result['num_input_tokens'];tout+=result['num_output_tokens']
        raw=self.cfg.json_parser(result['response']);raw=raw if isinstance(raw,dict) else {}
        goal=self.valid_goal(raw.get('goal_id'));objective=raw.get('objective')
        if isinstance(objective,dict):self.ledger.install_objective(objective.get('action'),goal,str(objective.get('reason','')))
        proposal_check=self.ledger.action_check(raw['action'],goal,self.schemas) if isinstance(raw.get('action'),str) else {'blockers':[{'kind':'missing_model_action'}]}
        action,check,dispatch=self.ledger.dispatch(self.candidates(raw),goal)
        first=result['response']
        if action is None and self.ledger.repairs<32:
            self.ledger.repairs+=1
            repair={'rejected':dispatch,'current_dependency_state':self.ledger.packet(),
              'instruction':'All proposals were rejected BEFORE execution. Propose a different preparation/route or another independent task, in the same JSON format. No arbitrary inspect fallback. Vetoed actions were not environment experiments. Include up to three genuinely different short paths.'}
            result=self.llm.generate(user_prompt=prompt+'\nDispatcher feedback:\n'+json.dumps(repair,ensure_ascii=False),system_prompt=self.actor_system)
            tin+=result['num_input_tokens'];tout+=result['num_output_tokens']
            raw=self.cfg.json_parser(result['response']);raw=raw if isinstance(raw,dict) else {};goal=self.valid_goal(raw.get('goal_id'))
            objective=raw.get('objective')
            if isinstance(objective,dict):self.ledger.install_objective(objective.get('action'),goal,str(objective.get('reason','')))
            action,check,dispatch=self.ledger.dispatch(self.candidates(raw),goal)
            self.emit({'event':'repair','step':self.ledger.step,'initial_response':first,'final_response':result['response'],'dispatch':dispatch})
        if action is None:
            self.emit({'event':'algorithm_stalled','step':self.ledger.step,'dispatch':dispatch,'packet':self.ledger.packet()})
            # Explicit algorithm failure is scored as an early stop; never spend hundreds of steps inspecting.
            raise NoAdmissibleAction('v3 could not produce an admissible new action after one correction; inspect control_audit')
        reasoning=str(raw.get('reasoning',''))[:2400]
        executed={'reasoning':reasoning+' [Dispatcher: '+dispatch['source']+']','action':action}
        rejection_note=json.dumps({'proposed':raw.get('action'),'initial_proposal_check':proposal_check,'executed':action,'dispatch':dispatch},ensure_ascii=False)
        self.memorize(text+'\n'+self.cfg.format_response(executed)+'\nDispatcher feedback (proposals are not executed actions): '+rejection_note)
        test=raw.get('test_id') if isinstance(raw.get('test_id'),str) else None
        if action!=raw.get('action'):test=None
        self.ledger.choose(action,reasoning,goal,test,check)
        self.emit({'event':'decision','step':self.ledger.step,'response':result['response'],'action':action,'goal_id':goal,'test_id':test,'check':check,
           'reviews_so_far':self.ledger.reviews,'repairs_so_far':self.ledger.repairs,'initial_proposal_check':proposal_check,'dispatch':dispatch,'packet':self.ledger.packet()})
        return action,tin,tout,json.dumps(executed)
    def save_memory(self,full_memory_dir):
        super().save_memory(full_memory_dir)
        p=Path(full_memory_dir)/'feedback_v3_state.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(self.ledger.to_dict(),ensure_ascii=False),encoding='utf-8');tmp.replace(p)
    def observe_final(self,text):
        self.ledger.advance(text);self.emit({'event':'terminal_outcome','step':self.ledger.step,'outcome':self.ledger.history[-1] if self.ledger.history else None,'net_cycle':self.ledger.loop})

@lru_cache(maxsize=None)
def create_feedback_v3_agent(Agent):
    return type('FeedbackV3Agent__'+Agent.__module__+'.'+Agent.__name__,(FeedbackV3Agent,Agent),{'__module__':Agent.__module__,'__agent__':Agent})
