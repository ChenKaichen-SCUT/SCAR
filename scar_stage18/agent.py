"""One STM5 request per step; no provider construction in the policy package."""
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
from .controller import Controller18
from .execution_context import render


class Agent18(BaselineAgent):
    def __init__(self, id, name, cfg=None):
        super().__init__(id, name, cfg)
        self.controller = Controller18()
        self.memory_paths = ['memory.json', 'stage18.json']

    @property
    def public_state(self):
        from scar_stage16.state import PublicRuleState
        return PublicRuleState(self.controller.legacy_copy())

    def _act(self, obs):
        self.controller.table.observe(obs)
        text, summary, context = render(self.facts, self.controller, obs)
        original = self.cfg.system_prompt
        self.cfg.system_prompt = original+'\n'+text
        try:
            proposal, tin, tout, response = ShortTermMemoryAgent._act(self, obs)
        finally:
            self.cfg.system_prompt = original
        before = self.controller.to_dict()
        actual = self.controller.choose(obs, proposal)
        if not valid_syntax(actual, self.available_actions):
            # Exceptional syntax fallback is transactional too: no phantom probe.
            self.controller = Controller18.from_dict(before)
            self.controller.audit18 = dict(llm_proposal=proposal, final_action='wait',
                reason='invalid_final_syntax_transaction_rollback', rejected_action=actual)
            self.controller.pending_probe = self.controller.explore_pending = None
            actual = 'wait'
        self.decision = dict(proposed_action=proposal, executed_action=actual,
            intercepted=actual != proposal, all_proposals=list(dict.fromkeys([proposal, actual])),
            structured=copy.deepcopy(self.controller.last_choice),
            controller_before=before, fact_summary=summary, execution_context=context,
            stage18=copy.deepcopy(self.controller.audit18), extra_repair_call=False, variant='SCAR18')
        self.short_term_memory[-1] = f"{obs['text']}\nProposed: {proposal}\nExecuted action: {actual}"
        self.events += self.controller.events
        self.controller.events.clear()
        return actual, tin, tout, response

    def save_memory(self, directory):
        ShortTermMemoryAgent.save_memory(self, directory)
        atomic_json(Path(directory)/'stage18.json', dict(schema_version=1, method='SCAR18',
            controller=self.controller.to_dict(), facts=self.facts.to_dict(),
            system_prompt=self.cfg.system_prompt, action_prompt=self.cfg.action_prompt,
            model=baseline.MODEL, stm_size=baseline.STM_SIZE))

    def load_memory(self, directory):
        data = json.loads((Path(directory)/'stage18.json').read_text())
        assert data['schema_version'] == 1 and data['method'] == 'SCAR18'
        assert data['model'] == baseline.MODEL and data['stm_size'] == baseline.STM_SIZE
        assert data['action_prompt'] == self.cfg.action_prompt
        ShortTermMemoryAgent.load_memory(self, directory)
        assert self.short_term_memory_size == baseline.STM_SIZE
        self.controller = Controller18.from_dict(data['controller'])
        self.facts = PublicFacts16.from_dict(data['facts'])
        self.cfg.system_prompt = data['system_prompt']


@lru_cache(None)
def agent_class(base):
    return type('SCAR18__'+base.__name__, (Agent18, base), {'__module__': base.__module__})


def make_agent(provider, *, game, memory_dir='memory_stage18'):
    from scar.integration import DeepSeekMemoryConfig
    from utils import dynamic_load_game_class
    cfg = DeepSeekMemoryConfig(llm_name=baseline.MODEL, llm_provider='deepseek',
        embed_name=baseline.EMBEDDING_MODEL, max_new_tokens=baseline.MAX_TOKENS,
        temperature=baseline.TEMPERATURE, short_term_memory_size=baseline.STM_SIZE,
        torch_seed=42, full_mem_path=str(memory_dir))
    cfg.scar_provider = provider
    return agent_class(dynamic_load_game_class(game, 'agent', 'Agent'))('agent_adam_davis', 'adam_davis', cfg)


def make_method(method, game, provider, objective, target, history, folder):
    assert method == 'SCAR18'
    agent = make_agent(provider, game=game, memory_dir=folder)
    agent.initialize_episode(history, 'craft 1 '+target, objective)
    return agent


def decision_state(agent, method):
    assert method == 'SCAR18'
    return dict(decision=copy.deepcopy(agent.decision), controller=agent.controller.to_dict(),
                memory=list(agent.short_term_memory))
