"""Direct game-agent entry point with an explicitly supplied model provider.

No credentials, provider factory, task catalogue or experiment runner are read.
observe_transition is the sole ingestion point for real public feedback.
"""
import copy
import json
from functools import lru_cache
from pathlib import Path
from agents.fixed_size.short_term_memory_agent import ShortTermMemoryAgent
from scar.agents.scar.repair import valid_syntax
from scar.agents.scar.state import action_key
from scar.io import atomic_json
from scar_unknown17.facts import PublicFacts
from . import config as frozen
from .controller import make_controller, dump_controller, restore_controller
from .knowledge import PublicFacts16
from .state import PublicRuleState


class BaselineAgent(ShortTermMemoryAgent):
    variant = 'S1_P1_P3'

    def __init__(self, id, name, cfg=None):
        super().__init__(id, name, cfg)
        self.controller = make_controller(self.variant)
        self.facts = PublicFacts() if self.variant == 'S1' else PublicFacts16()
        self.decision, self.events = {}, []
        self.memory_paths = ['memory.json', 'baseline.json']

    @property
    def public_state(self):
        return PublicRuleState(self.controller)

    def set_recovery_objective(self, action, goal):
        self.controller.set_goal(action, goal)
        self.facts.set_goal(action, goal)

    def initialize_episode(self, history, target_action, public_goal):
        """Fresh agent only. History consists solely of public transitions."""
        if self.controller.in_episode or self.short_term_memory:
            raise ValueError('initialize_episode requires a fresh agent')
        self.cfg.system_prompt += frozen.OBJECTIVE_PREFIX + public_goal
        for transition in history:
            before, action, after = (transition[k] for k in ('before', 'action', 'after'))
            self.memorize(f"{before['text']}\nAction: {action}\n{after['text']}")
            self.observe_transition(before, action, after)
        self.memorize('Recovery objective: '+public_goal)
        self.set_recovery_objective(target_action, public_goal)

    def observe_transition(self, before, action, after):
        self.controller.observe(before, action, after)
        self.facts.observe(before, action, after)
        self.events += self.controller.events
        self.controller.events.clear()

    def _act(self, obs):
        original = self.cfg.system_prompt
        text, summary = self.facts.render(obs)
        self.cfg.system_prompt = original+'\n'+text
        try:
            proposal, tin, tout, response = ShortTermMemoryAgent._act(self, obs)
        finally:
            self.cfg.system_prompt = original
        before = dump_controller(self.controller)
        actual = self.controller.choose(obs, proposal)
        if not valid_syntax(actual, self.available_actions):
            self.events.append({'event': 'format_fallback', 'actual': actual})
            actual = 'wait'
        self.decision = {
            'proposed_action': proposal, 'executed_action': actual,
            'intercepted': action_key(actual) != action_key(proposal),
            'all_proposals': list(dict.fromkeys([proposal, actual])), 'rule_predictions': [],
            'reason': 'fifo_simple_mechanisms', 'structured': self.controller.last_choice,
            'fact_summary': summary, 'extra_repair_call': False,
            'controller_before': before, 'variant': self.variant,
        }
        self.short_term_memory[-1] = f"{obs['text']}\nProposed: {proposal}\nExecuted action: {actual}"
        self.events += self.controller.events
        self.controller.events.clear()
        return actual, tin, tout, response

    def save_memory(self, directory):
        super().save_memory(directory)
        atomic_json(Path(directory)/'baseline.json', {
            'schema_version': frozen.SCHEMA_VERSION, 'variant': self.variant,
            'controller': dump_controller(self.controller), 'facts': self.facts.to_dict(),
            'system_prompt': self.cfg.system_prompt, 'action_prompt': self.cfg.action_prompt,
            'model': frozen.MODEL, 'stm_size': frozen.STM_SIZE,
        })

    def load_memory(self, directory):
        data = json.loads((Path(directory)/'baseline.json').read_text())
        if (data.get('schema_version') != frozen.SCHEMA_VERSION or data.get('variant') != self.variant
                or data.get('model') != frozen.MODEL or data.get('stm_size') != frozen.STM_SIZE
                or data.get('action_prompt') != self.cfg.action_prompt):
            raise ValueError('incompatible frozen agent checkpoint')
        controller = restore_controller(data['controller'], self.variant)
        facts = copy.deepcopy(data['facts'])
        if self.variant == 'S1' and ('knowledge' in facts['table'] or 'knowledge15' in facts['table']):
            raise ValueError('S1 checkpoint contains repaired facts')
        facts = (PublicFacts if self.variant == 'S1' else PublicFacts16).from_dict(facts)
        super().load_memory(directory)
        if self.short_term_memory_size != frozen.STM_SIZE:
            raise ValueError('STM size differs from frozen baseline')
        self.controller, self.facts = controller, facts
        self.cfg.system_prompt = data['system_prompt']


@lru_cache(None)
def create_agent(base, variant):
    frozen.BaselineConfig(variant)
    return type(f'SCAR16{variant}__{base.__name__}', (BaselineAgent, base),
                {'variant': variant, '__module__': base.__module__})


def make_agent(provider, *, game='robot_kingdom', config=None, memory_dir='memory_stage16'):
    """Provider.generate(user, system) uses the existing STM response contract.

The caller supplies the provider configured for deepseek-flash, thinking disabled,
max_tokens=768, temperature=0.7. A capture provider suffices for offline checks.
"""
    from scar.integration import DeepSeekMemoryConfig
    from utils import dynamic_load_game_class
    config = config or frozen.BaselineConfig()
    cfg = DeepSeekMemoryConfig(llm_name=frozen.MODEL, llm_provider='deepseek',
        embed_name=frozen.EMBEDDING_MODEL, max_new_tokens=frozen.MAX_TOKENS,
        temperature=frozen.TEMPERATURE, short_term_memory_size=frozen.STM_SIZE,
        torch_seed=config.seed, full_mem_path=str(memory_dir))
    cfg.scar_provider = provider
    return create_agent(dynamic_load_game_class(game, 'agent', 'Agent'), config.variant)(
        'agent_adam_davis', 'adam_davis', cfg)
