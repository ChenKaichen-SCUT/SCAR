"""Official baseline classes, unchanged; injected audited provider/config only."""
from agents.llm_agent_config import LLMAgentConfig
from agents.fixed_size.fixed_size_memory_agent_config import FixedSizeMemoryAgentConfig
from agents.rag.voyager_agent import VoyagerAgentConfig
from agents.long_context_agent import LongContextAgent
from .config import MODEL, SEED, EMBEDDING_PATH


class ProviderConfig:
    def get_llm(self, **kwargs):
        return self.audited_provider

    def get_device(self):
        return 'cpu'


class PlainConfig(ProviderConfig, LLMAgentConfig):
    pass


class MemoryConfig(ProviderConfig, FixedSizeMemoryAgentConfig):
    # Official STM calls the config, while the official implementation lives
    # on LongContextAgent. Reuse its exact code, with the expected cfg access.
    def construct_user_prompt_long_context(self, memory, observation):
        from types import SimpleNamespace
        return LongContextAgent.construct_user_prompt_long_context(
            SimpleNamespace(cfg=self), memory, observation)


class VoyagerConfig(ProviderConfig, VoyagerAgentConfig):
    pass


def make_agent(method, game, provider, memory_dir, base=None):
    from utils import dynamic_load_game_class
    from eval import instantiate_agent
    from scar_stage18_fixed.agent import create_stage18_fixed
    base = base or dynamic_load_game_class(game, 'agent', 'Agent')
    cls = VoyagerConfig if method == 'VoyagerAgent' else PlainConfig if method == 'NoMemoryAgent' else MemoryConfig
    cfg = cls(llm_name=MODEL['model'], llm_provider='deepseek',
              max_new_tokens=MODEL['max_tokens'], temperature=MODEL['temperature'],
              top_p=MODEL['top_p'], presence_penalty=MODEL['presence_penalty'],
              torch_seed=SEED, embed_name=EMBEDDING_PATH, full_mem_path=str(memory_dir),
              short_term_memory_size=5)
    # Voyager otherwise reconstructs a plain VoyagerAgentConfig and loses the
    # injected get_llm. Supply its real config with actions already attached.
    if method == 'VoyagerAgent':
        cfg.available_actions = base('interface_probe', 'interface_probe').available_actions
        cfg.__post_init__()
        cfg.debug_log_file = str(memory_dir.parent / 'voyager_debug.txt')
    cfg.audited_provider = provider
    info = dict(id='agent_adam_davis', name='adam_davis', cfg=cfg)
    if method == 'Stage18-Fixed':
        return create_stage18_fixed(base)(**info)
    return instantiate_agent(method, info, base)
