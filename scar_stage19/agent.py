"""On-demand subgoal requests; deterministic execution makes no model call."""
import copy
import json
from functools import lru_cache
from pathlib import Path
from agents.fixed_size.short_term_memory_agent import ShortTermMemoryAgent
from scar_stage16.agent import BaselineAgent
from scar_stage16.knowledge import PublicFacts16
from scar_stage16 import config as baseline
from scar.agents.scar.repair import valid_syntax
from scar.io import atomic_json
from .controller import Controller19
from .execution_context import render


class Agent19(BaselineAgent):
    def __init__(self, id, name, cfg=None):
        super().__init__(id, name, cfg)
        self.controller = Controller19()
        self.memory_paths = ['memory.json', 'stage19.json']

    @property
    def public_state(self):
        from scar_stage16.state import PublicRuleState
        return PublicRuleState(self.controller.legacy_copy())

    def _act(self, obs):
        from .planning import SYSTEM, FIELDS, validate
        before = self.controller.to_dict()
        action = self.controller.choose(obs)
        called = False
        proposal = acceptance = trigger = summary = None
        tin = tout = 0
        response = ''
        if action is None and self.controller.can_request():
            trigger = copy.deepcopy(self.controller.blocker19)
            prompt, summary = render(self.controller, self.facts, obs, self.short_term_memory)
            self.last_user_prompt = prompt
            self.controller.start_request()
            result = self.cfg.scar_provider.generate(user_prompt=prompt, system_prompt=SYSTEM,
                required=FIELDS, phase='subgoal', max_tokens=baseline.MAX_TOKENS, validator=validate)
            called = True
            proposal = result['parsed']
            acceptance = self.controller.accept(proposal, prompt)
            tin, tout, response = result['num_input_tokens'], result['num_output_tokens'], result['response']
            action = self.controller.choose(obs)
        if action is None:
            action = self.controller.choose(obs, allow_fallback=True)
        if not valid_syntax(action, self.available_actions):
            # Keep real request/acceptance audit, roll back speculative execution.
            failed = action
            post = self.controller
            self.controller = Controller19.from_dict(before)
            for name in ('plan_calls19','request_contexts19','acceptance19'):
                setattr(self.controller, name, copy.deepcopy(getattr(post, name)))
            self.controller.pending_probe = self.controller.explore_pending = None
            self.controller.audit19 = dict(source='invalid_syntax_transaction_rollback', rejected=failed, final_action='wait')
            action = 'wait'
        self.decision = dict(llm_called=called, planning_trigger=trigger, subgoal_proposal=proposal,
            subgoal_acceptance=copy.deepcopy(acceptance), executed_action=action,
            controller_before=before, fact_summary=summary, stage19=copy.deepcopy(self.controller.audit19),
            active_subgoal=copy.deepcopy(self.controller.intent19), variant='SCAR19',
            no_action_proposal_interface=True, extra_repair_call=False)
        self.memorize(f"{obs['text']}\nExecuted action: {action}\nSource: {self.controller.audit19.get('source')}")
        self.events += self.controller.events
        self.controller.events.clear()
        return action, tin, tout, response

    def save_memory(self, directory):
        ShortTermMemoryAgent.save_memory(self, directory)
        atomic_json(Path(directory)/'stage19.json', dict(schema_version=1, method='SCAR19',
            controller=self.controller.to_dict(), facts=self.facts.to_dict(),
            system_prompt=self.cfg.system_prompt, action_prompt=self.cfg.action_prompt,
            model=baseline.MODEL, stm_size=baseline.STM_SIZE))

    def load_memory(self, directory):
        data = json.loads((Path(directory)/'stage19.json').read_text())
        assert data['schema_version'] == 1 and data['method'] == 'SCAR19'
        assert data['model'] == baseline.MODEL and data['stm_size'] == baseline.STM_SIZE
        assert data['action_prompt'] == self.cfg.action_prompt
        ShortTermMemoryAgent.load_memory(self, directory)
        assert self.short_term_memory_size == baseline.STM_SIZE
        self.controller = Controller19.from_dict(data['controller'])
        self.facts = PublicFacts16.from_dict(data['facts'])
        self.cfg.system_prompt = data['system_prompt']


@lru_cache(None)
def agent_class(base):
    return type('SCAR19__'+base.__name__, (Agent19, base), {'__module__': base.__module__})


def make_agent(provider, *, game, memory_dir='memory_stage19'):
    from scar.integration import DeepSeekMemoryConfig
    from utils import dynamic_load_game_class
    cfg = DeepSeekMemoryConfig(llm_name=baseline.MODEL, llm_provider='deepseek',
        embed_name=baseline.EMBEDDING_MODEL, max_new_tokens=baseline.MAX_TOKENS,
        temperature=baseline.TEMPERATURE, short_term_memory_size=baseline.STM_SIZE,
        torch_seed=42, full_mem_path=str(memory_dir))
    cfg.scar_provider = provider
    return agent_class(dynamic_load_game_class(game, 'agent', 'Agent'))('agent_adam_davis', 'adam_davis', cfg)


def make_method(method, game, provider, objective, target, history, folder):
    assert method == 'SCAR19'
    agent = make_agent(provider, game=game, memory_dir=folder)
    agent.initialize_episode(history, 'craft 1 '+target, objective)
    return agent


def decision_state(agent, method):
    assert method == 'SCAR19'
    return dict(decision=copy.deepcopy(agent.decision), controller=agent.controller.to_dict(),
                memory=list(agent.short_term_memory))
