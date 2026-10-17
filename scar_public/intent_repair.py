"""V13: audit task/method selection before acquisition overwrites the proposal.

Observe/enforce arms have identical prompts, parsers, base planner and audits.
Only enforcement of an audited switch differs. No task completion is inferred
from a new NPC instruction, and an upstream production is not a goal switch.
"""
import copy
import json
import re
from collections import deque
from time import perf_counter

from scar_public.evidence_repair import RepairMemory,RepairController,EvidenceRepairAgent
from scar_public.method_repair import (output_support,local_stock,material_effects,
    portfolio_check,joint_material_completion)
from scar_public.obligations import base_name,words
from scar_public.causal_model import digest

SCHEMA = """
For production/acquisition decisions, optionally include task_quote (the exact
public task) and method_endpoint (the final item sought for that task, which may
differ from the intermediate item crafted now). These describe your intended
method, not established world facts. Omit an unresolved endpoint rather than
inventing one. Do not infer task completion from producing an intermediate.
"""


def update_tasks(state,text,step):
    """Read public imperative NPC instructions without changing the base prompt."""
    for speaker,quote in re.findall(r'^([\w-]+) says: (.+)$',text,re.M):
        if not re.match(r'(?:Craft|Make|Produce|Arm|Obtain|Equip|Find|Locate|Defeat|Record|Write|Bring|Deliver|Explore|Speak|Search|Return|Learn)\b',quote):
            # A new report can change the objective without using this grammar.
            # Retire an old anchor rather than silently keep enforcing it; this
            # does not certify the old task as complete.
            if speaker in state and quote!=state[speaker]['quote']:del state[speaker]
            continue
        previous=state.get(speaker)
        state[speaker]=dict(quote=quote,source=speaker+' says: '+quote,last_seen=step,
            supersedes=previous['quote'] if previous and previous['quote']!=quote else None,
            qualification='Current public instruction from this speaker; replacement is not proof of completing the old task')


def task_view(model,tasks):
    view=copy.copy(model)
    view.tasks=list(dict.fromkeys(model.tasks+[r['quote'] for r in tasks.values() if r['quote'] not in model.completed]))
    view.known_tasks=list(dict.fromkeys(model.known_tasks+view.tasks))
    return view


def dependency_path(model,start,end,limit=6):
    todo=deque([(start,[])]);seen={start}
    while todo:
        item,path=todo.popleft()
        if item==end:return path
        if len(path)>=limit:continue
        for output in sorted(set(model.recipes)|set(model.qualitative_recipes)):
            inputs=model.recipes.get(output,{}).get('needs',model.qualitative_recipes.get(output,[]))
            if item in inputs and output not in seen:
                seen.add(output);todo.append((output,path+[dict(input=item,output=output,
                    numeric=output in model.recipes,needs=model.recipes.get(output,{}).get('needs'))]))
    return None


def proposed_intent(model,parsed,anchors):
    action=parsed['action'];target=action.split()[-1] if action.startswith('craft ') else parsed.get('resource_target','')
    quote=parsed.get('task_quote') or parsed.get('frame',{}).get('goal_quote','')
    if quote not in model.tasks:
        # Reuse only the exact current task anchor, never arbitrary cited prose.
        return dict(target=target,task='',endpoint='',status='UNBOUND_TASK')
    entities=set(model.entities());explicit=parsed.get('method_endpoint','')
    literals=model.goal_contract(quote)['supported_literals']
    named=list(dict.fromkeys(base_name(x['item']) for x in literals if x['kind'] in ('crafted','held','equipped')))
    if len(named)==1:endpoint=named[0];source='TASK_NAMED_ENDPOINT'
    elif explicit in entities:endpoint=explicit;source='EXPLICIT_LLM_INTENT'
    else:
        method=parsed.get('frame',{}).get('method','').lower().replace('_',' ')
        mentioned=[n for n in sorted(set(model.recipes)|set(model.qualitative_recipes))
                   if re.search(r'\b'+re.escape(words(n))+r'\b',method)]
        downstream=[n for n in mentioned if not target or dependency_path(model,target,n) is not None]
        # Discard an intermediate if a uniquely mentioned downstream endpoint
        # exists. Two branches remain ambiguous instead of selecting by spelling.
        ends=[n for n in downstream if not any(n!=o and dependency_path(model,n,o) is not None for o in downstream)]
        if len(ends)==1:endpoint=ends[0];source='UNIQUE_METHOD_ENDPOINT'
        elif not mentioned and target:endpoint=target;source='PROVISIONAL_DIRECT_OUTPUT'
        else:endpoint='';source='AMBIGUOUS_ENDPOINT'
    # An already anchored endpoint plus a public dependency path is enough to
    # recognize an upstream step even when the current frame abbreviates it.
    old=anchors.get(quote)
    if old and target and dependency_path(model,target,old['endpoint']) is not None and not explicit and len(named)!=1:
        endpoint=old['endpoint'];source='PERSISTENT_ENDPOINT_WITH_PUBLIC_DEPENDENCY'
    return dict(target=target,task=quote,endpoint=endpoint,status=source)


class IntentMemory(RepairMemory):
    def __init__(self):
        super().__init__();self.intent_tasks={};self.intent_anchors={};self.intent_audits=[]
        self.intent_interventions=[];self.intent_observed_count=0;self.intent_inspections=[]
        self.intent_reviewed={}
        self.model.acquisition_pruning=True

    def load(self,state):
        super().load(state)
        self.model.acquisition_pruning=True


class IntentController(RepairController):
    # Paired development runs found extra calls but no immediate command repair.
    # Keep the audit active; paid enforcement is an explicit research option.
    intervention_mode='observe'

    def view(self):return task_view(self.memory.model,self.memory.intent_tasks)

    def prepare_decision(self,text,step):
        m=self.memory
        for i in range(m.intent_observed_count,len(m.observations)):
            update_tasks(m.intent_tasks,m.observations[i],i)
        m.intent_observed_count=len(m.observations)
        view=self.view()
        for task in list(m.intent_anchors):
            if task not in view.tasks:del m.intent_anchors[task]
        # A checkpoint has the public previous method but no V13 registry yet.
        if not m.intent_anchors and m.frame:
            seed=proposed_intent(view,dict(action='',resource_target=m.resource_target,frame=m.frame),{})
            if seed['task'] and seed['endpoint']:
                m.intent_anchors[seed['task']]=dict(endpoint=seed['endpoint'],step=step,source='PREVIOUS_PUBLIC_FRAME')
        return super().prepare_decision(text,step)

    def assess(self,parsed,step,phase):
        started=perf_counter();m=self.memory;model=self.view()
        intent=proposed_intent(model,parsed,m.intent_anchors)
        task,target,endpoint=intent['task'],intent['target'],intent['endpoint']
        old=m.intent_anchors.get(task);status=intent['status'];block=False;data={}
        if not target:status='NOT_A_PRODUCTION_SELECTION'
        elif not task or not endpoint:pass
        elif not parsed['action'].startswith('craft '):
            # A provisional resource target does not turn navigation, inspecting,
            # or gathering into consumption. Never spend a repair call on these.
            status='PREPARATION_NOT_CONSUMPTION'
            if not old:m.intent_anchors[task]=dict(endpoint=endpoint,step=step,source=intent['status'])
        elif target!=endpoint and dependency_path(model,target,endpoint) is None and parsed['action'].startswith('craft '):
            status='UPSTREAM_LINK_UNSUPPORTED';block=True
            data['reason']='The claimed endpoint alone does not supply a public dependency path from this craft.'
        elif not old:
            status='NEW_PROVISIONAL_METHOD'
            m.intent_anchors[task]=dict(endpoint=endpoint,step=step,source=intent['status'])
        elif target!=old['endpoint'] and dependency_path(model,target,old['endpoint']) is not None:
            status='SUPPORTED_UPSTREAM_STEP'
            data['dependency']=dependency_path(model,target,old['endpoint'])
        elif endpoint==old['endpoint']:status='CONTINUE_ENDPOINT'
        else:
            support=output_support(model,endpoint,task)
            effects=material_effects(model,parsed['action'])
            stock,unknown=local_stock(model)
            previous_recipe=model.recipes.get(old['endpoint'])
            material=portfolio_check(stock,[dict(target=old['endpoint'],needs=previous_recipe['needs'])],effects) if previous_recipe and effects and not unknown else dict(status='UNKNOWN',unknown=unknown)
            # Evaluate legitimate alternatives jointly with explicit other active
            # commitments; do not preserve old inputs as terminal requirements.
            others=[]
            for other in model.tasks:
                if other==task:continue
                for lit in model.goal_contract(other)['supported_literals']:
                    if lit['kind'] in ('crafted','held') and not lit['value']:
                        pair=(base_name(lit['item']),1)
                        if pair not in others:others.append(pair)
            witnesses=[]
            for e in effects or []:
                post={i:n-e['consume'].get(i,0) for i,n in stock.items()}
                if any(stock.get(i,0)<n for i,n in e['consume'].items()):continue
                for i,n in e['produce'].items():post[i]=post.get(i,0)+n
                witnesses.append(joint_material_completion(model,post,[(endpoint,1)]+others))
            data=dict(task_support=support,material_options=material,joint_material_witnesses=witnesses)
            if support['status']=='UNKNOWN':status='UNSUPPORTED_ENDPOINT_SWITCH';block=True
            elif effects and not unknown and witnesses and all(w['status']=='JOINT_MATERIAL_WITNESS' for w in witnesses):
                status='SUPPORTED_SWITCH_WITH_MATERIAL_WITNESS'
                m.intent_anchors[task]=dict(endpoint=endpoint,step=step,source=support['status'])
            elif material.get('displaced'):
                status='SWITCH_LOSES_CURRENT_MATERIAL_CERTIFICATE';block=True
            else:
                # Missing quantities or remote resources are uncertainty, not a
                # proof that a supported goal switch must be forbidden.
                status='SUPPORTED_ROLE_MATERIALS_UNRESOLVED'
        row=dict(step=step,phase=phase,action=parsed['action'],intent=intent,previous=copy.deepcopy(old),
                 status=status,would_intervene=block,details=data)
        row['qualification']='Review request, not a proof of task failure. The previous endpoint is also provisional.'
        row['review_id']=digest(row);json.dumps(row)
        row['compute_and_assembly_ms']=(perf_counter()-started)*1000
        if target:m.intent_audits.append(row)
        return row

    def select_proposal(self,parsed,text,step,raw_query,prompt):
        row=self.assess(parsed,step,'before_acquisition')
        if not row['would_intervene'] or self.intervention_mode=='observe':return parsed
        # Cache the *decision to spend review budget*, not a global rejection of
        # the item. A changed task bridge, dependency or reserve result merits a
        # new review; clock ticks, repeated prose, and phase names do not.
        key=digest(dict(task=row['intent']['task'],endpoint=row['intent']['endpoint'],
            previous=(row['previous'] or {}).get('endpoint'),status=row['status'],
            support=row['details'].get('task_support'),
            displaced=row['details'].get('material_options',{}).get('displaced')))
        if key in self.memory.intent_reviewed:
            return {**parsed,'intent_review_reuse':dict(key=key,first_step=self.memory.intent_reviewed[key],
                outcome='Unresolved exploration allowed; no repeated paid review and no success certificate')}
        if step in self.memory.intent_reviewed.values():
            return {**parsed,'intent_unresolved':'At most one additional method review per environment action'}
        self.memory.intent_reviewed[key]=step
        # One bounded request. Both arms use identical provider/prompt until this
        # concrete review changes the decision; no blanket new advice is sent.
        revised=raw_query(prompt+'\nA task/method selection check found:\n'+json.dumps(row)+
            '\nThe old endpoint is provisional, not sacred. Supply a publicly supported same-task endpoint '
            'or a real upstream recipe chain; otherwise choose a non-consuming observation or repair an '
            'observed enabling condition. Do not treat missing evidence as global task impossibility. Return ONE action.')
        second=self.assess(revised,step,'bounded_revision')
        # Unknown role is not impossibility. A second unresolved proposal is
        # explicitly exploratory; do not create an endless inspect/look loop.
        # This controller makes a bounded recommendation, not a safety theorem.
        if second['would_intervene']:
            revised={**revised,'intent_unresolved':'No task-completion or resource-preservation certificate; bounded review exhausted'}
        self.memory.resource_target='';self.memory.resource_fresh=False
        event=dict(step=step,review=row,revision_review=second,proposed=parsed['action'],executed=revised['action'],
                   action_changed=parsed['action']!=revised['action'],extra_revision_calls=1)
        self.memory.intent_interventions.append(event)
        return {**revised,'intent_intervention':event}

    def finalize_decision(self,parsed,text,step,raw_query,prompt):
        # Acquisition may introduce a consuming action without a new LLM call.
        # It is subject to the same review budget and evidence, at the last point
        # where the actual command can change. Previously reviewed keys reuse it.
        return self.select_proposal(parsed,text,step,raw_query,prompt)

    def after_decision(self,parsed,text,step):
        # Inherited acquisition can choose an upstream action after the LLM's
        # intent was reviewed. Audit that transformation for false-positive study.
        row=self.assess(parsed,step,'executed_action_audit')
        if row['intent']['target']:parsed['intent_audit']=row
        events=[e for e in self.memory.intent_interventions if e['step']==step]
        for event in events:
            event['final_executed']=parsed['action']
            event['final_action_changed']=event['proposed']!=parsed['action']
        if events:parsed['intent_step_interventions']=events
        super().after_decision(parsed,text,step)


class IntentRepairAgent(EvidenceRepairAgent):
    def __init__(self,llm,system_prompt):
        super().__init__(llm,system_prompt)
        self.system_prompt+=SCHEMA  # identical in observe and enforce arms
        self.notebook=IntentMemory();self.resource_controller=IntentController(self.notebook)
