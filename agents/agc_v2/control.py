"""Confidence and public action reliability; no task planner or game rules."""
import re
from dataclasses import dataclass,asdict
from agents.agc.control import Control as PreviousControl,GoalState as PreviousGoal,MAX_GOALS,MAX_FAILURES,MAX_SEEN,WINDOW
from agents.agc.state import extract,satisfied_literal
from scar.io import digest

THRESHOLD=.4
INITIAL_CONFIDENCE=.7
MAX_ACTION_RETRIES=3
INVALID_MESSAGE='Previous action was invalid.\nPlease generate another valid action.'
GOAL_MESSAGE='Current goal confidence is below the threshold. Reconsider its validity using the available public observations.'
STOP_WORDS=set('a an the to of and or for in on at with from by is are be have has get find gather collect obtain make craft enter reach go current goal all necessary required before after about using use'.split())


def words(s):return set(re.findall(r'[a-z0-9]+',s.lower()))-STOP_WORDS


@dataclass
class GoalState(PreviousGoal):
    confidence:float=INITIAL_CONFIDENCE


class Control(PreviousControl):
    @classmethod
    def from_dict(cls,d):
        self=cls();self.__dict__.update(d);self.goal=GoalState(**d['goal']) if d['goal'] else None
        return self

    def adopt(self,description,evidence,step,source):
        if self.goal and self.goal.goal_description==description and self.goal.status not in ('INVALID','COMPLETED'):return
        previous=asdict(self.goal) if self.goal else None
        if previous:self.archive=(self.archive+[dict(**previous,retired_step=step)])[-MAX_GOALS:]
        verified=all(e.get('verified',source=='public') for e in evidence)
        self.goal=GoalState(description,step,evidence,step,source=source,confidence=INITIAL_CONFIDENCE if verified else .35)
        self.events.append(dict(kind='goal_reset' if previous else 'goal_created',step=step,previous=previous,new=asdict(self.goal),
            reset_reason='public_instruction' if source=='public' else 'model_goal_change',
            previous_below_threshold=bool(previous and previous['confidence']<THRESHOLD)))

    def set_confidence(self,value,step,reasons):
        if not self.goal:return
        old=self.goal.confidence;self.goal.confidence=round(max(0.,min(1.,value)),6)
        self.events.append(dict(kind='confidence_update',step=step,goal=self.goal.goal_description,before=old,after=self.goal.confidence,reasons=reasons))
        if self.goal.status not in ('INVALID','COMPLETED'):
            self.status('SUSPICIOUS' if self.goal.confidence<THRESHOLD else 'ACTIVE',step,'confidence_threshold')

    def evidence_verified(self,quote,obs):
        if not isinstance(quote,str) or not 4<=len(quote)<=500:return False
        corpus=self.public_recent+[obs['text']]
        if self.goal:corpus += [e['quote'] for e in self.goal.evidence if e.get('verified',self.goal.source=='public')]
        normalized=' '.join(quote.split())
        return any(normalized in ' '.join(s.split()) for s in corpus)

    def assess(self,proposal,obs,syntax_ok,step):
        hard=[]
        if not isinstance(proposal,dict) or not isinstance(proposal.get('action'),str):
            return dict(decision='RECONSIDER',hard=True,reasons=['missing_action'],evidence_verified=False,goal_review=False)
        action=proposal['action'].strip();description=proposal.get('goal_description');state=extract(obs)
        if not syntax_ok:hard.append('action_not_in_public_action_syntax')
        if not isinstance(description,str) or not description.strip() or len(description)>400:hard.append('missing_or_oversized_goal_description')
        last=self.history[-2:]
        repeated=len(last)==2 and all(r['failed'] and r['action']==action and r['context']==state['context'] for r in last)
        if repeated:hard.append('consecutive_identical_failures_in_unchanged_public_context')
        # Invalid/completed goals require reconsideration, never a replacement action.
        invalid=bool(self.goal and self.goal.status in ('INVALID','COMPLETED') and description==self.goal.goal_description)
        verified=self.evidence_verified(proposal.get('goal_evidence'),obs)
        low=bool(self.goal and self.goal.confidence<THRESHOLD and description==self.goal.goal_description)
        review=bool(low or invalid)
        return dict(decision='RECONSIDER' if hard or review else 'EXECUTE',hard=bool(hard),reasons=hard+(['goal_confidence_requires_review'] if review else []),
            evidence_verified=verified,goal_review=review)

    def accept_goal(self,proposal,step,verified):
        quote=proposal.get('goal_evidence');quote=quote[:500] if isinstance(quote,str) else ''
        old=self.goal.goal_description if self.goal else None
        self.adopt(proposal['goal_description'].strip(),[dict(quote=quote,step=step,source='model_selected_public_quote',verified=verified)],step,'model')
        if not verified:self.set_confidence(min(self.goal.confidence,.35),step,['unverified_public_evidence'])
        elif self.goal.goal_description==old:
            self.goal.evidence=[dict(quote=quote,step=step,source='model_selected_public_quote',verified=True)]

    def summary(self,state,reconsider=None):
        out=super().summary(state,None)
        out.update(confidence_threshold=THRESHOLD,reevaluation_requested=bool(self.goal and self.goal.confidence<THRESHOLD),
            goal_output_policy='Keep the same subgoal while the public evidence supports it. Confidence is a heuristic, not a probability. '
            'Temporary absence of progress alone does not require changing a supported goal. If confidence is below the threshold, reconsider the goal from current public evidence. '
            'Prefer an exact public quote for goal_evidence; unverified text lowers confidence, but does not by itself prohibit an action. '
            'The controller supplies no action or replacement goal.')
        return out

    def progress(self,before,action,after,step):
        b,a=extract(before),extract(after);state_new=a['signature'] not in self.seen_states
        new_entities=sorted(set(a['entities'])-set(self.seen_entities));event_new=bool(a['event'] and digest(a['event']) not in self.seen_events)
        flags=dict(observation_new=state_new,inventory_changed=b['hands']!=a['hands'] or b['equipment']!=a['equipment'] or
            (a['observed_container_contents'] is not None and a['observed_container_contents']!=b['observed_container_contents']),
            location_changed=b['location']!=a['location'],new_entities=new_entities,event_new=event_new)
        informative=bool(state_new or new_entities or event_new)
        for attr,value in [('seen_states',a['signature']),('seen_events',digest(a['event']))]:
            target=getattr(self,attr)
            if value not in target:target.append(value)
            setattr(self,attr,target[-MAX_SEEN:])
        self.seen_entities=list(dict.fromkeys(self.seen_entities+new_entities))[-MAX_SEEN:]
        self.history=(self.history+[dict(step=step,action=action,progress=int(informative),failed=a['failed'],context=b['context'],flags=flags)])[-WINDOW:]
        if a['failed']:
            old=next((r for r in self.failures if (r['action'],r['context'])==(action,b['context'])),None)
            if old:self.failures.remove(old)
            self.failures=(self.failures+[dict(action=action,context=b['context'],result='failed',avoid_reason=a['feedback'][:500],count=old['count']+1 if old else 1,step=step)])[-MAX_FAILURES:]
        else:self.failures=[r for r in self.failures if (r['action'],r['context'])!=(action,b['context'])]
        related=False;signals=[]
        if self.goal:
            terms=words(self.goal.goal_description)
            gain=any(terms & words(name) and value>(b[field] or {}).get(name,0) for field in ('hands','equipment') for name,value in (a[field] or {}).items())
            related=bool(not a['failed'] and ((state_new and gain) or (event_new and terms & words(a['event']))))
            literal=action==self.goal.goal_description and not a['failed']
            if literal or satisfied_literal(self.goal.goal_description,a):
                self.set_confidence(1.,step,['literal_goal_completed']);self.status('COMPLETED',step,'literal_goal_completed')
                self.goal.last_progress_step=step;related=True
            elif a['permanent'] and action==self.goal.goal_description:
                self.set_confidence(0.,step,['explicit_public_impossibility']);self.status('INVALID',step,'explicit_public_impossibility')
            elif self.goal.status not in ('INVALID','COMPLETED'):
                if related:delta=.08;signals=['novel_goal_related_public_change'];self.goal.last_progress_step=step
                elif a['failed']:delta=-.12 if self.failed_count(action,b['context'])>=2 else -.08;signals=['repeated_failure' if delta==-.12 else 'public_failure']
                elif not informative:delta=-.06;signals=['no_new_public_information']
                else:delta=-.02;signals=['new_information_not_linked_to_goal']
                self.set_confidence(self.goal.confidence+delta,step,signals)
        self.ingest_goal(a,step)
        self.public_recent=(self.public_recent+[after['text']])[-5:];self.last=a
        return dict(**flags,informative=informative,goal_related_progress=related,stagnant=self.stagnant(),goal=asdict(self.goal) if self.goal else None)
