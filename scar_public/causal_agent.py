"""Opt-in V6 shadow integration. Learns/checks rules without overriding actions."""
import json

from scar_public.causal_model import CausalMonitor, PREFIXES, ProposalError, request_proposal
from scar_public.causal_compiler import fragment_check
from scar_public.obligation_agent import ObligationAgent, ObligationMemory


class CausalMemory(ObligationMemory):
    def __init__(self):
        super().__init__()
        self.causal = CausalMonitor()
        self.causal_calls = 0
        self.causal_errors = []
        self.causal_attempted = []
        self.causal_final_observed = False

    def prompt(self, observation):
        if self.causal_final_observed:
            if self.causal.observations[-1] != observation:
                raise ValueError('Resumed observation differs from the recorded final public state')
            self.causal_final_observed = False
        else:
            self.causal.observe(observation, self.last_action if self.causal.observations else None)
        return super().prompt(observation)  # Shadow mode preserves V6's actor prompt exactly.

    def state(self):
        result = super().state()
        result['causal'] = self.causal.state()
        return result

    def load(self, state):
        base = {k: v for k, v in state.items() if k != 'causal'}
        super().load(base)
        if 'causal' in state:
            self.causal = CausalMonitor.load(state['causal'])
        else:
            # Public V6 checkpoints are allowed; no environment pickle is read here.
            import re
            actions = {int(i): a for i, a in re.findall(r'^Action (\d+): (.*)$', self.ledger, re.M)}
            self.causal = CausalMonitor()
            for i, observation in enumerate(self.observations):
                self.causal.observe(observation, actions.get(i-1) if i else None)


class CausalShadowAgent(ObligationAgent):
    def __init__(self, llm, system_prompt, max_model_calls=6):
        super().__init__(llm, system_prompt)
        self.notebook = CausalMemory()
        self.max_model_calls = max_model_calls

    def observe_terminal(self, obs):
        memory = self.notebook
        if not memory.causal_final_observed:
            memory.causal.observe(obs['text'], memory.last_action)
            memory.causal_final_observed = True

    def act(self, obs):
        action, input_tokens, output_tokens, raw = super().act(obs)
        memory, usage = self.notebook, {}
        monitor = memory.causal
        known = monitor.rules.get(action, [])
        rejected = any(r['status'].startswith('rejected') for r in known)
        key = (action, sum(r['status'].startswith('rejected') for r in known))
        attempted = [list(k) for k in memory.causal_attempted]
        if (action.startswith(PREFIXES) and (not known or rejected)
                and list(key) not in attempted and memory.causal_calls < self.max_model_calls):
            memory.causal_calls += 1
            memory.causal_attempted.append(list(key))
            try:
                _, usage = request_proposal(self.llm, monitor, action)
            except (ProposalError, RuntimeError) as error:
                usage = getattr(error, 'usage', {})
                memory.causal_errors.append({'step': self.llm.step, 'type': type(error).__name__,
                                             'reason': str(error)[:200]})
        fragment = fragment_check(monitor, action) if monitor.rules.get(action) else {
            'status': 'NOT_COMPILED', 'reason': 'no learned candidate rule'}
        prediction = monitor.prepare(action)
        parsed = json.loads(raw)
        parsed['causal_shadow'] = {'prediction': prediction, 'action_override': False,
                                  'fragment': fragment,
                                  'model_calls': memory.causal_calls,
                                  'recent_feedback': [e for e in monitor.events if e['kind'] == 'feedback'][-1:],
                                  'scope': 'candidate transition hypotheses, not task success'}
        return (action, input_tokens + usage.get('prompt_tokens', 0),
                output_tokens + usage.get('completion_tokens', 0), json.dumps(parsed, ensure_ascii=False))
