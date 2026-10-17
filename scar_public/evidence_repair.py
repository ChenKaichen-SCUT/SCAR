"""V11: scoped evidence -> explicit enabling conditions -> checked local repair.

Four matched modes share observation collection and acquisition computation.
None of these public-history methods can certify hidden time stationarity.
"""
from dataclasses import asdict, replace
from itertools import product
import json
import re

from scar_public.causal_model import digest
from scar_public.resource_competition import (ResourceDomain, ResourceGap, consumption,
    compile_resources, policy_profile_costs)
from scar_public.resource_trial import from_public, fresh, public_outcome, TrialSession
from scar_public.resource_evidence import EvidenceBank, evidence_context
from scar_public.resource_agent import (EvidenceDecisionMemory, EvidenceDecisionController,
    EvidenceDecisionAgent, ResourceController, OPTIONS, problem_from_data)


def semantic_context(text,scope='clock'):
    # A conservative observed clock cell, not learned rule boundaries. Unknown
    # within-hour changes remain possible and are not claimed away.
    clock = re.search(r'^Current Time: (\d+-\d+-\d+ \d+):',text,re.M)
    attributes = re.findall(r'^My (?:level|attack|defense) is at? ?[^\n]+|^My level is [^\n]+',text,re.M)
    modifiers = [line for line in text.splitlines() if re.search(r'\b(?:buff|bonus|effect|enchant|weather)\b',line,re.I)]
    result=dict(attributes=sorted(attributes),explicit_modifiers=sorted(modifiers))
    if scope=='clock':result['clock_cell']=clock[1] if clock else 'UNOBSERVED'
    elif scope!='attributes':raise ValueError('unknown evidence context scope')
    return result


def scoped_problem(model,text,target,scope='clock'):
    p=from_public(model,text,target,allow_carried=True)
    return replace(p,source={**p.source,'semantic_context':semantic_context(text,scope)})


def context_matches(text,saved):
    return semantic_context(text,'clock' if 'clock_cell' in saved else 'attributes')==saved


def failure_key(p,action):
    return digest([evidence_context(p)[0],p.holding,p.bag,p.ground,action])


def enabling_conditions(p,allowed,action):
    """Necessary inequalities, NOT a complete reachability decision."""
    d=ResourceDomain(p); op=d.actions.get(action)
    if not op or op[0]!='craft': return None
    r=p.recipes[0]; rows=[]
    bounds=(p.source or {}).get('hand_capacity_bounds')
    exact_capacity=not p.source or bool(bounds and bounds[0]==bounds[1])
    for quantity,access in sorted(map(tuple,allowed)):
        needs=consumption(r,op[2],quantity)
        stores=[0]+([1] if p.bag_name and 'bag' in access else [])+([2+d.l[p.start_location]] if 'ground' in access else [])
        deficits={item:max(0,amount-sum(d.start.resources[d.at(s,item)] for s in stores)) for item,amount in needs.items()}
        missing={item:max(0,amount-d.total(d.start,item)) for item,amount in needs.items()}
        # No finite storage obstruction when the floor is directly accessible.
        cap=None if 'ground' in access else p.hand_capacity-p.hand_background+(
            p.bag_capacity-p.bag_background if p.bag_name and 'bag' in access else 0)
        overload=max(0,sum(needs.values())-cap) if cap is not None else 0
        rows.append(dict(profile=[quantity,access],required=needs,accessible_deficit=deficits,
            total_material_deficit=missing,accessible_capacity=cap,capacity_shortfall=overload,
            arrangement_obstructed=bool(any(missing.values()) or overload and exact_capacity)))
    return dict(target=p.target,action=action,unit='milli-unit',profiles=rows,
        all_profiles_obstructed=bool(rows) and all(r['arrangement_obstructed'] for r in rows),
        capacity_is_exact=exact_capacity,
        next_obligation='For each surviving rule, obtain the missing material and enough accessible capacity. '
            'If all rules have an obstruction, rearranging these same local materials cannot solve it: '
            'seek an evidenced capacity/access change, upstream material, another method or another task. '
            'Reconsider after the condition changes; never declare the entire quest impossible.')


class RepairMemory(EvidenceDecisionMemory):
    def __init__(self):
        super().__init__()
        self.evidence_pending=None
        self.evidence_failures={}
        self.evidence_repairs=[]
        self.evidence_observation_audit=[]
        self.repair_attempts=[]
        self.evidence_targets=[]
        self.evidence_grounding_observations=[]


class RepairController(EvidenceDecisionController):
    mode='structured'
    context_scope='clock'
    # The prospective gate is shared by the four evidence-use arms.
    options={**OPTIONS,'require_profile_nondegradation':True}

    def evidence_filter(self,problem):
        allowed,metadata=self.bank().query(problem)
        return (allowed if self.mode=='structured' else None),metadata

    def evidence_observed(self,event,saved):
        super().evidence_observed(event,saved)
        p=self.session.compiled.domain.problem
        if event.get('status')=='ACTIVE' and event['action'].startswith('craft ') and event['observed'][0]=='failure':
            # An exact-state cache is deliberately weaker than a rule constraint.
            # Cache only a failed first action: later prefixes need a new grounding.
            if len(self.session.events)==1:
                key,entry=self.bank().entry(p)
                self.memory.evidence_failures[failure_key(p,event['action'])]=dict(
                    action=event['action'],context=key,epoch=entry['epoch'],event=event)
        self.memory.evidence_targets.append(p.target)

    def attempt_signature(self,target):
        return ResourceController.attempt_signature(self,target)

    def consider(self,parsed,text,step):
        # A stale container is an observation gap, not a license to invent its
        # contents. This paid prerequisite is not labeled a verified experiment.
        if self.mode=='structured' and parsed['action'].startswith('craft '):
            target=parsed['action'].split()[-1]
            try:
                self.ground(text,target)
            except ResourceGap as error:
                if str(error)=='attached container contents stale; inspect before planning':
                    state=fresh(text)
                    bags=[name for name,b in self.memory.model.containers.items()
                          if (state['holding'].get(name) or state['equipped'].get(name)) and b.get('uncertain_after_craft')]
                    if len(bags)==1 and len(self.memory.evidence_grounding_observations)<6 and step+1<300:
                        event=dict(target=target,container=bags[0],step=step,observation_sha256=digest(text))
                        self.memory.evidence_grounding_observations.append(event)
                        return {**parsed,'action':'inspect '+bags[0],'decision_source':'paid_grounding_observation',
                            'grounding_observation':event,'reasoning':'Observe stale accessible container contents before modeling the craft; this action costs one step.'}
        return super().consider(parsed,text,step)

    def ground(self,text,target):
        return scoped_problem(self.memory.model,text,target,self.context_scope)

    def resume(self,text):
        pending=self.memory.evidence_pending
        self.memory.evidence_pending=None
        if pending:
            p=problem_from_data(pending['problem']); action=pending['action']
            try:
                observed=fresh(text); status=public_outcome(text,action)
                if not status or 'I was attacked' in text: raise ResourceGap('missing outcome or ambient combat')
                if not context_matches(text,p.source['semantic_context']): raise ResourceGap('public semantic context changed')
                if observed['equipped']!=p.source['equipment']: raise ResourceGap('equipment changed')
                carried=p.source.get('fixed_carried_container')
                if carried and observed['holding'].get(carried['name'],0)!=carried['count']:
                    raise ResourceGap('fixed carried container detached')
                if set(observed['holding'])-set(p.items)-({carried['name']} if carried else set()):
                    raise ResourceGap('unexpected held item')
                d=ResourceDomain(p); r=p.recipes[0]
                vector=lambda values:tuple(values.get(n,0) for n in p.items)
                actual=(status,observed['location'],vector(observed['holding']),vector(observed['ground']),
                        (status=='success',),None)
                survivors=[]
                for pair in product(r.quantity_modes,r.access_modes):
                    _,prediction=d.transition({r.output:pair},d.start,action)
                    if prediction==actual:survivors.append(pair)
                key,entry=self.bank().entry(p)
                before=set(map(tuple,entry['allowed']));after=before&set(survivors)
                if not after: raise ResourceGap('all retained rules contradicted by actual feedback')
                entry['allowed']=sorted(after);entry['observations']+=1
                self.bank().state['revision']+=int(after!=before)
                event=dict(kind='PASSIVE_MATCHED_TRANSITION',context=key,action=action,
                    observation_sha256=digest(text),before=len(before),after=len(after),
                    eliminated=sorted(before-after),step=pending['step'])
                self.bank().state['audit'].append(event)
                if status=='failure' and fresh(pending['text'])==observed:
                    self.memory.evidence_failures[failure_key(p,action)]=dict(action=action,context=key,epoch=entry['epoch'],event=event)
                self.memory.evidence_observation_audit.append(event)
            except ResourceGap as error:
                self.bank().invalidate(p,str(error))
                self.memory.evidence_observation_audit.append(dict(kind='INVALIDATED',reason=str(error),action=action))
        return super().resume(text)

    def prepare_decision(self,text,step):
        if self.mode=='none':return ''
        facts=[]
        for target in list(dict.fromkeys([self.memory.resource_target]+self.memory.evidence_targets[-3:])):
            if not target:continue
            try:
                p=self.ground(text,target);allowed,meta=self.bank().query(p)
                if not allowed:continue
                fact=dict(target=target,evidence=meta,surviving_joint_rules=allowed[target])
                if self.mode=='structured':
                    fact['enabling_conditions']=enabling_conditions(p,allowed[target],'craft 1 '+target)
                    if fact['enabling_conditions']['all_profiles_obstructed'] and self.memory.resource_target==target:
                        self.memory.resource_target='';self.memory.resource_fresh=False
                if self.mode in ('prompt','structured'):facts.append(fact)
            except ResourceGap:continue
        return '\nApplicable real-feedback evidence (conditional local rules):\n'+json.dumps(facts) if facts else ''

    def review_proposal(self,parsed,text):
        action=parsed['action']
        if self.mode in ('none','prompt') or not action.startswith('craft '):return None
        try:
            p=self.ground(text,action.split()[-1])
            if self.mode=='cache':
                record=self.memory.evidence_failures.get(failure_key(p,action))
                _,entry=self.bank().entry(p)
                if not record or record['epoch']!=entry['epoch']:return None
                review=dict(status='CONTEXTUAL_FAILURE_CACHE',action=action,
                    reason='This exact command failed in this same observed physical arrangement and clock cell. Change a condition.',
                    evidence=record)
            else:
                review=self.bank().review_action(p,action)
                if not review:return None
                allowed,_=self.bank().query(p)
                review['enabling_conditions']=enabling_conditions(p,allowed[p.target],action)
            review['fallback_inspection']='inspect '+self.memory.model.stations[p.target]['name']
            return review
        except ResourceGap:return None

    def certified_repair(self,review,text,step):
        if self.mode!='structured':return None
        try:
            p=self.ground(text,review['action'].split()[-1]);allowed,_=self.bank().query(p)
            signature=digest([asdict(p),allowed])
            if signature in self.memory.repair_attempts or len(self.memory.repair_attempts)>=6:return None
            self.memory.repair_attempts.append(signature)
            if review['enabling_conditions']['all_profiles_obstructed']:
                self.memory.evidence_repairs.append(dict(status='ENABLING_CONDITION_REQUIRED',step=step,review=review))
                return None
            horizon=min(6,300-step)
            c=compile_resources(p,horizon=horizon,max_states=12000,allowed_profiles=allowed)
            planner=c.planner();result=planner.solve(c.belief,horizon,600)
            if result.policy and result.upper!=float('inf') and not result.policy.get('stop'):
                planner.verify(c.belief,horizon,result.policy)
                action=result.policy['action']
                event=dict(status='VERIFIED_STRONG_LOCAL_REPAIR',step=step,action=action,
                    profile_costs=policy_profile_costs(planner,c.belief,result.policy),fingerprint=c.fingerprint)
                self.memory.evidence_repairs.append(event)
                self.session=TrialSession(c,dict(guarantee_mode='strong',status='VERIFIED_STRONG_LOCAL_REPAIR',
                    success_exempt_models=[]),result.policy,planner)
                _,metadata=self.bank().query(p)
                self.memory.resource_trial_state=dict(problem=asdict(p),options={**self.options,'horizon':horizon,'mode':'strong'},
                    fingerprint=c.fingerprint,feedback=[],pending_action=self.session.action(),
                    allowed_profiles=allowed,evidence=metadata,repair_direct=True)
                return dict(action=action,reasoning='First action of a checked local repair; observe before replanning.',
                    decision_source='evidence_condition_repair',repair_certificate=event,frame=dict(self.memory.frame))
            self.memory.evidence_repairs.append(dict(status='REPAIR_SEARCH_UNKNOWN',step=step))
        except ResourceGap as error:
            self.memory.evidence_repairs.append(dict(status='REPAIR_GAP',reason=str(error),step=step))
        return None

    def after_decision(self,parsed,text,step):
        action=parsed['action']
        if not action.startswith('craft '):return
        target=action.split()[-1]
        self.memory.evidence_targets.append(target)
        # Certified session feedback is already collected by the common controller.
        if self.memory.resource_trial_state:return
        try:
            p=self.ground(text,target)
            if action not in ResourceDomain(p).actions:return
            self.memory.evidence_pending=dict(problem=asdict(p),action=action,text=text,step=step)
        except ResourceGap:pass


class EvidenceRepairAgent(EvidenceDecisionAgent):
    def __init__(self,llm,system_prompt):
        super().__init__(llm,system_prompt)
        self.notebook=RepairMemory();self.resource_controller=RepairController(self.notebook)

    def observe_terminal(self,obs):
        if self.notebook.evidence_pending:self.resource_controller.resume(obs['text'])
        super().observe_terminal(obs)
