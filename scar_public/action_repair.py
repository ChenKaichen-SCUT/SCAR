"""V14: compile a grounded obstruction into an observation-checked action program.

No extra language call. The trigger is a scoped real-feedback rejection; the
program repairs an observed capability and then reacquires the SAME endpoint.
It is a conditional execution proposal, not a certified whole-task policy.
"""
import copy,re
from scar_public.intent_repair import IntentMemory,IntentController,IntentRepairAgent
from scar_public.method_repair import task_binding,observed_loss_sites,route_to
from scar_public.causal_model import digest
from scar_public.obligations import words


def capacity_candidates(memory,target,conditions,text,step):
    """Compile only non-consuming capability repairs, using public evidence."""
    model=memory.model;s=model.current
    if 'I was attacked' in text:return [],'AMBIENT_COMBAT'
    profiles=conditions.get('profiles',[])
    if not conditions.get('capacity_is_exact') or not profiles:return [],'NO_EXACT_CAPACITY_OBSTRUCTION'
    if not all(r['capacity_shortfall']>0 and not any(r['total_material_deficit'].values()) for r in profiles):
        return [],'NOT_A_PURE_ACCESSIBLE_CAPACITY_GAP'
    held=s.get('holding');floor=s.get('ground');eq=s.get('equipped')
    if held is None or floor is None or eq is None:return [],'INCOMPLETE_CURRENT_STATE'
    required={n for r in profiles for n in r['required']}
    required_total=max(sum(r['required'].values()) for r in profiles)/1000
    candidates=[]
    for name,bag in model.containers.items():
        proof=next((l for l in reversed(model.source_lines) if l=='I equipped '+name+' as inventory.'),None)
        if not proof or eq or bag.get('uncertain_after_craft'):continue
        background=max(0,bag.get('used',0)-sum(v for n,v in bag['items'].items() if n in required))
        if model.hand_capacity+bag['capacity']-background<required_total:continue
        if held.get(name):path=[];loc=s['location'];action='equip '+name;retrieval=1
        else:
            locations=[l for l,r in model.locations.items() if r['objects'].get(name)]
            locations+=observed_loss_sites(memory,name)
            if floor.get(name):locations.append(s['location'])
            routes=[(route_to(model,l),l) for l in set(locations)]
            routes=[(p,l) for p,l in routes if p is not None and (p or floor.get(name))]
            if not routes:continue
            path,loc=min(routes,key=lambda x:(len(x[0]),x[1]))
            full=sum(held.values())+1>model.hand_capacity
            if full:
                choices=sorted((n for n,v in held.items() if v>=1),key=lambda n:(n in required,n))
                if not choices:continue
                action='drop '+choices[0]
            else:action=path[0] if path else 'pick up '+name
            retrieval=len(path)+2+int(full)
        # One paid inspection after attachment; at least craft+pickup remain.
        lower_work=retrieval+1+2
        if step+lower_work>300:continue
        signature=digest([target,action,s,bag,model.routes()])
        if signature in memory.action_attempts:continue
        candidates.append(dict(action=action,container=name,location=loc,route=path,
            conditional_retrieval_actions=retrieval,minimum_remaining_actions=lower_work,
            required_input_total=required_total,optimistic_joint_capacity=model.hand_capacity+bag['capacity']-background,
            capability_quote=proof,signature=signature,
            resource_effect='No modeled material consumption; dropped material remains at its observed location',
            qualification='Conditional retrieval; remembered location, navigation, survival and remaining craft semantics are not guaranteed'))
    return sorted(candidates,key=lambda r:(r['conditional_retrieval_actions'],r['container'])),None


def acknowledged(action,text):
    checks=(('drop ','I dropped '),('pick up ','I picked up '),('enter ','I entered '),
            ('equip ','I equipped '),('inspect ','I inspected '))
    for prefix,report in checks:
        if action.startswith(prefix):
            ending=':' if prefix=='inspect ' else ' as inventory\\.' if prefix=='equip ' else '\\.'
            return bool(re.search('^'+re.escape(report+action[len(prefix):])+ending,text,re.M))
    if action.startswith('craft '):return bool(re.search('^'+re.escape('I successfully crafted '+action[6:])+r'\.',text,re.M))
    if action.startswith(('store ','take out ')):
        from scar_public.resource_trial import public_outcome
        return public_outcome(text,action)=='success'
    return False


class ActionMemory(IntentMemory):
    def __init__(self):
        super().__init__();self.action_program=None;self.action_compilations=[]
        self.action_events=[];self.action_attempts=[];self.action_outcomes=[]
        self.action_goal_bindings={}

    def update(self,parsed,observation,step):
        from scar_public.intent_repair import task_view,proposed_intent
        view=task_view(self.model,self.intent_tasks)
        intent=proposed_intent(view,parsed,self.intent_anchors)
        task=intent['task'] or task_binding(view,parsed,intent['target'])
        if task:
            for target in {intent['target'],intent['endpoint']} - {''}:
                self.action_goal_bindings[target]=dict(task=task,step=step,
                    qualification='Recorded actor method-to-task intention, not proof of task sufficiency')
        super().update(parsed,observation,step)


class ActionController(IntentController):
    action_mode='execute'

    def review_proposal(self,parsed,text):
        review=super().review_proposal(parsed,text)
        if review:
            target=review['action'].split()[-1];view=self.view()
            task=task_binding(view,parsed,target)
            saved=self.memory.action_goal_bindings.get(target,{})
            if not task and saved.get('task') in view.tasks:task=saved['task']
            review['original_task']=task
        return review

    def compile_repair(self,review,text,step):
        target=review['action'].split()[-1];task=review.get('original_task','')
        if not task or task not in self.view().tasks:return None
        choices,gap=capacity_candidates(self.memory,target,review.get('enabling_conditions',{}),text,step)
        event=dict(step=step,target=target,task=task,evidence=copy.deepcopy(review),candidates=choices,gap=gap,
            chosen=choices[0] if choices else None)
        self.memory.action_compilations.append(event)
        return event if choices else None

    def activate(self,event,step):
        choice=event['chosen'];m=self.memory
        m.action_program=dict(target=event['target'],task=event['task'],created=step,
            container=choice['container'],trigger=event['evidence'],phase='retrieve',refreshed=False,
            pending=None,used=0,assumptions=choice['qualification'])
        m.resource_target='';m.resource_fresh=False
        return self.emit(choice['action'],step,'capacity_retrieval',choice)

    def emit(self,action,step,phase,certificate):
        m=self.memory;p=m.action_program;p['pending']=action;p['used']+=1
        if 'signature' in certificate:m.action_attempts.append(certificate['signature'])
        event=dict(step=step,action=action,target=p['target'],task=p['task'],phase=phase,
            certificate=copy.deepcopy(certificate),extra_llm_calls=0)
        m.action_events.append(event)
        return dict(action=action,decision_source='evidence_action_program',action_certificate=event,
            reasoning='Execute the first checked action that restores the missing observed condition; inspect actual feedback before continuing.',
            frame={**m.frame,'goal_quote':p['task'],'method':'Restore observed accessible capacity, then acquire '+p['target'],
                   'expected':'Actual observation must confirm the primitive action; acquiring the output is not assumed to finish the task.'})

    def stop(self,reason,step):
        p=self.memory.action_program
        if p:self.memory.action_outcomes.append(dict(step=step,reason=reason,program=copy.deepcopy(p)))
        self.memory.action_program=None;self.memory.resource_target=''

    def prepare_decision(self,text,step):
        # Preserve the target before the inherited obstruction notice clears it.
        target=self.memory.resource_target
        if not target:
            method=self.memory.frame.get('method','').lower().replace('_',' ')
            mentioned=[n for n,b in self.memory.action_goal_bindings.items() if b['task'] in self.view().tasks and
                re.search(r'\b'+re.escape(words(n))+r'\b',method)]
            if mentioned:target=max(mentioned,key=lambda n:self.memory.action_goal_bindings[n]['step'])
        result=super().prepare_decision(text,step)
        self.prepared=None
        if not self.memory.action_program and target:
            review=self.review_proposal(dict(action='craft 1 '+target,frame=self.memory.frame),text)
            if review:self.prepared=self.compile_repair(review,text,step)
        return result

    def certified_repair(self,review,text,step):
        # Same local solver in both arms; the new mechanism only fills the
        # explicit ENABLING_CONDITION_REQUIRED gap left by that solver.
        local=super().certified_repair(review,text,step)
        if local:return local
        event=self.compile_repair(review,text,step)
        if event and self.action_mode=='execute':return self.activate(event,step)
        return None

    def method_condition_step(self,text,step):
        m=self.memory;p=m.action_program
        if not p:
            if getattr(self,'prepared',None) and self.action_mode=='execute':return self.activate(self.prepared,step)
            return None
        if p['task'] in self.view().completed:self.stop('PUBLIC_TASK_COMPLETION',step);return None
        if p['task'] not in self.view().tasks:self.stop('TASK_NO_LONGER_ACTIVE',step);return None
        if step-p['created']>=24 or p['used']>=24 or step>=300:
            self.stop('BOUNDED_PROGRAM_EXPIRED',step);return None
        if p['pending']:
            if m.last_action!=p['pending'] or not acknowledged(p['pending'],text):
                self.stop('EXECUTION_NOT_CONFIRMED',step);return None
            if p['pending']=='inspect '+p['container']:p['refreshed']=True
            p['pending']=None
        if 'I was attacked' in text:
            # Combat invalidates a resource-only execution guarantee. Yield this
            # turn to the actor, but do not forget the repaired capability/task.
            # Resumption is conditional on a later fresh non-combat observation.
            m.action_outcomes.append(dict(step=step,reason='PAUSED_FOR_COMBAT',target=p['target']))
            return None
        model=m.model;s=model.current;name=p['container']
        held=s.get('holding') or {};floor=s.get('ground') or {}
        if held.get(p['target'],0)>=1:self.stop('OUTPUT_HELD_TASK_FEEDBACK_STILL_REQUIRED',step);return None
        if floor.get(p['target'],0)>=1 and model.hand_capacity is not None and sum(held.values())+1<=model.hand_capacity:
            return self.emit('pick up '+p['target'],step,'observed_output_pickup',dict(public_floor_quantity=floor[p['target']]))
        if (s.get('equipped') or {}).get(name):
            if not p['refreshed'] or model.containers[name].get('uncertain_after_craft'):
                return self.emit('inspect '+name,step,'paid_contents_observation',dict(container=name))
            p['phase']='acquire'
            plan=model.acquisition(p['target'])
            if plan['status']=='acquired':self.stop('OUTPUT_HELD_TASK_FEEDBACK_STILL_REQUIRED',step);return None
            if plan.get('plan') and len(plan['plan'])<=300-step:
                return self.emit(plan['plan'][0],step,'same_endpoint_acquisition',plan)
            self.stop('NO_EXECUTABLE_CONTINUATION',step);return None
        choices,gap=capacity_candidates(m,p['target'],p['trigger']['enabling_conditions'],text,step)
        chosen=next((c for c in choices if c['container']==name),None)
        if chosen:return self.emit(chosen['action'],step,'capacity_retrieval',chosen)
        self.stop(gap or 'CAPABILITY_ROUTE_NO_LONGER_AVAILABLE',step);return None


class ActionRepairAgent(IntentRepairAgent):
    def __init__(self,llm,system_prompt):
        super().__init__(llm,system_prompt)
        self.notebook=ActionMemory();self.resource_controller=ActionController(self.notebook)
