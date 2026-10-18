"""LLM-proposed, publicly testable obstacle hypotheses; unknown is not a veto.

Replaces the old fixed repair menu, not the normal actor. The gate certifies
neither task relevance nor survival. Proposed relations are never world facts.
"""
import copy
import json
import math
import re

from scar_public.causal_model import digest
from scar_public.continuation import PROTECTED, feedback_lines, nearby, task_key, threatened
from scar_public.obstacle_repair import ObstacleRepairAgent, edge_blocker, mentions, test_value
from scar_public.public_model import quantities, state_from_text


PREFIXES=('pick up ','enter ','inspect ','talk to ')


def command_parts(action):
    if not isinstance(action,str): return None
    for prefix in PREFIXES:
        if action.startswith(prefix) and re.fullmatch(r'[\w-]+',action[len(prefix):]):
            return prefix,action[len(prefix):]
    return None


def predicate_valid(test):
    if not isinstance(test,dict) or not isinstance(test.get('target'),str): return False
    if test.get('kind') not in ('held','at','visible','contained','report'): return False
    count=test.get('count',1)
    if not isinstance(count,(int,float)) or isinstance(count,bool) or not math.isfinite(count) or count<=0:return False
    if test['kind']=='contained' and not isinstance(test.get('container'),str):return False
    if test['kind']=='report':
        a,b=test.get('true_contains'),test.get('false_contains')
        if not all(isinstance(x,str) and len(x)>=3 for x in (a,b)) or a==b:return False
    return True


def evaluate(test,text):
    if test['kind']=='visible':
        state=state_from_text(text)
        if test.get('location') and state['location']!=test['location']:return None
        return None if state['ground'] is None else state['ground'].get(test['target'],0)>=test.get('count',1)
    if test['kind'] in ('held','at'):return test_value(test,text)
    name=test.get('container',test['target'])
    end=r'(?=\n\n|\n(?:I |My |Current |Neighboring |[\w-]+ says:)|\Z)'
    match=re.search(r'^I inspected '+re.escape(name)+r': (.*?)'+end,text,re.M|re.S)
    match=match or re.search(r'^'+re.escape(name)+r' says: (.*?)'+end,text,re.M|re.S)
    if not match:return None
    if test['kind']=='contained':
        contents=re.search(r'It contains: (.*?) \(capacity:',match[1],re.S)
        return None if not contents else quantities(contents[1]).get(test['target'],0)>=test.get('count',1)
    yes,no=(mentions(match[1],test[k]) for k in ('true_contains','false_contains'))
    return yes if yes!=no else None  # silence or conflicting phrases is UNKNOWN


def information_step(step):
    parts=command_parts(step['action'])
    return parts[0] in ('inspect ','talk to ') or step['test']['kind'] not in ('held','at')


def required_reserves(memory,goals):
    """Only observed explicit held outputs and their observed recipe inputs.

    These are conservative reservations for the present method, not a complete
    formalization of the task. They constrain declared/observed spending only.
    """
    model=memory.model;held=model.current.get('holding') or {};reserves={}
    for goal in goals:
        if hasattr(model,'goal_contract'):
            for literal in model.goal_contract(goal)['supported_literals']:
                if literal['kind'] in ('held','equipped'):reserves[literal['item']]=max(1,reserves.get(literal['item'],0))
    def visit(name,count,seen):
        if name in seen or len(seen)>=3:return
        if held.get(name,0):reserves[name]=max(count,reserves.get(name,0))
        for item,number in model.recipes.get(name,{}).get('needs',{}).items():visit(item,number,seen|{name})
    for output in model.recipes:
        if any(mentions(g,output) for g in goals) and not held.get(output):visit(output,1,set())
    return reserves


def check_steps(steps,memory,evidence,task,reserves,observed_uses=(),initial=None):
    """Project only listed public interfaces and inventory arithmetic.

    Future unknown rooms/effects remain warnings; fresh observation is required
    before every actual action. Unlike route-only checking, a pickup can change
    the carried-state scope of a later failed edge.
    """
    state=copy.deepcopy(initial if initial is not None else memory.model.current)
    errors=[];unknown=[];model=memory.model
    for index,step in enumerate(steps):
        action=step.get('action');parts=command_parts(action)
        if not parts:errors.append('UNSUPPORTED_ACTION');break
        kind,name=parts
        if not predicate_valid(step.get('test')):errors.append('UNOBSERVABLE_TEST');break
        test=step['test']
        if kind=='pick up ' and (test['kind']!='held' or test['target']!=name):errors.append('TEST_NOT_LINKED_TO_ACTION')
        if kind=='enter ' and test['kind']=='at' and test['target']!=name:errors.append('TEST_NOT_LINKED_TO_ACTION')
        if kind=='inspect ' and not (test['kind']=='report' and test['target']==name or test['kind']=='contained' and test['container']==name):
            errors.append('TEST_NOT_LINKED_TO_ACTION')
        if kind=='talk to ' and not (test['kind']=='report' and test['target']==name):errors.append('TEST_NOT_LINKED_TO_ACTION')
        held,ground=state.get('holding'),state.get('ground');place=state.get('location')
        if kind=='pick up ':
            if ground is not None and ground.get(name,0)<1:errors.append('OBJECT_NOT_AT_PROJECTED_LOCATION')
            if held is not None and model.capacity_upper is not None and sum(held.values())+1>model.capacity_upper:
                errors.append('CAPACITY_CONTRADICTION')
            if ground is None:unknown.append(dict(index=index,kind='FUTURE_GROUND_UNKNOWN'))
        elif kind=='enter ':
            if place is not None and name not in state.get('neighbors',[]):errors.append('EXIT_NOT_IN_OBSERVED_ADJACENCY')
            shadow=copy.copy(evidence);shadow.current=state
            blocker=edge_blocker(shadow,task,place,action,index)
            if blocker:errors.append(dict(reason='UNCHANGED_DOWNSTREAM_BLOCKER',witness=blocker))
        elif kind=='inspect ':
            visible=set(held or {})|set(ground or {})|set(state.get('equipped') or {})
            if ground is not None and name not in visible:errors.append('INSPECTION_TARGET_NOT_AVAILABLE')
        elif index==0 and initial is None and name not in nearby(evidence.observation):errors.append('SPEAKER_NOT_CURRENTLY_VISIBLE')
        spend=step.get('may_consume',{})
        if not isinstance(spend,dict) or any(not isinstance(n,str) or not isinstance(v,(int,float)) or isinstance(v,bool)
            or not math.isfinite(v) or v<0 for n,v in spend.items()):errors.append('MALFORMED_RESOURCE_BUDGET');spend={}
        spend=dict(spend)
        for use in observed_uses:
            if use['action']==action and use['location']==place:
                for item,amount in use['consumed'].items():
                    if (held or {}).get(item,0):spend[item]=max(spend.get(item,0),amount)
        for item,amount in spend.items():
            if held is not None and amount>held.get(item,0):errors.append('SPENDING_UNAVAILABLE_RESOURCE')
            if min((held or {}).get(item,0),reserves.get(item,0))>max(0,(held or {}).get(item,0)-amount):
                errors.append('TASK_RESOURCE_RESERVATION')
        if kind=='pick up ':
            if held is not None:held[name]=held.get(name,0)+1
            if ground is not None:ground[name]=max(0,ground.get(name,0)-1)
        elif kind=='enter ':
            destination=model.edges.get(place,{}).get(name)
            state['location']=destination;listing=model.locations.get(destination)
            state['ground']=copy.deepcopy(listing['objects']) if listing else None
            state['neighbors']=listing['neighbors'] if listing else []
            unknown.append(dict(index=index,kind='NAVIGATION_EFFECTS_AND_SAFETY_UNVERIFIED'))
        # Spending is a possible effect, not a certified prediction. Continuing
        # after such an action requires real observations; do not fabricate facts.
        if spend:
            unknown.append(dict(index=index,kind='CONSUMPTION_IS_A_HYPOTHESIS',resources=spend))
            if held is not None:
                for item,amount in spend.items():held[item]=max(0,held.get(item,0)-amount)
    return dict(errors=errors,unknown=unknown,projected=state)


def validate(candidate,memory,evidence,task,goals,attempts,uses,remaining):
    if not isinstance(candidate,dict):return None,['MALFORMED_HYPOTHESIS']
    if candidate.get('goal_quote') not in goals:return None,['UNANCHORED_GOAL']
    if not all(isinstance(candidate.get(k),str) and candidate[k].strip() for k in ('blocker','hypothesis','task_link')):
        return None,['MISSING_CAUSAL_HYPOTHESIS']
    sources='\n'.join(memory.observations)
    basis=candidate.get('basis',[])
    if not isinstance(basis,list) or not basis or len(basis)>3 or any(not isinstance(q,str) or len(q)<8 or q not in sources for q in basis):
        return None,['UNSUPPORTED_SOURCE_QUOTE']
    steps=candidate.get('steps')
    if not isinstance(steps,list) or not 1<=len(steps)<=min(3,remaining) or any(not isinstance(s,dict) for s in steps):
        return None,['INVALID_PLAN_LENGTH']
    if any(command_parts(s.get('action')) and not mentions(sources,command_parts(s['action'])[1]) for s in steps):
        return None,['UNOBSERVED_ENTITY']
    reserves=required_reserves(memory,goals)
    checked=check_steps(steps,memory,evidence,task,reserves,uses)
    if checked['errors']:return None,checked['errors']
    info=information_step(steps[-1]);branches=candidate.get('branches')
    if any(information_step(s) for s in steps[:-1]):return None,['INFORMATION_REQUIRES_A_BRANCH_BEFORE_CONTINUING']
    if info:
        if len(steps)+1>remaining:return None,['NO_BUDGET_FOR_INFORMATION_CONTINUATION']
        if not isinstance(branches,dict) or set(branches)!= {'true','false'}:return None,['MISSING_DISTINCT_DECISIONS']
        if not all(isinstance(b,dict) and command_parts(b.get('action')) and predicate_valid(b.get('test')) for b in branches.values()):
            return None,['INVALID_BRANCH']
        if branches['true']['action']==branches['false']['action']:return None,['IDENTICAL_BRANCH_ACTIONS']
        for outcome,branch in branches.items():
            projected=copy.deepcopy(checked['projected']);test=steps[-1]['test']
            if test['kind']=='visible' and projected.get('ground') is not None:
                projected['ground'][test['target']]=1 if outcome=='true' else 0
            branch_check=check_steps([branch],memory,evidence,task,reserves,uses,initial=projected)
            if branch_check['errors']:return None,branch_check['errors']
            checked['unknown']+=branch_check['unknown']
    elif branches:return None,['BRANCHES_REQUIRE_AN_INFORMATION_TEST']
    key=digest([task,[(s['action'],s['test']) for s in steps],memory.model.current.get('location'),
        memory.model.current.get('holding'),memory.model.current.get('equipped')])
    if any(a['key']==key and a['epoch']==evidence.epoch and evidence.step-a['step']<=24 for a in attempts):
        return None,['ALREADY_TRIED_IN_THIS_CONTEXT']
    return dict(**copy.deepcopy(candidate),key=key,task=task,epoch=evidence.epoch,step=evidence.step,
        information=info,checks=checked,reserves=reserves),[]


def inspect_proposals(response,memory,evidence,task,goals,attempts,uses,remaining):
    proposals=response.get('hypotheses',[]);accepted=[];rejected=[]
    if not isinstance(proposals,list):return accepted,[dict(reasons=['HYPOTHESES_MUST_BE_A_LIST'])]
    for candidate in proposals[:2]:
        admitted,reasons=validate(candidate,memory,evidence,task,goals,attempts,uses,remaining)
        if admitted:accepted.append(admitted)
        else:rejected.append(dict(candidate=candidate,reasons=reasons))
    return accepted,rejected


INSTRUCTION='''
The current method has observed failure/repetition. Propose up to TWO short ways
to change its blocking condition, ranked by likely task benefit, evidential
support and action cost. You MAY infer a new causal hypothesis from public facts
and ordinary object affordances; it need NOT have succeeded before. Label it as
a hypothesis, never an observed rule. Do not repeat an unchanged failed method.
Only public observations support facts; quoted provenance does not prove your
inference. Preserve task materials and urgent survival behavior. Do not invent
entities. A program has 1-3 actions, each followed by an observable test. Stop or
replan on contradiction/unknown. Do not require a known alternative resource
source before trying a plausible repair. Acquisition and navigation are changes,
not automatically information gain. Information tests require two DISTINCT
concrete branch actions; a different observation must change the next decision.
Unknown report content selects neither. No free-form 'reconsider' branch.
Allowed program actions: pick up ITEM, enter EXIT, inspect ITEM, talk to NPC.
Tests: {kind:held|visible,target:ITEM,count:1}, {kind:at,target:EXIT},
{kind:contained,container:ITEM,target:ITEM,count:1}, or
{kind:report,target:ITEM_OR_NPC,true_contains:literal,false_contains:different_literal}.
Report predicates match literal observed text, not inferred meaning. Optional
may_consume:{ITEM:quantity} declares possible spending for each action.
Return reasoning, action, hypotheses:[{goal_quote:exact listed goal, blocker:what
currently blocks it,hypothesis:what may change it,task_link:why that serves this
goal,basis:[1-3 exact short observation quotes],steps:[{action:command,test:object,
may_consume:{}}],branches:null OR {true:{action:command,test:object},false:{action:command,test:object}}}].
action is the first action of your preferred hypothesis, or the original action
with hypotheses:[] if no repair is worthwhile. Prefer one concise hypothesis when
the choice is clear. All schemas above are JSON; no extra keys or long reasoning.
'''


class HypothesisRepairAgent(ObstacleRepairAgent):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.hypothesis_pending=None;self.hypothesis_attempts=[];self.hypothesis_queries=[];self.observed_uses=[]

    def observe_use(self,text):
        if not self.continuation.records:return
        last=self.continuation.records[-1]
        before,after=last['before'].get('holding'),last['after'].get('holding')
        if before is None or after is None:return
        consumed={n:v-after.get(n,0) for n,v in before.items() if v>after.get(n,0)}
        reports=[line for line in text.splitlines() if line.startswith('I used ')]
        if len(consumed)==1 and any(mentions(line,next(iter(consumed))) for line in reports):
            record=dict(action=last['action'],location=last['before']['location'],consumed=consumed,
                reports=reports,step=last['step'],qualification='Observed co-occurrence with explicit use; no universal causal rule')
            if record not in self.observed_uses:self.observed_uses.append(record)

    def finalize_decision(self,executed,obs,step,prompt,query):
        evidence=self.continuation;task=task_key(self.notebook);self.observe_use(obs['text'])
        event=dict(step=step,original=executed['action'],changed=False,trigger=None)
        pending=self.hypothesis_pending;self.hypothesis_pending=None
        if pending:
            program=pending['program'];index=pending['index'];test=program['steps'][index]['test']
            outcome=evaluate(test,obs['text']);failure=feedback_lines(obs['text'])
            # Failed execution does not establish an intended observation. A false
            # state predicate is a refuted attempted effect, not useful information.
            if failure and program['information']:outcome=None
            result=dict(step=step,contract=program,index=index,outcome=outcome,failures=failure,
                admitted=False,decision_distinguishing=False,cancellation_reasons=[])
            self.obstacle_outcomes.append(result);event['previous_repair']=result
            follow=None;next_program=program;next_index=index+1
            if outcome is True and not failure and next_index<len(program['steps']):follow=program['steps'][next_index]
            elif program['information'] and next_index==len(program['steps']) and outcome is not None:
                follow=program['branches'][str(outcome).lower()];result['decision_distinguishing']=True
                next_program={**program,'steps':[follow],'branches':None,'information':False};next_index=0
            reasons=result['cancellation_reasons']
            if outcome is None:reasons.append('OUTCOME_UNKNOWN')
            if outcome is False and not program['information']:reasons.append('EXPECTED_EFFECT_NOT_OBSERVED')
            if task!=program['task']:reasons.append('TASK_CHANGED')
            if threatened(obs['text']) or executed['action'].startswith(PROTECTED):reasons.append('URGENT_ACTION_YIELD')
            if follow and not reasons:
                checked=check_steps(next_program['steps'][next_index:],self.notebook,evidence,task,
                    required_reserves(self.notebook,[program['goal_quote']]),self.observed_uses)
                reasons+=checked['errors'];result['continuation_check']=checked
                if not reasons:
                    result.update(admitted=True,proposed_continuation=follow['action'])
                    event.update(reason='OBSERVED_EFFECT_SELECTS_CONTINUATION',changed=follow['action']!=executed['action'])
                    if event['changed']:executed=self.replace(executed,follow['action'],program['goal_quote'],program['hypothesis'])
                    self.hypothesis_pending=dict(program=next_program,index=next_index)
                    return self.finish(executed,event,task)
        trigger=self.repair_trigger(executed['action'],task);event['trigger']=trigger
        if trigger and self.repair_mode!='off' and not threatened(obs['text']) and not executed['action'].startswith(PROTECTED):
            context=evidence.context(executed['action'],task)
            if len(self.hypothesis_queries)>=12:event['reason']='REPAIR_QUERY_BUDGET'
            elif any(q['context']==context and q['action']==executed['action'] and step-q['step']<=6 for q in self.hypothesis_queries):
                event['reason']='RECENT_QUERY_SAME_CONTEXT'
            else:
                goals=list(dict.fromkeys(r['quote'] for r in self.notebook.progress_tasks.values()))
                quote=executed.get('frame',{}).get('goal_quote','')
                if len(quote)>=12 and any(quote in t for t in self.notebook.observations):goals=list(dict.fromkeys([quote]+goals))
                if goals:
                    packet=dict(original=executed['action'],trigger=trigger,goals=goals,current=self.notebook.model.current,
                        remaining_actions=self.max_steps-step,capacity_upper=self.notebook.model.capacity_upper,
                        reserved_resources=required_reserves(self.notebook,goals),observed_uses=self.observed_uses[-6:],
                        previous_trials=[dict(hypothesis=o['contract']['hypothesis'],outcome=o['outcome'],
                            action=o['contract']['steps'][o['index']]['action'],failures=o['failures']) for o in self.obstacle_outcomes[-6:]])
                    response=query(prompt+'\nObstacle hypothesis proposals:\n'+json.dumps(packet,ensure_ascii=False)+INSTRUCTION)
                    self.hypothesis_queries.append(dict(context=context,action=executed['action'],step=step))
                    accepted,rejected=inspect_proposals(response,self.notebook,evidence,task,goals,
                        self.hypothesis_attempts,self.observed_uses,self.max_steps-step)
                    event.update(packet=packet,proposal=response,programs=accepted,program_rejections=rejected,proposal_calls=1)
                    if not accepted and rejected and len(self.hypothesis_queries)<12:
                        # One bounded correction of a concrete grounding/model
                        # contradiction; no environment rollout or hidden answer.
                        correction=dict(rejected=rejected,current_observed_state=self.notebook.model.current,
                            current_observation=obs['text'],remaining_actions=self.max_steps-step)
                        event['initial_proposal']=response;event['initial_rejections']=rejected
                        response=query(prompt+'\nObstacle hypothesis proposals:\n'+json.dumps(packet,ensure_ascii=False)+INSTRUCTION+
                            '\nThe first proposal failed explicit checks. CURRENT holdings and ground are different; '
                            'historical possession is not current possession. A new remedy must actually change the '
                            'failed condition before retrying. Correct the hypothesis/steps using the feedback below, '
                            'or retain the original with hypotheses:[] if no worthwhile plan survives. '
                            'Unsupported claims must be removed, not restated. This is the only correction attempt.\n'+
                            json.dumps(correction,ensure_ascii=False))
                        self.hypothesis_queries.append(dict(context=context,action=executed['action'],step=step,revision=True))
                        accepted,rejected=inspect_proposals(response,self.notebook,evidence,task,goals,
                            self.hypothesis_attempts,self.observed_uses,self.max_steps-step)
                        event.update(proposal=response,programs=accepted,program_rejections=rejected,proposal_calls=2)
                    if response.get('action')==executed['action']:event['reason']='ACTOR_RETAINS_ORIGINAL'
                    elif event['programs']:
                        choice=event['programs'][0];action=choice['steps'][0]['action']
                        event.update(reason='TESTABLE_HYPOTHESIS',contract=choice,changed=action!=executed['action'])
                        self.hypothesis_attempts.append(choice);self.hypothesis_pending=dict(program=choice,index=0)
                        if event['changed']:executed=self.replace(executed,action,choice['goal_quote'],choice['hypothesis'])
                    else:event['reason']='NO_ADMITTED_HYPOTHESIS'
        return self.finish(executed,event,task)
