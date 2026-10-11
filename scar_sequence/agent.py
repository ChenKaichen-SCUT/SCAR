"""Same STM proposal and DeepSeek call; deterministic public-only intervention."""
from functools import lru_cache
import json
from pathlib import Path
from agents.fixed_size.short_term_memory_agent import ShortTermMemoryAgent
from scar.agents.scar.repair import valid_syntax
from scar.agents.scar.state import action_key
from scar.io import atomic_json
from scar_sequence.planner import Controller


class StructuredAgent(ShortTermMemoryAgent):
    mode = 'srp'
    def __init__(self, id, name, cfg=None):
        super().__init__(id,name,cfg)
        self.controller = Controller(self.mode)
        self.decision, self.events = {}, []
        self.memory_paths = ['memory.json','structured.json']

    def set_recovery_objective(self, target_action, public_objective):
        self.controller.set_goal(target_action, public_objective,
                                 'Follow the current publicly announced task' in public_objective)

    def observe_transition(self, before, action, after):
        self.controller.observe(before,action,after)
        self.events += self.controller.events
        self.controller.events.clear()

    def _act(self, obs):
        proposal, tin, tout, response = ShortTermMemoryAgent._act(self,obs)
        actual = self.controller.choose(obs,proposal)
        if not valid_syntax(actual, self.available_actions):
            self.events.append({'event':'structured_format_fallback','action':actual})
            actual = proposal
        intercepted = action_key(actual) != action_key(proposal)
        self.decision = {'proposed_action': proposal, 'executed_action': actual,
            'intercepted': intercepted, 'all_proposals': list(dict.fromkeys([proposal,actual])),
            'rule_predictions': [], 'reason': self.controller.last_choice['reason'],
            'structured': self.controller.last_choice, 'extra_repair_call': False}
        self.short_term_memory[-1] = f"{obs['text']}\nProposed: {proposal}\nExecuted action: {actual}"
        self.events += self.controller.events; self.controller.events.clear()
        return actual,tin,tout,response

    def save_memory(self, directory):
        super().save_memory(directory)
        atomic_json(Path(directory)/'structured.json',self.controller.to_dict())

    def load_memory(self, directory):
        super().load_memory(directory)
        self.controller = Controller.from_dict(json.loads((Path(directory)/'structured.json').read_text()))


@lru_cache(None)
def create_agent(base, mode):
    return type(f'Structured{mode}__{base.__name__}',(StructuredAgent,base),{'mode':mode,'__module__':base.__module__})


def make_agent(algorithm, game, provider, settings, memory_dir):
    if algorithm not in {'SRP','ResourceFIFO'}:
        from scar_v3.agent import make_agent as original
        return original(algorithm,game,provider,settings,memory_dir)
    from scar.integration import DeepSeekMemoryConfig
    from utils import dynamic_load_game_class
    cfg = DeepSeekMemoryConfig(llm_name=settings['model'],llm_provider='deepseek',
        embed_name=settings['embedding_model'],max_new_tokens=settings['max_tokens'],
        temperature=settings['temperature'],short_term_memory_size=5,
        torch_seed=settings.get('seed',42),full_mem_path=str(memory_dir))
    cfg.scar_provider = provider
    return create_agent(dynamic_load_game_class(game,'agent','Agent'),
                        'srp' if algorithm == 'SRP' else 'fifo')('agent_adam_davis','adam_davis',cfg)
