"""Remove only stale-goal default arbitration authority; preserve LLM inputs.

The saved goal/facts/history are deliberately untouched, per user choice.
Public REJECT checks, acquisition bounds, syntax fallback and the frozen
transaction still run. This is not a controller bypass or a new target picker.
"""
import copy
import re
from contextlib import contextmanager
from contextvars import ContextVar
from scar_v3.state import PublicState,parse_action
from scar_stage18 import arbitration as original_arbitration
from scar_stage18_fixed.agent import Controller18Fixed,rebind

ACTIVE=ContextVar('stage23_reset_gate',default=None)
STAGNATION_STEPS=12
FAILED_GOAL_ATTEMPTS=3
DEFAULT_REASON='retain_structured_default_when_evidence_does_not_resolve'


class ResetGate:
    def __init__(self,variant,start,history=()):
        self.variant=variant;self.start=start;self.identity=None;self.age=0
        self.failed=0;self.released=None;self.events=[];self.last={}
        # Warm only generic counters; past triggers are not applied retroactively.
        for r in history:
            c=r['decision']['controller_before']
            self._identity(c)
            self.observe(r['action'],r['feedback'],c)

    def _identity(self,c):
        ident=(c['generation'],c['target'])
        if ident!=self.identity:
            self.identity=ident;self.age=0;self.failed=0;self.released=None
        return ident

    def before(self,step,controller,obs):
        c=controller.to_dict();ident=self._identity(c)
        state=PublicState.observe(obs);goal=parse_action(c['target'])
        # Reaching a public destination contradicts continuing to demand that
        # already satisfied move when no new explicit instruction repeats it.
        reached=(goal.verb=='enter' and state.location is not None and
            state.location.split(',')[-1].strip()==goal.target and state.goal!=c['target'])
        changed_statement=bool(state.goal and state.goal!=c['target'])
        reasons=[]
        if self.age>=STAGNATION_STEPS:reasons.append('registered_goal_unchanged_12_transitions')
        if self.failed>=FAILED_GOAL_ATTEMPTS:reasons.append('three_consecutive_goal_attempt_failures')
        if reached:reasons.append('current_public_location_already_satisfies_enter_goal')
        if changed_statement:reasons.append('new_explicit_public_statement_disagrees')
        trigger=(self.variant=='Oracle-Reset' and step==self.start) or (self.variant=='Stage18-Reset' and bool(reasons))
        newly=bool(trigger and c['target'] and self.released!=ident)
        if newly:
            self.released=ident
            self.events.append(dict(step=step,goal=c['target'],generation=c['generation'],
                reasons=['oracle_checkpoint_release'] if self.variant=='Oracle-Reset' else reasons,
                prior_goal_age=self.age,consecutive_goal_failures=self.failed))
        self.last=dict(step=step,triggered=newly,active=self.variant!='Stage18-Origin' and self.released==ident,
            goal=c['target'],generation=c['generation'],generic_reasons=reasons,
            goal_age=self.age,consecutive_goal_failures=self.failed)
        return copy.deepcopy(self.last)

    def observe(self,action,after,controller_before):
        self._identity(controller_before);self.age+=1
        g=parse_action(controller_before['target']);a=parse_action(action)
        if (g.verb,g.target)==(a.verb,a.target):
            feedback=PublicState.observe(after).feedback
            self.failed=self.failed+1 if re.search(r'\b(?:Cannot|Invalid)\b',feedback) else 0

    def allows(self,controller):
        return (self.variant!='Stage18-Origin' and self.released==
                (controller.generation,controller.target))

    @contextmanager
    def enabled(self):
        token=ACTIVE.set(self)
        try:yield
        finally:ACTIVE.reset(token)


class ResetArbitration:
    @staticmethod
    def choose(controller,proposal,candidate,checks):
        original,reason=original_arbitration.choose(controller,proposal,candidate,checks)
        gate=ACTIVE.get()
        if (gate is not None and gate.allows(controller) and reason==DEFAULT_REASON and
                checks['llm']['status']!='REJECT'):
            return proposal,'stage23_released_stale_goal_default'
        return original,reason


class ResetController(Controller18Fixed):
    # Exact frozen choose code object and transaction, only one dependency
    # replaced. With the gate off it produces byte-identical original decisions.
    choose=rebind(Controller18Fixed.choose,arbitration=ResetArbitration)


def attach(agent,variant):
    agent.controller.__class__=Controller18Fixed if variant=='Stage18-Origin' else ResetController
