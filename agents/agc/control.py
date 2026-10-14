"""Bounded goal/progress/failure state; emits EXECUTE or RECONSIDER only."""
from collections import Counter
from dataclasses import dataclass,asdict
from scar.io import digest
from .state import extract,satisfied_literal

WINDOW=8
MAX_FAILURES=12
MAX_GOALS=8
MAX_SEEN=256
MAX_RECONSIDER=1


@dataclass
class GoalState:
    goal_description:str
    creation_step:int
    evidence:list
    last_progress_step:int
    status:str='ACTIVE'
    source:str='model'


class Control:
    def __init__(self):
        self.goal=None;self.archive=[];self.failures=[];self.history=[]
        self.seen_states=[];self.seen_events=[];self.seen_entities=[];self.events=[]
        self.last_public_goal=None;self.public_recent=[];self.last=None

    def to_dict(self):
        return dict(goal=asdict(self.goal) if self.goal else None,archive=self.archive,failures=self.failures,
            history=self.history,seen_states=self.seen_states,seen_events=self.seen_events,seen_entities=self.seen_entities,
            last_public_goal=self.last_public_goal,public_recent=self.public_recent,last=self.last,events=self.events)

    @classmethod
    def from_dict(cls,d):
        self=cls();self.__dict__.update(d)
        self.goal=GoalState(**d['goal']) if d['goal'] else None
        return self

    def status(self,status,step,reason):
        if self.goal and self.goal.status!=status:
            old=self.goal.status;self.goal.status=status
            self.events.append(dict(kind='goal_status',step=step,goal=self.goal.goal_description,before=old,after=status,reason=reason))

    def adopt(self,description,evidence,step,source):
        if self.goal and self.goal.goal_description==description and self.goal.status not in ('INVALID','COMPLETED'):return
        previous=asdict(self.goal) if self.goal else None
        if previous:
            self.archive=(self.archive+[dict(**previous,retired_step=step)])[-MAX_GOALS:]
        self.goal=GoalState(description,step,evidence,step,source=source)
        self.events.append(dict(kind='goal_reset' if previous else 'goal_created',step=step,previous=previous,new=asdict(self.goal)))

    def initialize(self,obs):
        state=extract(obs);self.last=state
        self.seen_states=[state['signature']];self.seen_events=[digest(state['event'])];self.seen_entities=state['entities'][-MAX_SEEN:]
        self.public_recent=[obs['text']]
        self.ingest_goal(state,0)

    def ingest_goal(self,state,step):
        explicit=state['public_goal']
        if explicit and explicit!=self.last_public_goal:
            if self.goal and self.goal.status not in ('COMPLETED','INVALID') and self.goal.goal_description!=explicit:
                self.status('INVALID',step,'new_explicit_public_instruction_supersedes_current_goal')
            self.adopt(explicit,[dict(quote=explicit,step=step,source='public_explicit_instruction')],step,'public')
            self.last_public_goal=explicit
        if self.goal and satisfied_literal(self.goal.goal_description,state):
            self.status('COMPLETED',step,'public_location_satisfies_literal_enter_goal')

    def progress(self,before,action,after,step):
        b,a=extract(before),extract(after)
        state_new=a['signature'] not in self.seen_states
        new_entities=sorted(set(a['entities'])-set(self.seen_entities))
        event_new=bool(a['event'] and digest(a['event']) not in self.seen_events)
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
            key=(action,b['context']);old=next((r for r in self.failures if (r['action'],r['context'])==key),None)
            if old:self.failures.remove(old)
            record=dict(action=action,context=b['context'],result='failed',avoid_reason=a['feedback'][:500],
                count=(old['count']+1 if old else 1),step=step)
            self.failures=(self.failures+[record])[-MAX_FAILURES:]
        else:
            self.failures=[r for r in self.failures if (r['action'],r['context'])!=(action,b['context'])]
        if self.goal:
            if action==self.goal.goal_description and not a['failed']:
                self.status('COMPLETED',step,'literal_goal_action_accepted_by_public_feedback')
            elif a['permanent'] and action==self.goal.goal_description:
                self.status('INVALID',step,'explicit_public_impossibility_for_literal_goal_action')
            elif self.goal.status not in ('COMPLETED','INVALID'):
                if self.stagnant() or self.failed_count(action,b['context'])>=3:
                    self.status('SUSPICIOUS',step,'low_information_repetition_or_repeated_public_failure')
                elif informative:
                    self.goal.last_progress_step=step;self.status('ACTIVE',step,'new_public_information_or_state')
        self.ingest_goal(a,step)
        self.public_recent=(self.public_recent+[after['text']])[-5:];self.last=a
        return dict(**flags,informative=informative,stagnant=self.stagnant(),goal=asdict(self.goal) if self.goal else None)

    def stagnant(self):
        return len(self.history)==WINDOW and sum(r['progress'] for r in self.history)<=1 and max(Counter(r['action'] for r in self.history).values())>=5

    def failed_count(self,action,context):
        return max((r['count'] for r in self.failures if r['action']==action and r['context']==context),default=0)

    def summary(self,state,reconsider=None):
        return dict(current_goal=asdict(self.goal) if self.goal else None,recent_progress=[r['progress'] for r in self.history],
            stagnant=self.stagnant(),previous_failed_attempts=[r for r in self.failures if r['context']==state['context']][-6:],
            other_recent_failed_attempts=[r for r in self.failures if r['context']!=state['context']][-3:],
            reconsider=reconsider,goal_output_policy='Keep the same goal_description while valid. Use one current subgoal, not the whole game. '
            'If completed or INVALID, reconsider using current public evidence. goal_evidence must be an exact quote from public observations, not your own reasoning. '
            'No action or replacement goal is supplied by the controller.')

    def assess(self,proposal,obs,syntax_ok,step):
        state=extract(obs);reasons=[];hard=[]
        if not isinstance(proposal,dict) or not isinstance(proposal.get('action'),str):return 'RECONSIDER',['missing_action'],True
        action=proposal['action'].strip();description=proposal.get('goal_description');quote=proposal.get('goal_evidence')
        if not syntax_ok:hard.append('action_not_in_public_action_syntax')
        if not isinstance(description,str) or not description.strip() or len(description)>400:hard.append('missing_or_oversized_goal_description')
        if not isinstance(quote,str) or not 4<=len(quote)<=500:hard.append('missing_or_oversized_public_evidence')
        else:
            corpus=self.public_recent+[obs['text']]+([e['quote'] for e in self.goal.evidence] if self.goal else [])
            normalized_quote=' '.join(quote.split())
            if not any(normalized_quote in ' '.join(text.split()) for text in corpus):hard.append('goal_evidence_not_an_exact_public_quote')
        if self.goal and self.goal.status in ('INVALID','COMPLETED'):
            if description==self.goal.goal_description:hard.append('retaining_invalid_or_completed_goal')
            if self.goal.status=='INVALID' and action==self.goal.goal_description:hard.append('executing_literal_invalid_goal')
        if self.failed_count(action,state['context'])>=2:reasons.append('repeated_failure_in_same_public_context')
        if self.stagnant() and (action=='wait' or sum(r['action']==action for r in self.history)>=3):reasons.append('repeated_low_information_action')
        if self.goal and self.goal.status=='SUSPICIOUS':reasons.append('current_goal_suspicious')
        return ('RECONSIDER' if hard or reasons else 'EXECUTE'),hard+reasons,bool(hard)

    def accept_goal(self,proposal,step):
        self.adopt(proposal['goal_description'].strip(),[dict(quote=proposal['goal_evidence'],step=step,source='model_selected_public_quote')],step,'model')
