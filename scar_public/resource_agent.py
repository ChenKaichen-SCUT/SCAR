"""Opt-in V6 controller for model-relative resource experiments (no extra LLM).

V6/LLM chooses the method target. The finite planner chooses a verified experiment
or direct policy, follows real observation branches, and returns to V6 on gaps.
"""
from dataclasses import asdict
import json

from scar_public.causal_model import digest
from scar_public.obligation_agent import ObligationAgent, ObligationMemory
from scar_public.resource_competition import Recipe, ResourceProblem, ResourceGap, compile_resources, select_experiment
from scar_public.resource_trial import TrialSession, from_public, make_trial

OPTIONS = dict(horizon=6,mode='preserve_opportunity',max_states=12000,
               expansion_budget=600,prefix_depth=2,max_prefixes=40,max_extra_actions=0)


class ResourceMemory(ObligationMemory):
    def __init__(self):
        super().__init__()
        self.resource_trials = []
        self.resource_trial_state = None
        self.resource_attempts = []

    def resource_feedback(self):
        summaries=[]
        for row in self.resource_trials[-3:]:
            selection=row.get('selection')
            summaries.append({k:selection.get(k) for k in ('status','guarantee_mode','prefix',
                'success_exempt_models','reason')} if selection else row)
        return '\nResource competition audit (conditional local model, never full-task success):\n'+json.dumps(summaries,ensure_ascii=False)


def restore_trial(saved):
    data = dict(saved['problem'])
    data['recipes'] = tuple(Recipe(r['output'],tuple(tuple(n) for n in r['needs']),tuple(r['stations']),
        tuple(r['quantity_modes']),tuple(r['access_modes']),tuple(r['quantities'])) for r in data['recipes'])
    for name in ('locations','items','assumptions'): data[name] = tuple(data[name])
    data['protected_totals'] = tuple(tuple(t) for t in data['protected_totals'])
    options = saved['options']
    compiled = compile_resources(ResourceProblem(**data),horizon=options['horizon'],max_states=options['max_states'])
    report,witness,planner = select_experiment(compiled,**{k:v for k,v in options.items() if k not in ('horizon','max_states')})
    if witness is None or compiled.fingerprint != saved['fingerprint']:
        raise ResourceGap('checkpoint reconstruction has no matching certificate')
    session = TrialSession(compiled,report,witness,planner)
    for feedback in saved['feedback']:
        if session.action() != feedback['action']:
            raise ResourceGap('checkpoint policy differs; replan required')
        session.observe(feedback['text'])
    if session.action() != saved['pending_action']:
        raise ResourceGap('checkpoint pending command differs; replan required')
    return session


class ResourceController:
    def __init__(self, memory):
        self.memory = memory; self.session = None

    def program(self, action):
        session = self.session
        return {'reasoning':'Execute a conditional resource policy, then check fresh public feedback.',
                'action':action,'decision_source':'resource_competition',
                'resource_competition':{'fingerprint':session.compiled.fingerprint,
                    'guarantee_mode':session.result['guarantee_mode'],'action_override':True,
                    'surviving_models':sorted({n for n,_ in session.belief}),
                    'recent_feedback':session.events[-1:], 'scope':'local craft-and-hold milestone'},
                'frame':{**self.memory.frame,'expected':'Observe quantities and accessibility; invalidate on mismatch.'}}

    def save_pending(self, action):
        self.memory.resource_trial_state['pending_action'] = action

    def resume(self, text):
        memory = self.memory; saved = memory.resource_trial_state
        if not saved: return None
        try:
            if self.session is None: self.session = restore_trial(saved)
            action = self.session.pending
            if action != memory.last_action:
                raise ResourceGap('actual previous action differs from certified command')
            self.session.observe(text)
            saved['feedback'].append({'action':action,'text':text})
            following = self.session.action()
            if following:
                self.save_pending(following); return self.program(following)
            memory.resource_trials.append(self.session.summary())
            if self.session.status == 'LOCAL_MILESTONE_CONFIRMED':
                memory.resource_target=''; memory.resource_fresh=False
        except ResourceGap as error:
            memory.resource_trials.append({'status':'RESUME_INVALIDATED','reason':str(error)})
        self.session = None; memory.resource_trial_state = None
        return None

    def consider(self, parsed, text, step):
        memory = self.memory
        target = parsed.get('resource_target','')
        if parsed['action'].startswith('craft '): target = parsed['action'].split()[-1]
        if not target or target not in memory.model.recipes or len(memory.resource_attempts) >= 6:
            return parsed
        signature = digest([target,memory.model.current,memory.model.containers])
        if signature in memory.resource_attempts or step+OPTIONS['horizon']>300: return parsed
        try:
            # Missing public evidence is an admission failure, not a search.
            # Do not exhaust the finite computation budget before a grounded
            # problem exists (or suppress it after new station evidence arrives).
            from_public(memory.model,text,target)
            memory.resource_attempts.append(signature)
            report,session = make_trial(memory.model,text,target,**OPTIONS)
            memory.resource_trials.append({'selection':report,'step':step})
            if session:
                self.session=session; action=session.action()
                memory.resource_trial_state={'problem':asdict(session.compiled.domain.problem),'options':dict(OPTIONS),
                    'fingerprint':session.compiled.fingerprint,'feedback':[],'pending_action':action}
                if action: return {**parsed,**self.program(action)}
        except ResourceGap as error:
            memory.resource_trials.append({'status':'GROUNDING_UNKNOWN','step':step,'reason':str(error)})
        return parsed


class ResourceCompetitionAgent(ObligationAgent):
    def __init__(self,llm,system_prompt):
        super().__init__(llm,system_prompt)
        self.notebook=ResourceMemory()
        self.resource_controller=ResourceController(self.notebook)

    def observe_terminal(self, obs):
        if self.notebook.resource_trial_state:
            # No following action is executed at the global budget/environment end.
            self.resource_controller.resume(obs['text'])
            if self.notebook.resource_trial_state:
                report = self.resource_controller.session.summary()
                report['status'] = 'GLOBAL_RUN_ENDED_BEFORE_LOCAL_MILESTONE'
                self.notebook.resource_trials.append(report)
                self.notebook.resource_trial_state = None
                self.resource_controller.session = None
