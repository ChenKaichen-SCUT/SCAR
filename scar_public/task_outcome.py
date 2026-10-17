"""V15: task-supported continuation selection before local efficiency.

Ranks observable support and preservation of known joint material witnesses,
not invented success probabilities. Every route is conditional; only public
task feedback establishes task completion. No engine/evaluator access.
"""
import copy,re
from scar_public.action_repair import ActionMemory,ActionController,ActionRepairAgent
from scar_public.intent_repair import proposed_intent,dependency_path
from scar_public.method_repair import output_support,task_binding,local_stock,joint_material_completion,material_effects
from scar_public.obligations import base_name,words
from scar_public.causal_model import digest


def task_role(model,endpoint,task):
    # A literal negative type report supersedes older positive descriptions.
    # Names and missing descriptions alone never establish a negative type.
    support=output_support(model,endpoint,task)
    if support['status']=='TASK_NAMED_OUTPUT':return support
    for line in reversed(model.source_lines):
        match=re.match(r'I inspected ([\w-]+): (.*)',line)
        if match and base_name(match[1])==base_name(endpoint):
            for category in ('weapon','armor','container'):
                if re.search(r'\b'+category+r'\b',task,re.I) and re.search(r'\bnot (?:a |an |the )?'+category+r'\b',match[2],re.I):
                    return dict(status='EXPLICIT_ROLE_CONTRADICTION',quote=line,task=task,output=endpoint)
            break
    return support


def preview_model(model):
    m=copy.copy(model)
    # acquisition/arrange records proposed discovery inspections. Candidate
    # evaluation must never mark an unexecuted inspection as already attempted.
    m.discovery_checks=copy.deepcopy(model.discovery_checks)
    return m


def remaining_obligations(model,task,endpoint):
    """Keep other explicit outputs, not the current method's ingredients."""
    result=[]
    for quote in model.tasks:
        for lit in model.goal_contract(quote)['supported_literals']:
            name=base_name(lit['item'])
            needed=lit['kind']=='held' or lit['kind']=='equipped' or (lit['kind']=='crafted' and not lit['value'])
            if needed and not (quote==task and name==base_name(endpoint)) and (name,1) not in result:
                result.append((name,1))
    return result


def reserve_check(model,task,endpoint,plan):
    """Conservative warning on losing a previously constructive material witness.

Failure to construct a new witness is UNKNOWN, not a proof of infeasibility.
We defer autonomous consumption in that case, rather than ban the task/recipe.
"""
    goals=remaining_obligations(model,task,endpoint)
    stock,unknown=local_stock(model)
    if not goals:return dict(status='NO_OTHER_EXPLICIT_OUTPUTS',goals=[])
    if unknown:return dict(status='UNKNOWN',goals=goals,unknown=unknown)
    before=joint_material_completion(model,stock,goals)
    if before['status']!='JOINT_MATERIAL_WITNESS':return dict(status='UNKNOWN',goals=goals,before=before)
    post=dict(stock)
    for action in plan:
        if not action.startswith('craft '):continue
        effects=material_effects(model,action)
        if not effects:return dict(status='UNKNOWN',goals=goals,before=before)
        for item in {n for e in effects for n in e['consume']}:
            post[item]=post.get(item,0)-max(e['consume'].get(item,0) for e in effects)
        # Inputs from remote sites are not silently promoted to fresh local stock.
        if any(v<0 for v in post.values()):return dict(status='UNKNOWN',goals=goals,before=before)
        for item,n in effects[0]['produce'].items():post[item]=post.get(item,0)+n
    # Identical possession predicates can share an item. Do not invent a demand
    # for two copies just because two task quotations mention the same output.
    joint=list(dict.fromkeys([(endpoint,1)]+goals))
    after=joint_material_completion(model,post,joint)
    return dict(status='JOINT_WITNESS_RETAINED' if after['status']=='JOINT_MATERIAL_WITNESS' else 'JOINT_WITNESS_NOT_REESTABLISHED',
        goals=goals,before=before,after=after,
        qualification='Material relaxation only; failure is inconclusive, accessibility and survival remain open')


def repair_preview(model,event):
    """Complete the hypothetical retrieval before searching an endpoint suffix.

Only observed model data are copied. This is a planning assumption, never new
evidence. A short retrieval alone is insufficient to admit the intervention.
"""
    c=event['chosen'];m=preview_model(model);m.current=copy.deepcopy(model.current)
    m.locations=copy.deepcopy(model.locations);m.containers=copy.deepcopy(model.containers)
    held=m.current['holding'];prefix=[];name=c['container'];origin=m.current['location']
    if c['action'].startswith('drop '):
        item=c['action'][5:];held[item]-=1
        if held[item]<=0:del held[item]
        m.locations[origin]['objects'][item]=m.locations[origin]['objects'].get(item,0)+1
        prefix.append(c['action'])
    prefix+=c['route']
    if not held.get(name):prefix.append('pick up '+name)
    else:held[name]-=1
    held.pop(name,None);prefix+=['equip '+name,'inspect '+name]
    dest=c['location'];m.locations[dest]['objects'].pop(name,None)
    m.current.update(location=dest,holding=held,equipped={name:1},ground=dict(m.locations[dest]['objects']),
        neighbors=m.locations[dest]['neighbors'])
    suffix=m.acquisition(event['target'],max_nodes=1500,seconds=.25)
    if suffix.get('status')!='candidate' or not suffix.get('plan'):return None
    return dict(plan=prefix+suffix['plan'],assumptions=suffix.get('assumptions',[])+[
        'container retrieval succeeds and inspected contents match remembered contents',
        'endpoint task role and remaining goal conditions require actual feedback'])


def physical_key(model,text):
    # Episode control only, not a reusable impossibility certificate. Health and
    # explicit modifiers matter; mere time passage does not renew a repair lease.
    attributes=[l for l in text.splitlines() if l.startswith(('My health','My attack','My defense','My level')) or
        re.search(r'\b(?:buff|bonus|penalty|modifier|weather)\b',l,re.I)]
    return digest([model.current,model.containers,model.recipes,model.completed,attributes])


class OutcomeMemory(ActionMemory):
    def __init__(self):
        super().__init__();self.outcome_decisions=[];self.outcome_focus=None
        self.outcome_lease=None;self.outcome_deferred={};self.outcome_probes=[]


class OutcomeController(ActionController):
    max_steps=300

    def compile_repair(self,review,text,step):
        event=super().compile_repair(review,text,step)
        if not event:return None
        plan=repair_preview(self.memory.model,event)
        if not plan:return None
        event['endpoint_preview']=plan
        return event

    def focus(self,parsed):
        view=self.view();intent=proposed_intent(view,parsed,self.memory.intent_anchors)
        target=intent['endpoint'] or intent['target'] or self.memory.resource_target
        if not target:
            method=parsed.get('frame',{}).get('method','').lower().replace('_',' ')
            mentioned=[n for n,b in self.memory.action_goal_bindings.items() if b['task'] in view.tasks and
                re.search(r'\b'+re.escape(words(n))+r'\b',method)]
            if len(mentioned)==1:target=mentioned[0]
        task=intent['task'] or task_binding(view,parsed,target)
        if not task:task=self.memory.action_goal_bindings.get(target,{}).get('task','')
        if task in view.tasks and target:return dict(task=task,target=target)
        return None

    def prepare_decision(self,text,step):
        m=self.memory
        old=m.resource_target
        result=super().prepare_decision(text,step)
        m.outcome_focus=self.focus(dict(action='',resource_target=old,frame=m.frame)) or m.outcome_focus
        if m.outcome_focus and m.outcome_focus['task'] not in self.view().tasks:m.outcome_focus=None
        self.chosen_step=None
        return result

    def alternatives(self,focus,text,step):
        m=self.memory;model=preview_model(self.view());task=focus['task'];original=focus['target'];remaining=self.max_steps-step
        endpoints=[original]
        endpoints += [n for n in sorted(model.entities()) if n!=original and task_role(model,n,task)['status'] not in ('UNKNOWN','EXPLICIT_ROLE_CONTRADICTION')][:4]
        candidates=[];rejected=[]
        for endpoint in endpoints:
            support=task_role(model,endpoint,task);supported=support['status']!='UNKNOWN'
            if support['status']=='EXPLICIT_ROLE_CONTRADICTION':
                rejected.append(dict(endpoint=endpoint,reason='EXPLICIT_ROLE_CONTRADICTION',support=support));continue
            # A failed bounded attempt defers this endpoint at this observation,
            # not forever and not as an assertion of global infeasibility.
            key=digest([task,endpoint,physical_key(model,text)])
            if m.outcome_deferred.get(key,0)>step:continue
            plan=model.acquisition(endpoint,max_nodes=1500,seconds=.25)
            event=None;actions=plan.get('plan') or []
            if plan.get('status')=='acquired':
                # Possession is not success. The ordinary actor must address the
                # remaining task predicates instead of acquiring another copy.
                rejected.append(dict(endpoint=endpoint,reason='ENDPOINT_HELD_TASK_FEEDBACK_REQUIRED'));continue
            if plan.get('status')!='candidate' or not actions:
                review=self.review_proposal(dict(action='craft 1 '+endpoint,frame={'goal_quote':task}),text)
                event=self.compile_repair(review,text,step) if review else None
                if event:actions=event['endpoint_preview']['plan']
                elif plan.get('status')=='observe_container' and actions:
                    # Observation is a prerequisite, not a completed endpoint path.
                    rejected.append(dict(endpoint=endpoint,reason='STALE_CONTENTS',observe=actions[0]));continue
                else:continue
            reserve=reserve_check(model,task,endpoint,actions)
            # Keep one action for obtaining task feedback; this still does not
            # certify navigation, hidden rules or an entire quest suffix.
            if len(actions)+1>remaining:
                rejected.append(dict(endpoint=endpoint,reason='CANDIDATE_EXCEEDS_REMAINING_BUDGET'));continue
            if reserve['status']=='JOINT_WITNESS_NOT_REESTABLISHED':
                rejected.append(dict(endpoint=endpoint,reason='DEFER_UNCERTIFIED_RESOURCE_DISPLACEMENT',reserve=reserve));continue
            # Unknown roles may be explored, but never receive an open-ended
            # autonomous commitment. This is an explicit heuristic, not a bound.
            if not supported and len(actions)+1>min(24,remaining):
                rejected.append(dict(endpoint=endpoint,reason='UNSUPPORTED_ROLE_EXCEEDS_TRIAL_ALLOWANCE'));continue
            candidates.append(dict(endpoint=endpoint,task=task,support=support,role_supported=supported,
                reserve=reserve,plan=actions,repair=event,cost=len(actions)+1,key=key,
                qualification='Conditional endpoint plan, not task-completion probability or certificate'))
        candidates.sort(key=lambda c:(not c['role_supported'],c['reserve']['status']=='UNKNOWN',c['cost'],c['endpoint']!=original,c['endpoint']))
        return candidates,rejected

    def decision(self,focus,text,step):
        choices,rejected=self.alternatives(focus,text,step)
        row=dict(step=step,focus=focus,candidates=choices,rejected=rejected,
            chosen=choices[0] if choices else None,objective='Task support and retained material opportunities before endpoint cost; success judged only by environment feedback')
        self.memory.outcome_decisions.append(row)
        return row

    def emit_choice(self,choice,step):
        m=self.memory;task=choice['task'];target=choice['endpoint']
        m.outcome_focus=dict(task=task,target=target)
        m.outcome_lease=dict(task=task,target=target,created=step,allowance=min(24,choice['cost']+4),
            visited={},support=choice['support'])
        self.chosen_step=step
        if choice['repair']:
            return self.activate(choice['repair'],step)
        m.resource_target=target;m.resource_started=step;m.resource_fresh=False
        return dict(action=choice['plan'][0],reasoning='Execute a task-supported continuation, preserving known remaining material opportunities.',
            decision_source='task_outcome_selection',outcome_choice=choice,resource_target=target,
            frame={**m.frame,'goal_quote':task,'method':'Acquire '+target+' for the original task; verify actual task feedback.'})

    def bounded_probe(self,focus,text,step):
        """One grounded observation for a concrete uncertainty; never generic look."""
        m=self.memory;model=m.model;target=focus['target'];state=model.current
        visible=set(state.get('holding') or {})|set(state.get('ground') or {})|set(state.get('equipped') or {})
        names=[n for n in sorted(visible) if base_name(n)==base_name(target)]
        names += [n for n in sorted(visible) if n in model.containers and model.containers[n].get('uncertain_after_craft')]
        for name in names:
            signature=digest([focus,name,model.documents.get(name),model.containers.get(name),
                [l for l in model.source_lines if l.startswith('I inspected '+name+':')]])
            # Same unresolved interpretation receives at most one paid query.
            if any(p['signature']==signature for p in m.outcome_probes):continue
            event=dict(step=step,signature=signature,task=focus['task'],target=target,action='inspect '+name,
                purpose='Resolve endpoint role or stale accessible contents before committing')
            m.outcome_probes.append(event);m.resource_target='';self.chosen_step=step
            return dict(action=event['action'],reasoning=event['purpose'],decision_source='task_outcome_observation',
                outcome_probe=event,frame={**m.frame,'goal_quote':focus['task']})
        return None

    def release(self,text,step,reason):
        m=self.memory;lease=m.outcome_lease;focus=m.outcome_focus
        if focus:
            key=digest([focus['task'],focus['target'],physical_key(m.model,text)])
            m.outcome_deferred[key]=step+8
        m.outcome_decisions.append(dict(step=step,status='RELEASED',reason=reason,lease=copy.deepcopy(lease)))
        self.stop(reason,step);m.outcome_lease=None;m.resource_target='';m.resource_trial_state=None;self.session=None

    def method_condition_step(self,text,step):
        if self.action_mode!='execute':return super().method_condition_step(text,step)
        m=self.memory;focus=m.outcome_focus
        if not focus:return None
        if focus['task'] not in self.view().tasks:
            self.release(text,step,'TASK_REPORTED_OR_CHANGED');m.outcome_focus=None;return None
        if 'I was attacked' in text:return super().method_condition_step(text,step) if m.action_program else None
        lease=m.outcome_lease
        if lease:
            key=physical_key(m.model,text);lease['visited'][key]=lease['visited'].get(key,0)+1
            failed=bool(re.search(r'^Cannot ',text,re.M)) and m.last_action and m.last_action.startswith(('craft ','take out ','pick up ','store ','enter '))
            contradicted=task_role(self.view(),focus['target'],focus['task'])['status']=='EXPLICIT_ROLE_CONTRADICTION'
            if failed or contradicted or lease['visited'][key]>2 or step-lease['created']>=lease['allowance']:
                self.release(text,step,'OBSERVED_FAILURE_OR_NO_TASK_PROGRESS');lease=None
            elif m.action_program:return super().method_condition_step(text,step)
            else:return None  # Existing executor follows this bounded endpoint.
        row=self.decision(focus,text,step)
        if row['chosen']:return self.emit_choice(row['chosen'],step)
        m.resource_target=''
        return self.bounded_probe(focus,text,step)

    def certified_repair(self,review,text,step):
        # Guarded rejection is another entrance to the SAME choice rule. It
        # must not activate V14's capacity-only program around the new gate.
        if self.action_mode!='execute':return super().certified_repair(review,text,step)
        focus=dict(task=review.get('original_task',''),target=review['action'].split()[-1])
        if focus['task'] not in self.view().tasks:return None
        row=self.decision(focus,text,step)
        return self.emit_choice(row['chosen'],step) if row['chosen'] else self.bounded_probe(focus,text,step)

    def select_proposal(self,parsed,text,step,raw_query,prompt):
        if self.action_mode!='execute':return super().select_proposal(parsed,text,step,raw_query,prompt)
        self.assess(parsed,step,'task_outcome_before_acquisition')
        focus=self.focus(parsed)
        if not focus or 'I was attacked' in text:return parsed
        if not parsed['action'].startswith('craft ') and not parsed.get('resource_target'):return parsed
        row=self.decision(focus,text,step);self.memory.outcome_focus=focus
        if row['chosen']:return self.emit_choice(row['chosen'],step)
        # Missing support is uncertainty. No extra reconsideration call or hard
        # global action ban: use a relevant observation when available.
        return self.bounded_probe(focus,text,step) or parsed

    def finalize_decision(self,parsed,text,step,raw_query,prompt):
        if self.action_mode!='execute':return super().finalize_decision(parsed,text,step,raw_query,prompt)
        # The base acquisition solver may introduce a craft after selection.
        # Apply the same remaining-obligation check to the ACTUAL consuming step.
        if not parsed['action'].startswith('craft '):return parsed
        focus=self.focus(parsed) or self.memory.outcome_focus
        if not focus:return parsed
        reserve=reserve_check(self.view(),focus['task'],focus['target'],[parsed['action']])
        parsed['outcome_reserve_check']=reserve
        if reserve['status']!='JOINT_WITNESS_NOT_REESTABLISHED':return parsed
        self.release(text,step,'CONSUMPTION_LACKS_REMAINING_TASK_WITNESS')
        row=self.decision(focus,text,step)
        revised=self.emit_choice(row['chosen'],step) if row['chosen'] else self.bounded_probe(focus,text,step)
        # With no grounded substitute, defer to the actor once at its next turn;
        # a safe non-consuming observation of an actually visible ingredient is
        # an explicit charged fallback, not claimed information gain.
        if not revised:
            visible=sorted(set(self.memory.model.current.get('holding') or {})|set(self.memory.model.current.get('ground') or {}))
            if visible:revised=dict(action='inspect '+visible[0],reasoning='Defer resource consumption pending a supported remaining-task continuation.',
                frame=parsed.get('frame',{}),decision_source='task_outcome_resource_deferral')
        return revised or parsed


class TaskOutcomeAgent(ActionRepairAgent):
    def __init__(self,llm,system_prompt):
        super().__init__(llm,system_prompt)
        self.notebook=OutcomeMemory();self.resource_controller=OutcomeController(self.notebook)
