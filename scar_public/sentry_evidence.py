"""First isolated Sentry change: bounded access to actual historical outcomes.

This is an evidence-access experiment, not the complete persistent-recovery
algorithm. Author detection, routing, H-step verification and learning stay
unchanged. No SCAR planner, task parser, action substitution or world rule.
"""
import collections
import json
import math
import re


STOP = set('a an the i my me we you it is are was were be been to of and or in on at for with from this that have has had do did can could should would action observation reasoning current previous task agent next cycle'.split())


def terms(text):
    return {w for w in re.findall(r'[a-zA-Z0-9_]+', text.lower()) if len(w)>2 and w not in STOP}


class OutcomeLedger:
    """Keep literal public observations, never the actor's asserted facts."""
    def __init__(self, limit=6, excerpt_chars=1400):
        self.records=[];self.limit=limit;self.excerpt_chars=excerpt_chars

    def add(self, step, action, observation):
        if self.records and step<=self.records[-1]['step']:
            raise ValueError('Only actual, strictly increasing cycles may enter the ledger')
        # Action feedback appears before repeated inventory/context in this
        # benchmark. The excerpt is literal and explicitly not a complete view.
        self.records.append(dict(step=step,action=action,observation=observation[:self.excerpt_chars],
            truncated=len(observation)>self.excerpt_chars))

    def retrieve(self, query, before):
        candidates=[r for r in self.records if r['step']<before]
        if not candidates:return []
        q=terms(query);documents=[terms(r['action']+' '+r['observation']) for r in candidates]
        frequency=collections.Counter(t for d in documents for t in d)
        scored=[]
        for r,d in zip(candidates,documents):
            overlap=q&d
            if not overlap:continue
            action_terms=terms(r['action'])
            score=sum(math.log(1+len(candidates)/(1+frequency[t]))*(3 if t in action_terms else 1) for t in overlap)
            scored.append((score,r['step'],r))
        # Preserve earlier and later outcomes of the same operation, but avoid
        # filling the bounded packet with an unchanged repeated command.
        counts=collections.Counter();picked=[]
        for _,_,r in sorted(scored,key=lambda x:(x[0],x[1]),reverse=True):
            if counts[r['action']]>=2:continue
            picked.append(r);counts[r['action']]+=1
            if len(picked)>=self.limit:break
        return sorted(picked,key=lambda r:r['step'])

    def context(self, query, before):
        records=self.retrieve(query,before)
        if not records:return '',[]
        return ('\nAdditional historical observation excerpts, outside the recent window:\n'+
            json.dumps(records,ensure_ascii=False)+'\nThese are dated historical observations, not current inventory or persistent world facts. '
            'The records may be incomplete. A fact absent from the recent window is not thereby fabricated. '
            'Use historical evidence only for historical claims; current feedback takes precedence for current conditions. '
            'An action string alone does not show success: read its actual observation. '
            'Preserve genuine present failures even if a different historical claim is supported. '
            'You may cite these cycle numbers in the existing evidence field. Keep the original output schema.'),records


class LongContextActor:
    """AgentOdyssey LongContext/ReAct prompt and memory flow, audited transport.

No inherited SCAR actor, notebook or execution gate. Host repair advice is
appended to the conversation as recommended by the author Sentry integration.
"""
    def __init__(self, provider, system):
        self.llm=provider;self.system=system;self.memory='';self.guidance=''

    def act(self, text):
        if self.guidance:
            self.memory += self.guidance+'\n';self.guidance=''
        prompt=('My Memories: '+self.memory if self.memory else '')+f'My Current Observation: {text}\nWhat should I do next? Return only the JSON object.'
        reply=self.llm.generate(prompt,self.system)
        parsed=json.loads(reply['response'])
        self.memory+=text+'\nReasoning: '+parsed['reasoning'].strip()+'\nAction: '+parsed['action'].strip()+'\n'
        return parsed,reply


class EvidenceJudge:
    def __init__(self, provider, ledger, enabled):
        self.provider=provider;self.model=provider.model;self.ledger=ledger;self.enabled=enabled
        self.query='';self.before=0;self.records=[]

    def __call__(self, prompt, **options):
        original=prompt;selected=[]
        if self.enabled and prompt.startswith(('[SENTRY DETECTOR]','[SENTRY ESCAPE VERIFIER]')):
            # The query is public current reasoning/action/observation; neither
            # the whole taxonomy nor hidden evaluation results drives retrieval.
            extra,selected=self.ledger.context(self.query,self.before)
            prompt+=extra
        self.records.append(dict(step=self.provider.step,component=original.splitlines()[0],
            selected_cycles=[r['step'] for r in selected],extra_chars=len(prompt)-len(original)))
        response=self.provider.request([
            {'role':'system','content':'Follow the supplied Sentry evaluation schema. Return the requested JSON only.'},
            {'role':'user','content':prompt}],repair=100,options=options)
        choice=response['choices'][0]
        if choice.get('finish_reason')!='stop':raise RuntimeError('Incomplete Sentry response')
        return choice['message']['content']


class SentryEvidenceHost:
    def __init__(self, provider, system, evidence=False, steps=300):
        from Sentry import SentryRunner
        from Sentry.config import ModelConfig,SentryConfig
        self.ledger=OutcomeLedger();self.judge=EvidenceJudge(provider,self.ledger,evidence)
        self.runner=SentryRunner(self.judge,SentryConfig(model=ModelConfig(model=provider.model)),capture_runtime_events=True)
        self.runner.start_task(objective=f'Complete the main task specified by public game dialogue within {steps} environment actions. Use public observations to learn the task and rules.',action_schema=system)

    def observe(self, step, parsed, following, terminal=False):
        from Sentry import agent_step_from_parts
        self.ledger.add(step,parsed['action'],following)
        self.judge.query=parsed['reasoning']+'\n'+parsed['action']+'\n'+following
        self.judge.before=step-self.runner.config.trace.window_size+1
        cycle=agent_step_from_parts(step_id=step,reasoning=parsed['reasoning'],raw_action=parsed['action'],
            tool_name='game',tool_args={'command':parsed['action']},observation=following,
            parsed_ok=True,schema_valid=True,accepted_by_environment=None)
        repair=self.runner.step(cycle,terminal=terminal)
        if terminal:self.runner.finalize()
        return repair.prompt_text if repair else '',self.runner.guard.drain_runtime_events()
