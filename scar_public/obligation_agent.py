"""V3 chronological evidence plus an obligation-driven execution controller."""
import json
import re

from scar_public.obligations import ExecutionModel, base_name
from scar_public.viability import ViabilityMemory, VIABILITY_INSTRUCTION
from scar_public.evidence import EVIDENCE_INSTRUCTION


INSTRUCTION = """
Terminal checks are compiled conservatively from public task wording, not from your proposed
method. Unsupported goal semantics remain unknown. Never add consumed ingredients to the goal.
Historical crafting is an event; current possession and equipped status are different relations.
An unbound category such as 'weapon' is not an object named weapon.

The observed dependency tree may span recipes and locations. If a known item is only in a place
with no observed return route, do not pretend a familiar neighboring room leads there. Inspect
unexplored resources/locations or use another available method. Consider current threats.

Optionally add resource_target: the concrete output of an OBSERVED recipe you currently need
to acquire, or an empty string. This is a method choice, never a new terminal requirement.
The controller may search acquisition across known locations and recipes, execute one action,
then observe. Unknown transitions are conditional proposals, not successful simulated actions.

Writes trigger an actual inspect/write/inspect workflow when informative. Use the task role of
the content, not merely a quoted phrase. If accepted writes append to a nonempty document,
repeating the correct phrase does not restore its full contents: seek an appropriate fresh
document or an actually observed editing operation. Do not invent erase commands.
Return the V3 frame, reasoning and ONE action, plus resource_target only when useful.
"""

BINDING_INSTRUCTION = """
Resolve an imminent write against its public task role, BEFORE the write executes. You have the
exact task and chronological evidence. Return JSON with reasoning, action (one write command),
and alternatives: [{"value":"exact candidate text","quote":"exact public evidence excerpt",
"interpretation":"which task role this value serves","predicts_completion":true|false}].
Compare at most two materially plausible content bindings found in the observations. A phrase
used for a later different object is not automatically the current phrase. Pick the binding
whose SOURCE explicitly serves this task. Do not invent an alternative to fill the schema.
For a real ambiguity, each predicts whether writing your selected value satisfies this exact
task under that interpretation, on a suitable blank document with its tool available. These
are conditional hypotheses, not certified rules. If sources already identify the role clearly,
say so. Preserve exact spelling. Keep the selected document unchanged. Action must be write
followed by the selected value and the original document id; no extra quote delimiters.
"""


class ObligationMemory(ViabilityMemory):
    def __init__(self):
        super().__init__()
        self.model = ExecutionModel()
        self.resource_target = ''
        self.resource_started = 0
        self.pending_write = None
        self.binding_trials = []
        self.binding_queries = 0
        self.last_plan = None
        self.contracts = []

    def prompt(self, observation):
        self.model.observe(observation,self.last_action)
        result = super().prompt(observation)
        for trial in self.binding_trials:
            if trial.get('status') != 'awaiting_goal_feedback':continue
            goal = trial['goal']
            if goal in self.model.completed:
                trial.update(status='observed',observed=True)
            elif goal in self.model.current.get('fresh_tasks',[]):
                trial.update(status='observed',observed=False)
        contract = self.model.goal_contract(self.frame.get('goal_quote',''))
        self.contracts.append(contract)
        return result + '\nObserved obligation controller:\n' + json.dumps({
            'goal_contract':contract,'observed_model':self.model.view(),
            'resource_target':self.resource_target,'previous_resource_plan':self.last_plan,
            'write_semantics_observed':self.model.append_documents,
            'operation_experiments':self.model.semantic_trials[-3:],
            'binding_experiments':self.binding_trials[-3:]},ensure_ascii=False)

    def state(self):
        return {k:v for k,v in vars(self).items() if k!='model'}

    def load(self, state):
        for key in self.state():
            if key in state:setattr(self,key,state[key])
        self.model=ExecutionModel()
        actions={int(i):a for i,a in re.findall(r'^Action (\d+): (.*)$',self.ledger,re.M)}
        for i,obs in enumerate(self.observations):self.model.observe(obs,actions.get(i-1))


class ObligationAgent:
    def __init__(self,llm,system_prompt):
        self.llm=llm
        self.system_prompt=system_prompt.replace('exactly these keys','these required keys')+EVIDENCE_INSTRUCTION+VIABILITY_INSTRUCTION+INSTRUCTION
        self.notebook=ObligationMemory()

    def act(self,obs):
        memory=self.notebook; prompt=memory.prompt(obs['text']); model=memory.model; step=self.llm.step
        tokens=[0,0]
        def query(p,s=None):
            r=self.llm.generate(p,s or self.system_prompt)
            tokens[0]+=r['num_input_tokens'];tokens[1]+=r['num_output_tokens']
            return json.loads(r['response'])
        def program(action,source,reason):
            return {'reasoning':reason,'action':action,'decision_source':source,'frame':{
                **memory.frame,'goal_quote':memory.frame.get('goal_quote',''),
                'method':memory.frame.get('method',reason),'assessment':reason,
                'expected':'Observe actual feedback; no completion inferred from command acceptance.'}}
        parsed=None
        # Inspect the outcome of a genuinely distinguishing accepted write.
        if model.write_probe:
            name=model.write_probe['document']
            if name in (model.current.get('holding') or {}) or name in (model.current.get('ground') or {}):
                parsed=program('inspect '+name,'semantic_observation','Measure the full document text predicted differently by append and replace hypotheses.')
        if parsed is None and memory.pending_write:
            pending=memory.pending_write; name=pending['document'];doc=model.documents.get(name)
            fresh=doc and doc['observed_at']==len(model.history)-1
            if fresh:
                memory.pending_write=None
                if name in model.append_documents and doc['text'] and doc['text']!=pending['payload']:
                    prompt+='\nThe pending write is blocked by observed APPEND semantics and existing full text. Obtain a suitable fresh document or an evidenced editing method; do not repeat this write.\n'+json.dumps(pending)
                elif doc['text']==pending['payload']:
                    prompt+='\nThe requested full text is already present. Check the actual task/object/location binding; do not rewrite it.\n'
                else:
                    parsed=program(pending['action'],'semantic_intervention','Execute the selected task-bound write after a fresh inspection, then observe its actual effect.')
                    if pending.get('trial'):
                        trial=pending['trial']
                        trial.update(before_text=doc['text'],status='awaiting_goal_feedback',write_step=step,
                            qualification='Conditional on correct object/tool and completeness of the task preconditions; nonempty text may confound the binding test.')
                        memory.binding_trials.append(trial)
            else:
                # A failed inspection is not permission to assume empty contents.
                memory.pending_write=None
                prompt+='\nPending write inspection did not reveal current text; its result is unknown. Re-establish accessibility before writing.\n'
        if 'Stage completed:' in obs['text']:
            memory.resource_target=''
        if parsed is None and memory.resource_target and step-memory.resource_started<24:
            plan=model.acquisition(memory.resource_target);memory.last_plan=plan
            if plan.get('status')=='acquired':memory.resource_target=''
            elif plan.get('plan') and 'I was attacked' not in obs['text']:
                parsed=program(plan['plan'][0],'resource_search','Execute one step of the observed dependency/location arrangement, then replan from real feedback.')
            else:
                prompt+='\nResource obligation unresolved:\n'+json.dumps(plan)
        if parsed is None:
            parsed=query(prompt)
            action=parsed['action']
            target=parsed.get('resource_target','')
            if action.startswith('craft '):target=action.split()[-1]
            if target in model.recipes or target in model.qualitative_recipes:
                if target!=memory.resource_target:memory.resource_started=step
                memory.resource_target=target
                plan=model.acquisition(target);memory.last_plan=plan
                if plan.get('plan') and 'I was attacked' not in obs['text']:
                    parsed.update(action=plan['plan'][0],decision_source='resource_search')
                    parsed.setdefault('frame',{})['expected']='Observe the first action of the candidate resource plan, not its imagined suffix.'
            check=model.check_action(parsed['action'])
            repeat=model.relevant_repetition(parsed['action'])
            if check['status']=='contradicted' or (repeat>=2 and parsed['action'].startswith(('enter ','craft ','pick up ','drop '))):
                parsed=query(prompt+'\nProposed action: '+parsed['action']+'\nObserved constraint/repetition: '+json.dumps({
                    'check':check,'same_observed_arrangement_repetitions':repeat,'last_plan':memory.last_plan})+
                    '\nOne bounded repair: revise the missing obligation or select an informative new observation. Repetition needs an actual changed condition.')
        # A write proposal activates the probe workflow; no optional experiment field.
        if parsed['action'].startswith('write ') and parsed.get('decision_source')!='semantic_intervention':
            payload,name=parsed['action'][6:].rsplit(' ',1)
            write_goals=[t for t in model.tasks if re.search(r'\b(record|write|inscribe)\b',t,re.I)]
            goal=write_goals[0] if write_goals else parsed.get('frame',{}).get('goal_quote','')
            trial=None
            if memory.binding_queries<6:
                resolution=query('My Current Observation:\n'+obs['text']+'\nExact public task: '+goal+
                    '\nProposed write: '+parsed['action']+'\nChronological public evidence:\n'+memory.ledger,BINDING_INSTRUCTION)
                memory.binding_queries+=1
                proposed=resolution['action']
                choices=[a for a in resolution.get('alternatives',[])[:2] if isinstance(a,dict) and
                    isinstance(a.get('value'),str) and a['value'] and isinstance(a.get('quote'),str) and
                    a['value'] in a['quote'] and any(a['quote'] in o for o in memory.observations)]
                if proposed.startswith('write ') and proposed.rsplit(' ',1)[-1]==name:
                    selected=proposed[6:].rsplit(' ',1)[0]
                    if any(a['value']==selected for a in choices):payload=selected
                predictions=[a.get('predicts_completion') for a in choices]
                if len(choices)==2 and len({a['value'] for a in choices})==2 and all(type(p)is bool for p in predictions) and predictions[0]!=predictions[1]:
                    trial={'goal':goal,'selected':payload,'document':name,'alternatives':choices,'predictions':predictions,
                           'designed_at':step,'status':'pending_inspection'}
            pending={'action':'write '+payload+' '+name,'payload':payload,'document':name,'trial':trial}
            memory.pending_write=pending
            parsed['action']='inspect '+name
            parsed['decision_source']='semantic_precondition_observation'
            parsed.setdefault('frame',{})['expected']='Fresh full document text before a proposed semantic intervention.'
        parsed['goal_contract']=model.goal_contract(parsed.get('frame',{}).get('goal_quote',memory.frame.get('goal_quote','')))
        parsed['resource_plan']=memory.last_plan
        parsed['operation_experiments']=model.semantic_trials[-2:]
        parsed['binding_experiments']=memory.binding_trials[-2:]
        memory.update(parsed,obs['text'],step)
        return parsed['action'].strip(),tokens[0],tokens[1],json.dumps(parsed,ensure_ascii=False)
