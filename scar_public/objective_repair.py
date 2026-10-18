"""Verify the proposed blocker change separately from action execution.

The requirement catalog is computed before candidate generation. A candidate
chooses a requirement and a method, not its own definition of success. False
and unknown results schedule bounded replanning from the actual observation.
No game-specific entity, hidden simulator, or new resource-protection module.
"""
import copy
import json

from scar_public.causal_model import digest
from scar_public.continuation import PROTECTED, feedback_lines, task_key, threatened
from scar_public.hypothesis_repair import (
    HypothesisRepairAgent, INSTRUCTION, check_steps, command_parts, evaluate,
    required_reserves, validate,
)
from scar_public.obstacle_repair import missing_requirements
from scar_public.public_model import state_from_text


def requirement_catalog(memory, original, goals, evidence):
    """Finite task/recipe fragment, not a complete natural-language task model."""
    result=[]
    for target, need in missing_requirements(memory, original, goals).items():
        result.append(dict(kind='resource', target=target, count=need['count'],
                           support=need['support'], depth=need['depth']))
    # Access is an admissible subproblem only for an actually failed entrance.
    # Merely choosing another room cannot relabel resource search as access repair.
    for record in evidence.records[-6:]:
        action=record['action']
        if (action.startswith('enter ') and record['feedback'] and
            record['before'].get('location')==evidence.current.get('location') and
            record['after'].get('location')==record['before'].get('location')):
            result.append(dict(kind='access',target=action[6:],count=1,
                               support=record['feedback'],source=record['before']['location']))
    unique={}
    for need in result:
        key=digest([need['kind'],need['target'],need['count'],need.get('source')])[:12]
        unique[key]=dict(need,id=key)
    return list(unique.values())


def at_site(state, site):
    location=state.get('location')
    return location is not None and site in (location,location.split(', ')[-1])


def compile_verification(candidate, needs):
    need=next((n for n in needs if n['id']==candidate.get('need_id')),None)
    if not need:return None,['UNKNOWN_REQUIREMENT']
    spec=candidate.get('verification')
    if not isinstance(spec,dict):return None,['MISSING_REQUIREMENT_VERIFICATION']
    mode=spec.get('mode');steps=candidate.get('steps',[])
    if not steps:return None,['INVALID_PLAN_LENGTH']
    if mode in ('source','acquire') and need['kind']=='resource':
        test=dict(kind='visible' if mode=='source' else 'held',target=need['target'],count=need['count'])
        if mode=='source':
            site=spec.get('site')
            if not isinstance(site,str) or not site:return None,['SOURCE_LOCATION_REQUIRED']
            test['location']=site
        return dict(mode=mode,need=copy.deepcopy(need),test=test),[]
    if mode=='access' and need['kind']=='access':
        return dict(mode=mode,need=copy.deepcopy(need),test=dict(kind='at',target=need['target'])),[]
    if mode=='information' and steps[-1].get('test',{}).get('kind') in ('report','contained'):
        return dict(mode=mode,need=copy.deepcopy(need),test=steps[-1]['test']),[]
    return None,['VERIFICATION_DOES_NOT_MATCH_REQUIREMENT']


def check_objective(compiled, text, memory):
    """Return facts about the promised condition, not just arrival/acknowledgment."""
    state=state_from_text(text);need=compiled['need'];mode=compiled['mode']
    held=state.get('holding');resolved=None
    if need['kind']=='resource':
        resolved=None if held is None else held.get(need['target'],0)>=need['count']
    elif mode=='access':resolved=evaluate(compiled['test'],text)
    if mode=='source':
        test=compiled['test'];site=test['location']
        deficit=max(0,need['count']-(held or {}).get(need['target'],0))
        if not at_site(state,site) or state['ground'] is None:outcome=None
        else:outcome=state['ground'].get(need['target'],0)>=deficit
        room=(held is not None and (memory.model.capacity_upper is None or
                                  sum(held.values())+1<=memory.model.capacity_upper))
        can_pick=bool(outcome and room and not resolved)
        return dict(outcome=outcome,requirement_resolved=resolved,source_location=state['location'],
                    observed_quantity=None if state['ground'] is None else state['ground'].get(need['target'],0),
                    required_ground_quantity=deficit,
                    acquisition_possible_under_known_checks=can_pick,
                    status='REQUIREMENT_MET' if resolved else 'SOURCE_OBSERVED' if outcome else
                           'SOURCE_NOT_OBSERVED' if outcome is False else 'UNRESOLVED_OBSERVATION')
    outcome=evaluate(compiled['test'],text)
    return dict(outcome=outcome,requirement_resolved=resolved,
                status=('REPORT_MATCHED' if mode=='information' else 'REQUIREMENT_MET') if outcome is True else
                       'EXPECTED_CONDITION_ABSENT' if outcome is False else 'UNRESOLVED_OBSERVATION')


class TrialEvidence:
    """Scoped trial outcomes; an absence at one site is not global impossibility."""
    def __init__(self):self.records=[];self.revision=0

    def add(self, program, result, text, step):
        objective=program['objective'];state=state_from_text(text)
        record=dict(id=len(self.records),step=step,task=program['task'],goal=program['goal_quote'],
            need=objective['need'],mode=objective['mode'],test=objective['test'],
            plan=[s['action'] for s in program['steps']],outcome=result['outcome'],
            requirement_resolved=result['requirement_resolved'],status=result['status'],
            location=state['location'],holding=state['holding'],equipped=state['equipped'],
            ground_quantity=None if state['ground'] is None else state['ground'].get(objective['need']['target'],0),
            observation=text,expiry=step+24)
        self.records.append(record);self.revision+=1
        return record

    def active(self, task, memory, step):
        result=[]
        for record in self.records[-32:]:
            if record['task']!=task or step>record['expiry']:continue
            if record['mode']=='source' and record['outcome'] is False:
                # Unrelated clock text, food or inventory changes do not erase a
                # source observation; a changed count of THIS resource revokes it.
                listing=memory.model.locations.get(record['location'],{})
                if listing.get('objects',{}).get(record['need']['target'],0)!=record['ground_quantity']:continue
                held=memory.model.current.get('holding') or {}
                if held.get(record['need']['target'],0)+record['ground_quantity']>=record['need']['count']:continue
            result.append(record)
        return result

    def objections(self, program, memory, step):
        objective=program['objective'];need=objective['need'];errors=[]
        for record in self.active(program['task'],memory,step):
            if record['need']['id']!=need['id']:continue
            if objective['mode']=='source' and record['mode']=='source' and record['outcome'] is False:
                if objective['test']['location'] in (record['location'],record['location'].split(', ')[-1]):
                    errors.append(dict(reason='SOURCE_RECENTLY_TESTED_ABSENT',trial_id=record['id']))
            # UNKNOWN is not a false fact. It only says an identical experiment
            # in the same carried/location state needs a changed method or evidence.
            elif record['outcome'] is None and record['plan']==[s['action'] for s in program['steps']]:
                current=memory.model.current
                quantity=None if current.get('ground') is None else current['ground'].get(need['target'],0)
                if all(current.get(k)==record[k] for k in ('location','holding','equipped')) and quantity==record['ground_quantity']:
                    errors.append(dict(reason='UNCHANGED_UNRESOLVED_TRIAL',trial_id=record['id']))
        return errors


OBJECTIVE_INSTRUCTION='''
Each hypothesis must also contain need_id (one requirement id from the packet)
and verification:{mode:source|acquire|access|information,site:ROOM_FOR_SOURCE}.
Requirements are computed BEFORE your plan. You may select a relevant one but
cannot redefine its target/count or substitute arrival for a missing resource.
source: explore a publicly named location for the requirement's material; the
system checks its ACTUAL ground quantity there, not whether movement succeeded.
acquire: obtain the required quantity in hand. access: reach the specified
observed blocked entrance, not merely any other room. information: an explicit
report with two concrete decision branches as in the schema above; a report
match is not fulfillment of the resource/access requirement.
Step tests are ONLY execution milestones. Terminal verification is separately
compiled from the selected requirement. Prefer source when the route is known
but the resource presence is unverified. Unknown sources remain eligible.
After a trial, use its actual outcome to revise the SAME unmet requirement:
change the proposed source, access method, or way to observe the condition.
Do not repeat a recently empty source because unrelated facts changed. Unknown
visibility is not absence. Do not invent a solution or broaden the task when
none is justified. Retain the actor's action if no better plan survives.
'''


class ObjectiveRepairAgent(HypothesisRepairAgent):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.trial_evidence=TrialEvidence();self.revision_due=None

    def proposals(self,response,task,goals,needs,remaining,step):
        if 'hypotheses' not in response:return [],[dict(reasons=['MISSING_HYPOTHESES_FIELD'])]
        candidates=response.get('hypotheses',[]);accepted=[];rejected=[]
        if not isinstance(candidates,list):return [],[dict(reasons=['HYPOTHESES_MUST_BE_A_LIST'])]
        for candidate in candidates[:2]:
            program,reasons=validate(candidate,self.notebook,self.continuation,task,goals,
                self.hypothesis_attempts,self.observed_uses,remaining)
            objective=None
            if program:objective,reasons=compile_verification(candidate,needs)
            if program and objective:
                program['objective']=objective
                projected=program['checks']['projected']
                if objective['mode'] in ('source','access'):
                    site=objective['test'].get('location',objective['test']['target'])
                    last_entry=next((s['action'][6:] for s in reversed(program['steps']) if s['action'].startswith('enter ')),None)
                    # Unknown route effects may be tested, but a plan ending at
                    # an unrelated room cannot claim to test this destination.
                    if not (at_site(projected,site) or last_entry==site.split(', ')[-1]):
                        reasons=['SOURCE_NOT_REACHED_BY_PLAN' if objective['mode']=='source' else 'ACCESS_NOT_REACHED_BY_PLAN']
                elif objective['mode']=='acquire':
                    held=projected.get('holding')
                    need=objective['need']
                    if held is not None and held.get(need['target'],0)<need['count']:
                        reasons=['ACQUISITION_NOT_REACHED_BY_PLAN']
                if not reasons:reasons=self.trial_evidence.objections(program,self.notebook,step)
            if program and objective and not reasons:accepted.append(program)
            else:rejected.append(dict(candidate=candidate,reasons=reasons))
        return accepted,rejected

    def assess_pending(self,obs,step,task):
        pending=self.hypothesis_pending;self.hypothesis_pending=None
        if not pending:return None,None
        program=pending['program'];index=pending['index'];text=obs['text']
        execution=evaluate(program['steps'][index]['test'],text);failures=feedback_lines(text)
        terminal=index==len(program['steps'])-1
        result=dict(step=step,contract=program,index=index,execution_outcome=execution,
            outcome=None,requirement_resolved=None,terminal=terminal,failures=failures,
            admitted=False,decision_distinguishing=False,cancellation_reasons=[])
        follow=None
        if terminal:
            result.update(check_objective(program['objective'],text,self.notebook))
            if failures and program['objective']['mode']=='information':result.update(outcome=None,status='UNRESOLVED_OBSERVATION')
        elif execution is True and not failures:
            follow=dict(program=program,index=index+1)
            result['status']='EXECUTION_MILESTONE_ONLY'
        else:
            result['status']='PLAN_EXECUTION_FAILED';result['cancellation_reasons'].append('STEP_EFFECT_NOT_OBSERVED')
        if program['task']!=task:
            result['cancellation_reasons'].append('TASK_CHANGED');follow=None
        elif terminal or follow is None:
            trial=self.trial_evidence.add(program,result,text,step);result['trial_id']=trial['id']
            if result['requirement_resolved'] is not True:
                self.revision_due=trial
            elif self.revision_due and self.revision_due['need']['id']==program['objective']['need']['id']:
                self.revision_due=None
            # A confirmed source can select acquisition; arrival alone cannot.
            if terminal and result.get('acquisition_possible_under_known_checks'):
                need=program['objective']['need'];count=(state_from_text(text)['holding'] or {}).get(need['target'],0)+1
                acquisition=dict(action='pick up '+need['target'],test=dict(kind='held',target=need['target'],count=count))
                continued={**program,'steps':[acquisition],'information':False,'branches':None,
                    'objective':dict(mode='acquire',need=need,test=dict(kind='held',target=need['target'],count=need['count']))}
                follow=dict(program=continued,index=0);result['decision_distinguishing']=True
            elif terminal and program['information'] and result['outcome'] is not None and not failures:
                branch=program['branches'][str(result['outcome']).lower()]
                continued={**program,'steps':[branch],'information':False,'branches':None}
                # The follow-up is checked against the original unmet need, not
                # against the report predicate again.
                need=program['objective']['need']
                continued['objective']=dict(mode='acquire' if need['kind']=='resource' else 'access',need=need,
                    test=dict(kind='held' if need['kind']=='resource' else 'at',target=need['target'],count=need['count']))
                follow=dict(program=continued,index=0);result['decision_distinguishing']=True
        self.obstacle_outcomes.append(result)
        return result,follow

    def finalize_decision(self,executed,obs,step,prompt,query):
        evidence=self.continuation;task=task_key(self.notebook);self.observe_use(obs['text'])
        event=dict(step=step,original=executed['action'],changed=False,trigger=None)
        result,follow=self.assess_pending(obs,step,task)
        if result:event['previous_repair']=result
        urgent=threatened(obs['text']) or executed['action'].startswith(PROTECTED)
        if follow and not urgent:
            program=follow['program'];index=follow['index']
            checked=check_steps(program['steps'][index:],self.notebook,evidence,task,
                required_reserves(self.notebook,[program['goal_quote']]),self.observed_uses)
            result['continuation_check']=checked;result['cancellation_reasons']+=checked['errors']
            if not result['cancellation_reasons']:
                action=program['steps'][index]['action'];result.update(admitted=True,proposed_continuation=action)
                event.update(reason='VERIFIED_CONDITION_SELECTS_CONTINUATION',changed=action!=executed['action'])
                if event['changed']:executed=self.replace(executed,action,program['goal_quote'],program['hypothesis'])
                self.hypothesis_pending=follow
                return self.finish(executed,event,task)
        elif follow and urgent:
            result['cancellation_reasons'].append('URGENT_ACTION_YIELD')
            if not result['terminal']:
                result['status']='INTERRUPTED_BEFORE_VERIFICATION'
                self.revision_due=self.trial_evidence.add(follow['program'],result,obs['text'],step)
        if self.revision_due and (self.revision_due['task']!=task or step>self.revision_due['expiry']):self.revision_due=None
        trigger=self.repair_trigger(executed['action'],task)
        revision=self.revision_due
        if revision:trigger=dict(kind='UNRESOLVED_REPAIR_REQUIREMENT',trial_id=revision['id'],status=revision['status'])
        event['trigger']=trigger
        if trigger and self.repair_mode!='off' and not urgent:
            context=evidence.context(executed['action'],task)
            query_limit=12 if revision else 10  # reserve two calls for real trial feedback
            if len(self.hypothesis_queries)>=12:event['reason']='REPAIR_QUERY_BUDGET'
            elif len(self.hypothesis_queries)>=query_limit:event['reason']='RESERVED_FOR_TRIAL_REVISION'
            elif not revision and any(q['context']==context and q['action']==executed['action'] and step-q['step']<=6 for q in self.hypothesis_queries):
                event['reason']='RECENT_QUERY_SAME_CONTEXT'
            else:
                goals=list(dict.fromkeys(r['quote'] for r in self.notebook.progress_tasks.values()))
                quote=executed.get('frame',{}).get('goal_quote','')
                if len(quote)>=12 and any(quote in t for t in self.notebook.observations):goals=list(dict.fromkeys([quote]+goals))
                needs=requirement_catalog(self.notebook,executed,goals,evidence)
                if revision:
                    needs=[revision['need']];goals=[revision['goal']]
                if goals and needs:
                    packet=dict(original=executed['action'],trigger=trigger,goals=goals,requirements=needs,
                        current=self.notebook.model.current,remaining_actions=self.max_steps-step,
                        capacity_upper=self.notebook.model.capacity_upper,
                        reserved_resources=required_reserves(self.notebook,goals),observed_uses=self.observed_uses[-6:],
                        trial_evidence=self.trial_evidence.active(task,self.notebook,step),
                        revision_of=revision['id'] if revision else None)
                    base=prompt+'\nObstacle hypothesis proposals:\n'+json.dumps(packet,ensure_ascii=False)+INSTRUCTION+OBJECTIVE_INSTRUCTION
                    response=query(base);self.hypothesis_queries.append(dict(context=context,action=executed['action'],step=step))
                    accepted,rejected=self.proposals(response,task,goals,needs,self.max_steps-step,step)
                    if not accepted and not rejected and response.get('action')!=executed['action']:
                        rejected=[dict(reasons=['ALTERNATIVE_WITHOUT_STRUCTURED_HYPOTHESIS'])]
                    event.update(packet=packet,proposal=response,programs=accepted,program_rejections=rejected,proposal_calls=1)
                    if not accepted and rejected and len(self.hypothesis_queries)<query_limit:
                        event.update(initial_proposal=response,initial_rejections=rejected)
                        response=query(base+'\nOne correction attempt. Use actual state and the fixed requirement. '+
                            'Correct the specific rejected claims/steps; do not restate them.\n'+json.dumps(dict(
                            rejected=rejected,current_observed_state=self.notebook.model.current,current_observation=obs['text']),ensure_ascii=False))
                        self.hypothesis_queries.append(dict(context=context,action=executed['action'],step=step,revision=True))
                        accepted,rejected=self.proposals(response,task,goals,needs,self.max_steps-step,step)
                        event.update(proposal=response,programs=accepted,program_rejections=rejected,proposal_calls=2)
                    # A failed trial causes one bounded revision event, not an
                    # unlimited query loop. Its evidence persists for later triggers.
                    self.revision_due=None
                    matching=next((p for p in accepted if p['steps'][0]['action']==response.get('action')),None)
                    if response.get('action')==executed['action'] and not matching:event['reason']='ACTOR_RETAINS_ORIGINAL'
                    elif accepted:
                        choice=matching or accepted[0]
                        action=choice['steps'][0]['action']
                        event.update(reason='REQUIREMENT_BOUND_HYPOTHESIS',contract=choice,changed=action!=executed['action'])
                        self.hypothesis_attempts.append(choice);self.hypothesis_pending=dict(program=choice,index=0)
                        if event['changed']:executed=self.replace(executed,action,choice['goal_quote'],choice['hypothesis'])
                    else:event['reason']='NO_ADMITTED_HYPOTHESIS'
                else:event['reason']='NO_COMPUTABLE_REQUIREMENT'
        return self.finish(executed,event,task)

    def observe_terminal(self,obs):
        # No LLM call or new action; include the final executed trial's outcome.
        super().observe_terminal(obs)
        self.assess_pending(obs,self.llm.step+1,task_key(self.notebook))
