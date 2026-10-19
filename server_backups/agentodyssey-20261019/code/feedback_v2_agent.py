"""Full history actor with persistent typed facts, task dependencies and checks."""
import json,os
from functools import lru_cache
from pathlib import Path
from agents.long_context_agent import LongContextAgent
from agents.feedback_v2_core import Ledger
from providers.deepseek_adapter import DeepSeekLanguageModel

REVIEW_SYSTEM='''You control a partially observed interactive agent. Use only the supplied public observations and ledger. No hidden state, reward or solutions are available.
The ledger retains separate pending tasks, exact symbolic parameters, recipe QUANTITIES, locations, containers and capacity evidence. Do not collapse different tasks or replace an observed quantity with a guess. Prioritize the current main task; side objectives need a concrete dependency justification. A new clue does not complete older obligations.
Propose a small dependency plan connecting the next actions to a pending task. Preserve scarce or task-required items while simultaneously satisfying quantity, location, hand/tool and capacity conditions. Stored, held, nearby and equipped are different. Unknown container contents are unknown, not empty.
Hypothesis tests must distinguish alternative causes. If any other required condition is false or unknown, a failed action cannot refute the tested mechanism. In particular a quantity deficit cannot test an unrelated availability mechanism. Keep hypotheses open; generic failure is never proof of a universal negative. Only environment observations count as facts; your text is a proposal.
Assess three separate outcomes: action accepted, local obstacle removed, and a task dependency actually satisfied. Changing action or moving an item is not sufficient recovery. Detect resource cycles that undo progress. Combat, waiting for observed changes and collecting required quantities can legitimately repeat.
Return JSON only. Reuse stable ids, at most 3 plans and 2 hypotheses. All plan.task_id/focus_task_id must refer to supplied pending tasks. Quote exact observations, >=8 characters, with their observation step. No fabricated objects, recipes, tools or numeric parameters.
{
 "diagnosis":"concise explanation, competing causes and uncertainty",
 "focus_task_id":"existing pending task id",
 "next_action_rationale":"one feasible next action and why it reduces a pending dependency; include joint constraint checks",
 "plans":[{"id":"stable id","task_id":"existing id","description":"one subgoal",
    "depends_on_tasks":[],"reserve_items":["observed object name"],
    "expected":[{"kind":"quantity","object":"observed name","amount":1}],
    "evidence":[{"step":1,"quote":"exact observed text"}]}],
 "hypotheses":[{"id":"stable id","claim":"untested relationship",
    "alternatives":"other unmet or unknown preconditions that would confound a test",
    "test_action":"one declared executable action, or empty if currently not identifiable",
    "evidence":[{"step":1,"quote":"exact observed text"}]}]
}
Supported expected kinds: quantity(object,amount), held(object), equipped(object), at_location(location exact label), task_complete(task_id). They are checked deterministically against public state. Do not claim a task complete merely because a local predicate became true. Omit unnecessary hypotheses.''' 

ACTOR_INSTRUCTION='''
Persistent public-observation ledger and dependency checks:
{packet}
Use the exact observed quantities and keep different task parameters separate. Choose a pending task id and take one action that satisfies its dependencies while preserving other pending obligations. Do not let a local repair repeatedly undo another requirement. Inspect uncertain resources before using their absence as evidence.
If testing a hypothesis, other necessary conditions must be satisfied; a confounded failure is inconclusive. Plans and hypotheses above are proposals, not authoritative facts. Resolve contradictions in favor of exact observed evidence. Distinguish held/equipped/container/nearby items and respect current capacity, tool and location conditions jointly. A fixed invocation or NPC command cannot express a different operation merely by changing reasoning.
Return JSON with reasoning, action, goal_id (an existing pending task id), and optionally test_id. The action uses the original declared interface. Reason briefly about the expected dependency change; do not invent achievements.
'''

class FeedbackV2Agent(LongContextAgent):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.ledger=Ledger();self.schemas=[(a.verb,list(a.params)) for a in self.available_actions]
        self.controller_llm=DeepSeekLanguageModel(llm_name=self.cfg.llm_name,max_new_tokens=4096,temperature=0.,presence_penalty=0.)
        base=os.environ['AO_API_BASE_URL'];assert base.endswith('/v1')
        self.controller_llm.client.base_url=base[:-3]+'__controller/v1'
        self.audit_path=Path(os.environ['AO_CONTROL_AUDIT']);self.audit_path.parent.mkdir(parents=True,exist_ok=True)
    def emit(self,r):
        with self.audit_path.open('a',encoding='utf-8') as f:f.write(json.dumps(r,ensure_ascii=False)+'\n')
    def parse(self,result):
        parsed=self.cfg.response_parser(result['response']);raw=self.cfg.json_parser(result['response'])
        raw=raw if isinstance(raw,dict) else {}
        for key in ['goal_id','test_id']:
            if not isinstance(raw.get(key),str):raw[key]=None
        return parsed,raw
    def valid_goal(self,raw_goal):
        if raw_goal in self.ledger.tasks and self.ledger.tasks[raw_goal]['status']=='open':return raw_goal
        if self.ledger.focus in self.ledger.tasks and self.ledger.tasks[self.ledger.focus]['status']=='open':return self.ledger.focus
        pending=self.ledger.packet()['pending_tasks'];return pending[0]['id'] if pending else None
    def _act(self,obs):
        text=obs['text'];self.ledger.advance(text);tin=tout=0
        if self.ledger.history:self.emit({'event':'outcome','step':self.ledger.step,'outcome':self.ledger.history[-1],'net_cycle':self.ledger.loop})
        trigger=self.ledger.trigger()
        if trigger:
            request=self.ledger.review_input();request['declared_actions']=[{'verb':v,'params':p} for v,p in self.schemas]
            result=self.controller_llm.generate(user_prompt=json.dumps(request,ensure_ascii=False),system_prompt=REVIEW_SYSTEM)
            tin+=result['num_input_tokens'];tout+=result['num_output_tokens']
            parsed=self.cfg.json_parser(result['response']);accepted=self.ledger.apply_review(parsed)
            self.emit({'event':'controller','step':self.ledger.step,'trigger':trigger,'response':result['response'],'accepted':accepted})
        packet=self.ledger.packet()
        prompt=self.construct_user_prompt_long_context(self.memory.get_all_memory(),text)+ACTOR_INSTRUCTION.format(packet=json.dumps(packet,ensure_ascii=False))
        result=self.llm.generate(user_prompt=prompt,system_prompt=self.cfg.system_prompt);tin+=result['num_input_tokens'];tout+=result['num_output_tokens']
        parsed,raw=self.parse(result);goal=self.valid_goal(raw.get('goal_id'));test=raw.get('test_id')
        check=self.ledger.action_check(parsed['action'],goal,self.schemas);first={'response':result['response'],'check':check}
        actionable=check['blockers'] or any(w['kind'] in ['quantity_deficit','net_cycle_reentry','reserved_task_resource'] for w in check['warnings'])
        if actionable and self.ledger.repairs<32:
            self.ledger.repairs+=1
            repair={'proposed_action':parsed['action'],'goal_id':goal,'checks':check,
                'instruction':'Reconsider once using these explicit constraints. Correct a factual/quantity/task-parameter mismatch; obtain missing information instead of treating uncertainty as refutation. Preserve required resources and break net-state cycles. If the action remains justified by new observations, explain the exact evidence. Return reasoning/action/goal_id and optional test_id JSON.'}
            retry=self.llm.generate(user_prompt=prompt+'\nJoint action check:\n'+json.dumps(repair,ensure_ascii=False),system_prompt=self.cfg.system_prompt)
            tin+=retry['num_input_tokens'];tout+=retry['num_output_tokens'];result=retry;parsed,raw=self.parse(result)
            goal=self.valid_goal(raw.get('goal_id'));test=raw.get('test_id');check=self.ledger.action_check(parsed['action'],goal,self.schemas)
            self.emit({'event':'repair','step':self.ledger.step,'initial':first,'final_response':result['response'],'final_check':check,'remaining_blockers':bool(check['blockers'])})
        strong=[b for b in check['blockers'] if b['kind'] in ['quantity_deficit','schema','task_parameter_mismatch']]
        if strong and any(v=='inspect' for v,_ in self.schemas):
            targets=[b.get('object') for b in strong if b.get('object')]
            targets += [c for c in self.ledger.accessible()[1] if c!='inventory']
            targets += sorted(set(self.ledger.hands)|set(self.ledger.equipped)|set(self.ledger.nearby))
            visible=set(self.ledger.hands)|set(self.ledger.equipped)|set(self.ledger.nearby)
            recent={t['action'] for t in self.ledger.history[-2:]}
            target=next((x for x in targets if x in visible and 'inspect '+x not in recent),None)
            if target:
                blocked=parsed
                parsed={'reasoning':'The proposed action conflicts with checked public facts. Inspect '+target+' to refresh resource or dependency information before replanning.','action':'inspect '+target}
                self.emit({'event':'constraint_fallback','step':self.ledger.step,'blocked_proposal':blocked,'violations':strong,'executed_action':parsed['action']})
                result=dict(result,response=json.dumps(parsed));test=None;check=self.ledger.action_check(parsed['action'],goal,self.schemas)
        self.memorize(text+'\n'+self.cfg.format_response(parsed))
        self.ledger.choose(parsed['action'],parsed['reasoning'],goal,test,check)
        self.emit({'event':'decision','step':self.ledger.step,'response':result['response'],'action':parsed['action'],'goal_id':goal,'test_id':test,'check':check,
                   'reviews_so_far':self.ledger.reviews,'repairs_so_far':self.ledger.repairs,'packet':packet})
        return parsed['action'],tin,tout,result['response']
    def save_memory(self,full_memory_dir):
        super().save_memory(full_memory_dir)
        p=Path(full_memory_dir)/'feedback_v2_state.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(self.ledger.to_dict(),ensure_ascii=False),encoding='utf-8');tmp.replace(p)
    def observe_final(self,text):
        self.ledger.advance(text)
        self.emit({'event':'terminal_outcome','step':self.ledger.step,'outcome':self.ledger.history[-1] if self.ledger.history else None,'net_cycle':self.ledger.loop})

@lru_cache(maxsize=None)
def create_feedback_v2_agent(Agent):
    return type('FeedbackV2Agent__'+Agent.__module__+'.'+Agent.__name__,(FeedbackV2Agent,Agent),{'__module__':Agent.__module__,'__agent__':Agent})
