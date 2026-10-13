"""AdaPlanner-AgentOdyssey Adaptation of official ALFWorld control flow.

Original: haotiansun14/AdaPlanner @ dba187601500e7d91fee5fd786a455aaa7988677
MIT (2023 Haotian Sun). This implementation uses a bounded JSON interpreter,
not the official unrestricted Python exec. See reports/stage17 source mapping.
"""
import copy
import json
import re
from pathlib import Path
from scar.io import atomic_json
from scar_v3.state import PublicState

PLAN_SCHEMA='''Return JSON {"reasoning":string,"steps":[...]}. Each step has an integer
id unique within the plan, and op: "action", "ask_LLM", "if", or "repeat".
Action: {"id":1,"op":"action","action":"inspect ITEM","expect":{"not_error":true}}.
Optional expectations: contains (string), location (exact public room name),
held {item:minimum}, ground {item:minimum}. Omit facts you cannot predict.
ask_LLM: {"id":2,"op":"ask_LLM","question":"a question about observations",
"bind":"variable_name"}. This asks a model at execution time and stores a string answer.
Use ${variable_name} substitution in later action strings or questions.
if: {"id":3,"op":"if","condition":{"contains":"public phrase"},"then":[steps],"else":[steps]}.
repeat: {"id":4,"op":"repeat","times":3,"body":[steps]} (1..20).
At most 100 nodes and nesting depth 8. No Python, code execution, hidden state queries,
physical environment reset, files, network or arbitrary tools. Use only the listed
game actions to discover information and change the world. Each action costs one step.
Plans may cover a useful phase of the task; if it ends, a continuation is planned.
Never claim target success merely because crafting deposited a product on the ground.'''


def validate_plan(data):
    ids=set();count=0
    def check(steps,depth=0):
        nonlocal count
        if not isinstance(steps,list) or not steps or depth>8:raise ValueError('Invalid plan structure')
        for step in steps:
            count+=1
            if count>100 or not isinstance(step,dict):raise ValueError('Plan size')
            ident=step.get('id')
            if not isinstance(ident,int) or ident in ids:raise ValueError('Unique integer ids required')
            ids.add(ident);op=step.get('op')
            if op=='action':
                if not isinstance(step.get('action'),str) or not step['action'].strip():raise ValueError('Action required')
                validate_condition(step.get('expect',{'not_error':True}))
            elif op=='ask_LLM':
                if not isinstance(step.get('question'),str) or not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]{0,50}',step.get('bind','')):raise ValueError('Invalid ask')
            elif op=='repeat':
                if not isinstance(step.get('times'),int) or not 1<=step['times']<=20:raise ValueError('Bounded repeat required')
                check(step.get('body'),depth+1)
            elif op=='if':
                validate_condition(step.get('condition'))
                check(step.get('then'),depth+1)
                if step.get('else'):check(step['else'],depth+1)
            else:raise ValueError('Unknown operation')
    check(data.get('steps'))


def validate_condition(condition):
    if not isinstance(condition,dict) or set(condition)-{'not_error','contains','location','held','ground'}:raise ValueError('Invalid public assertion')
    for key,value in condition.items():
        if key=='not_error' and not isinstance(value,bool):raise ValueError('boolean required')
        if key in ('contains','location') and not isinstance(value,str):raise ValueError('string required')
        if key in ('held','ground') and (not isinstance(value,dict) or any(not isinstance(v,(float,int)) or v<0 for v in value.values())):raise ValueError('Invalid count')


def check_condition(condition,obs):
    public=PublicState.observe(obs);fail=[]
    error=bool(re.search(r'Cannot |Invalid |blocked the way out|not enough|do not have',public.feedback,re.I))
    for key,value in condition.items():
        if key=='not_error' and value and error:fail.append('environment rejected action')
        elif key=='contains' and value.lower() not in obs['text'].lower():fail.append('expected public phrase absent: '+value)
        elif key=='location' and value!=(public.location or '').rsplit(', ',1)[-1]:fail.append('location differs')
        elif key in ('held','ground'):
            values=public.hands if key=='held' else public.ground
            if values is None or any(values.get(n,0)<v for n,v in value.items()):fail.append('public '+key+' assertion failed')
    return fail


class AdaPlanner:
    def __init__(self,id,name,cfg):
        super().__init__(id,name);self.cfg=cfg;cfg.available_actions=self.available_actions;cfg.__post_init__();self.llm=cfg.get_llm()
        self.target='';self.objective='';self.history=[];self.plan={};self.queue=[];self.variables={}
        self.versions=[];self.pending=None;self.deviation=None;self.events=[];self.version=0;self.step=0;self.decision={}

    def initialize(self,history,target,objective):
        self.target=target;self.objective=objective;self.history=copy.deepcopy(history)

    def system(self):
        # Preserve upstream action descriptions, replacing its single-action JSON
        # instruction explicitly with the phase-specific interpreter contract.
        return self.cfg.system_prompt+'\nFor this planning call, the JSON schema below overrides the single-action response schema.\n'+PLAN_SCHEMA

    def ask(self,user,phase,required,max_tokens=2048,validator=None):
        return self.llm.generate(user_prompt=user,system_prompt=self.system(),phase=phase,
            required=required,max_tokens=max_tokens,validator=validator)['parsed']

    def context(self,obs):
        return json.dumps(dict(objective=self.objective,current_observation=obs,
            recent_interactions=self.history[-3:],variables=self.variables,remaining_environment_actions=100-self.step),ensure_ascii=False)

    def plan_or_revise(self,obs):
        old=copy.deepcopy(self.plan);revision=bool(old)
        prompt=('Revise the executable plan using actual feedback. Preserve completed progress; do not assume a reset.\n' if revision else 'Create an executable plan to achieve the objective from this public state.\n')
        prompt+=self.context(obs)
        if revision:prompt+='\nPrevious plan and discrepancy: '+json.dumps(dict(plan=old,deviation=self.deviation),ensure_ascii=False)
        plan=self.ask(prompt,'revision' if revision else 'plan',('steps','reasoning'),validator=validate_plan)
        # Official code_check_prompt analogue: this is a separately charged call.
        checked=self.ask('Check this plan for interface syntax, feasible public expectations and bounded execution. '
            'Return the full corrected plan, preserving useful steps.\n'+self.context(obs)+'\n'+json.dumps(plan,ensure_ascii=False),
            'plan_check',('steps','reasoning'),validator=validate_plan)
        self.plan=checked;self.queue=copy.deepcopy(checked['steps']);self.version+=1
        resume=None
        if revision:
            ids=[s['id'] for s in checked['steps']]
            def valid_resume(data):
                if data.get('start_from') not in ids:raise ValueError('Resume must name a top-level step')
            resume=self.ask('Compare the old and revised plan and the CURRENT public state; choose the first still-needed '
                'top-level step in the revised plan. Completed physical progress and variables persist. '
                'Return JSON {"reasoning":string,"start_from":integer}.\n'+self.context(obs)+'\n'+json.dumps(dict(old=old,new=checked)),
                'resume',('start_from','reasoning'),max_tokens=768,validator=valid_resume)
            self.queue=self.queue[ids.index(resume['start_from']):]
        self.versions.append(dict(version=self.version,plan=copy.deepcopy(checked),resume=resume,
            discrepancy=copy.deepcopy(self.deviation),at_step=self.step,variables=copy.deepcopy(self.variables)))
        self.deviation=None;self.pending=None

    def substitute(self,text):
        def resolve(match):
            if match[1] not in self.variables:raise ValueError('Unbound plan variable: '+match[1])
            return self.variables[match[1]]
        return re.sub(r'\$\{([A-Za-z_][A-Za-z_0-9]*)\}',resolve,text)

    def _act(self,obs):
        # At most 64 internal control operations per environment decision. This is
        # a safety bound on the interpreter, not a six-attempt episode truncation.
        for _ in range(64):
            if self.deviation or not self.queue:self.plan_or_revise(obs)
            node=self.queue.pop(0);op=node['op']
            try:
                if op=='ask_LLM':
                    answer=self.ask('Answer the in-plan question using only public observations and variables. '
                        'Return JSON {"answer":string,"reasoning":string}.\n'+self.context(obs)+'\nQuestion: '+self.substitute(node['question']),
                        'ask_LLM',('answer','reasoning'),max_tokens=768,
                        validator=lambda d: isinstance(d['answer'],str) or (_ for _ in ()).throw(ValueError('string required')))
                    self.variables[node['bind']]=answer['answer'];self.events.append(dict(type='in_plan_ask',node=node,answer=answer));continue
                if op=='if':
                    branch='else' if check_condition(node['condition'],obs) else 'then'
                    self.queue=copy.deepcopy(node.get(branch,[]))+self.queue;continue
                if op=='repeat':self.queue=copy.deepcopy(node['body']*node['times'])+self.queue;continue
                action=self.substitute(node['action']);self.pending=copy.deepcopy(node)
                self.decision=dict(plan_version=self.version,node=node,action=action,variables=copy.deepcopy(self.variables))
                return action,0,0,json.dumps({'action':action,'reasoning':'execute AdaPlanner plan step'})
            except ValueError as exc:self.deviation=dict(kind='interpreter_error',message=str(exc),node=node)
        raise RuntimeError('AdaPlanner interpreter exceeded frozen 64 internal operations')

    def observe_transition(self,before,action,after):
        expected=(self.pending or {}).get('expect',{'not_error':True})
        failures=check_condition(expected,after)
        # Rejection is always an out-of-plan failure, even with an empty assertion.
        failures+=check_condition({'not_error':True},after)
        self.events.append(dict(type='feedback_check',version=self.version,node=copy.deepcopy(self.pending),
            expected=expected,failures=list(dict.fromkeys(failures)),step=self.step+1))
        if failures:self.deviation=dict(kind='assertion_failure',failures=list(dict.fromkeys(failures)),node=self.pending,feedback=after)
        self.history.append(dict(before=before,action=action,after=after));self.pending=None;self.step+=1

    def export(self):
        return {k:copy.deepcopy(getattr(self,k)) for k in ('target','objective','history','plan','queue','variables','versions','pending','deviation','events','version','step','decision')}
    def save_memory(self,directory):atomic_json(Path(directory)/'adaplanner.json',self.export())
    def load_memory(self,directory):self.__dict__.update(json.loads((Path(directory)/'adaplanner.json').read_text()))
