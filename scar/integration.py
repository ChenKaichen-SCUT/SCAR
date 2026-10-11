"""Extension registration and shared provider configs; upstream sources stay intact."""
from agents.fixed_size.fixed_size_memory_agent_config import FixedSizeMemoryAgentConfig
from agents.rag.rag_agent_config import RAGAgentConfig


class SharedProviderMixin:
    def get_llm(self, **kwargs):
        return self.scar_provider

    def response_parser(self, text):
        import json
        data = json.loads(text)
        if not isinstance(data.get("action"), str) or not data["action"].strip():
            raise ValueError("Malformed action must not become a wait action")
        return {"action": data["action"].strip(), "reasoning": str(data.get("reasoning", ""))}

    def get_device(self):
        return "cpu"


class DeepSeekMemoryConfig(SharedProviderMixin, FixedSizeMemoryAgentConfig):
    pass


class DeepSeekRAGConfig(SharedProviderMixin, RAGAgentConfig):
    pass


def make_agent(algorithm, game, provider, settings, memory_dir):
    from utils import dynamic_load_game_class
    from eval import instantiate_agent
    cls = DeepSeekRAGConfig if algorithm == "VanillaRAGAgent" else DeepSeekMemoryConfig
    cfg = cls(llm_name=settings["model"], llm_provider="deepseek", embed_name=settings["embedding_model"],
              max_new_tokens=settings["max_tokens"], temperature=settings["temperature"],
              short_term_memory_size=5, torch_seed=settings.get("seed", 42), full_mem_path=str(memory_dir))
    cfg.scar_provider, cfg.scar_settings = provider, settings["scar"]
    Agent = dynamic_load_game_class(game, "agent", "Agent")
    info = {"id": "agent_adam_davis", "name": "adam_davis", "cfg": cfg}
    if algorithm == "SCARAgent":
        from scar.agents.scar.agent import create_scar_agent
        return create_scar_agent(Agent)(**info)
    if algorithm == "SimpleFailureRecovery":
        from scar.baselines.simple_recovery import create_simple_recovery_agent
        return create_simple_recovery_agent(Agent)(**info)
    return instantiate_agent(algorithm, info, Agent)


def register_with_eval(provider, settings):
    """Runtime extension of the real eval factory (no copied/modified baseline files)."""
    import eval as official
    original_instantiate, original_build = official.instantiate_agent, official.build_agent_config

    def instantiate(agent_type, agent_info, AgentCls):
        factories = {}
        from scar.agents.scar.agent import create_scar_agent
        from scar.baselines.simple_recovery import create_simple_recovery_agent
        factories.update(SCARAgent=create_scar_agent, SimpleFailureRecovery=create_simple_recovery_agent)
        if agent_type in factories:
            return factories[agent_type](AgentCls)(**agent_info)
        return original_instantiate(agent_type, agent_info, AgentCls)

    def build(agent_type, kwargs):
        if agent_type in {"SCARAgent", "SimpleFailureRecovery"}:
            cfg = DeepSeekMemoryConfig(**kwargs)
            cfg.scar_provider, cfg.scar_settings = provider, settings["scar"]
            return cfg
        return original_build(agent_type, kwargs)

    official.instantiate_agent, official.build_agent_config = instantiate, build
    return original_instantiate, original_build
