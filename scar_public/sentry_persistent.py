"""Bounded, outcome-conditioned continuation of unresolved Sentry repairs.

The LLM still proposes the goal, explanation and next operation. Code enforces
literal observation references, a stable case goal, action-schema membership,
distinct probe branches and next-state freshness. These are structural checks,
not proofs that a quoted observation entails the proposed explanation.
"""
import hashlib
import json
import re


def fingerprint(text):
    return hashlib.sha256(text.encode()).hexdigest()


def action_valid(action, system):
    if not isinstance(action,str) or not action.strip() or '\n' in action:return False
    for line in system.splitlines():
        if not line.startswith('- '):continue
        template=line[2:].strip()
        if '<' not in template:
            if action.strip()==template:return True
            continue
        prefix=template.split('<',1)[0]
        count=len(re.findall(r'<[^>]+>',template))
        if action.startswith(prefix) and len(action[len(prefix):].split())>=count:return True
    return False


def validate_card(card, records, system, previous, latest):
    fields={'status','goal','blocker','hypothesis','revision','evidence','next','resolution'}
    if not isinstance(card,dict) or set(card)!=fields:raise ValueError('fixed card fields required')
    if card['status'] not in ('act','resolved','pause'):raise ValueError('unknown status')
    for key in ('goal','blocker','hypothesis','revision'):
        if not isinstance(card[key],str) or not card[key].strip():raise ValueError('nonempty '+key)
    if previous and card['goal']!=previous['goal']:raise ValueError('keep original goal verbatim until case closes')
    refs=card['evidence'];lookup={r['cycle']:r['observation'] for r in records}
    if not isinstance(refs,list) or not refs:raise ValueError('literal observation evidence required')
    for ref in refs:
        if not isinstance(ref,dict) or set(ref)!={'cycle','quote'}:raise ValueError('evidence needs cycle/quote')
        quote=ref['quote'];cycle=ref['cycle']
        if type(cycle) is not int or cycle not in lookup or not isinstance(quote,str) or len(quote.strip())<12:
            raise ValueError('invalid evidence reference')
        if quote not in lookup[cycle]:raise ValueError('quote absent from actual observation')
    if card['status']=='resolved':
        if not isinstance(card['resolution'],str) or not card['resolution'].strip():raise ValueError('explain original condition resolution')
        if latest not in [r['cycle'] for r in refs]:raise ValueError('resolution requires current observation')
    if card['status']!='act':
        if card['next'] is not None:raise ValueError('inactive card has no next action')
        return
    plan=card['next'];required={'action','kind','changes','preconditions','resource_check','expected','outcomes'}
    if not isinstance(plan,dict) or set(plan)!=required:raise ValueError('fixed next-operation fields required')
    if not action_valid(plan['action'],system):raise ValueError('operation outside supplied action schema')
    if plan['kind'] not in ('change','test'):raise ValueError('operation kind must change or test')
    for key in ('changes','preconditions','resource_check','expected'):
        if not isinstance(plan[key],str) or not plan[key].strip():raise ValueError('explain '+key)
    outcomes=plan['outcomes']
    if not isinstance(outcomes,list):raise ValueError('outcomes must be a list')
    if plan['kind']=='test':
        if len(outcomes)!=2:raise ValueError('test requires two distinguishable outcome branches')
        for branch in outcomes:
            if not isinstance(branch,dict) or set(branch)!={'observe','then'} or not all(isinstance(v,str) and v.strip() for v in branch.values()):
                raise ValueError('test needs observe/then branches')
        normalize=lambda s:' '.join(s.lower().split())
        if normalize(outcomes[0]['observe'])==normalize(outcomes[1]['observe']) or normalize(outcomes[0]['then'])==normalize(outcomes[1]['then']):
            raise ValueError('test outcomes must change the subsequent plan')


INSTRUCTION='''You continue an unresolved Sentry repair in a text environment.
Return one JSON card. Observations are evidence; actor reasoning and Sentry
judgments are hypotheses, not ground truth. Determine the current public task
and the condition actually preventing it. Do not substitute ingredients for a
requested final object. Do not assume that all materials must be held, that a
location supplies a facility, or that a new recipe avoids the same obstacle.

Use the previous attempted operation AND its actual following observation to
revise the explanation. If an advised operation was not executed, do not count
it as tested. A failed operation constrains that operation in those conditions;
it does not prove every way of achieving the goal impossible. Keep the previous
goal text EXACTLY until that case is resolved or paused. A state change or an
error-free action alone does not resolve the original condition.

Choose ONE grounded next operation that changes the blocking condition, is a
necessary step toward doing so, or tests competing explanations. Novel but
uncertain operations are allowed. For a test state two observable outcomes and
DIFFERENT subsequent plans. Do not inspect merely to postpone deciding. Check
known action preconditions, resources consumed and items still needed by the
task; explicitly mark uncertain facts rather than inventing guarantees. History
is dated: recheck location, quantities and access in the latest observation.
Do not repeat a failed operation unchanged unless an observed relevant condition
changed or the test has a stated stochastic reason. Avoid unnecessary detours.

If original condition is now resolved, explain why with an exact quote from the
latest observation. If goal interpretation is unsupported, a different task has
superseded it, or no grounded next operation exists, pause without declaring
success. A paused case remains unresolved. Do not use hidden rewards or rules.
Full public action/observation history is supplied; no top-K retrieval or actor
assertions replace it. Cite literal substrings, not paraphrases or action text.

Schema, with exactly these keys:
{"status":"act|resolved|pause","goal":"specific original task condition",
"blocker":"current obstructing condition","hypothesis":"explanation and uncertainty",
"revision":"what actual latest result changes, or initial diagnosis",
"evidence":[{"cycle":0,"quote":"literal substring of an observation"}],
"next":{"action":"one allowed command","kind":"change|test",
"changes":"how this addresses the SAME blocker, including any upstream step",
"preconditions":"known and uncertain enabling conditions",
"resource_check":"consumption and resources still needed by original task",
"expected":"concrete observable result",
"outcomes":[{"observe":"result A","then":"subsequent plan A"},
{"observe":"result B","then":"different subsequent plan B"}]},
"resolution":"only explain closure for resolved; otherwise empty"}
For non-act status next is null. For change operations outcomes can be [].
Keep each explanation concise. These are working hypotheses, not certificates.
'''


class PersistentRepair:
    def __init__(self,provider,system,mode='execute',max_calls=30,burst=6):
        if mode not in ('execute','advice'):raise ValueError(mode)
        self.provider=provider;self.system=system;self.mode=mode
        self.max_calls=max_calls;self.burst=burst;self.calls=0;self.remaining=0
        self.records=[];self.card=None;self.pending=None;self.events=[];self.attempts=[]
        self.case_number=0;self.last_verdict=None

    def seed(self,observation):
        if self.records:raise ValueError('history already initialized')
        self.records.append(dict(cycle=-1,action='',observation=observation))

    def observe(self,step,parsed,following,sentry_events,terminal=False):
        if self.records and step<=self.records[-1]['cycle']:raise ValueError('nonmonotone history')
        self.records.append(dict(cycle=step,action=parsed['action'],observation=following))
        if self.pending:
            self.attempts.append(dict(cycle=step,recommended=self.pending['card']['next'],
                executed=parsed['action'],matched=parsed['action']==self.pending['card']['next']['action'],
                observation=following))
        self.pending=None
        failures=[e for e in sentry_events if e['type']=='escape_result' and not e['resolved']]
        if failures:
            self.last_verdict={k:v for k,v in failures[-1].items() if k!='event_id'}
            # A new failed verification reopens a paused unresolved case. Keep
            # its goal and history; a fresh case is created only after closure.
            if self.card is None:self.case_number+=1
            self.remaining=self.burst
        if terminal or self.remaining<=0 or self.calls>=self.max_calls:return ''
        self.remaining-=1
        packet=dict(action_schema=self.system,unresolved_verdict=self.last_verdict,
            previous_card=self.card,attempts=self.attempts[-6:],history=self.records)
        errors=[];card=None
        for _ in range(2):
            if self.calls>=self.max_calls:break
            self.calls+=1
            prompt=json.dumps(packet,ensure_ascii=False)
            if errors:prompt+='\nCorrect structural errors: '+json.dumps(errors)
            result=self.provider.request([{'role':'system','content':INSTRUCTION},
                {'role':'user','content':prompt}],repair=200,
                options={'temperature':0.0,'max_tokens':2048,'response_format':{'type':'json_object'}})
            choice=result['choices'][0]
            try:
                if choice.get('finish_reason')!='stop':raise ValueError('incomplete card')
                candidate=json.loads(choice['message']['content'])
                validate_card(candidate,self.records,self.system,self.card,step)
                card=candidate;break
            except (ValueError,TypeError,KeyError) as exc:errors.append(str(exc))
        event=dict(type='persistent_card',step=step,case=self.case_number,calls=self.calls,
            structural_errors=errors,card=card,previous_attempt=self.attempts[-1] if self.attempts else None)
        self.events.append(event)
        if card is None:
            self.remaining=0;return ''
        self.card=card
        if card['status']=='resolved':
            self.card=None;self.attempts=[];self.remaining=0;return ''
        if card['status']=='pause':self.remaining=0;return ''
        self.pending=dict(step=step+1,observation_hash=fingerprint(following),card=card)
        return '\n[UNRESOLVED REPAIR CASE: working hypotheses, update from actual outcomes]\n'+json.dumps(card,ensure_ascii=False)

    def choose(self,step,observation,proposed):
        pending=self.pending
        eligible=bool(pending and pending['step']==step and pending['observation_hash']==fingerprint(observation))
        chosen=proposed
        if eligible and self.mode=='execute':
            card=pending['card'];chosen=dict(reasoning=card['next']['changes']+' Expected: '+card['next']['expected'],action=card['next']['action'])
        self.events.append(dict(type='persistent_choice',step=step,eligible=eligible,
            mode=self.mode,proposed=proposed['action'],chosen=chosen['action'],changed=chosen['action']!=proposed['action']))
        return chosen


def apply_choice(actor,step,observation,proposed,controller):
    """Keep the shared actor's conversation about actions actually executed."""
    chosen=controller.choose(step,observation,proposed)
    # No-op means no change to the complete response OR conversation. In
    # particular, equal commands must not introduce a new explanatory history.
    if chosen['action']==proposed['action']:return proposed
    old='Reasoning: '+proposed['reasoning'].strip()+'\nAction: '+proposed['action'].strip()+'\n'
    assert actor.memory.endswith(old)
    actor.memory=actor.memory[:-len(old)]+'Reasoning: '+chosen['reasoning'].strip()+'\nAction: '+chosen['action'].strip()+'\n'
    return chosen
