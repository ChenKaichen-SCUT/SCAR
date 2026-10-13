"""Factories accept public objective/history only, never task/evaluator records."""
import copy
from scar_stage16.agent import make_agent as frozen_agent
from scar_stage16.config import BaselineConfig, OBJECTIVE_PREFIX
from scar.integration import DeepSeekMemoryConfig
from utils import dynamic_load_game_class
from .budget_adapter import adapt


def make_method(method, game, provider, objective, target, history, folder):
    base=dynamic_load_game_class(game,'agent','Agent')
    if method=='A0':
        agent=adapt(frozen_agent(provider,game=game,config=BaselineConfig(seed=42),memory_dir=str(folder)))
        agent.initialize_episode(history,'craft 1 '+target,objective)
        return agent
    cfg=DeepSeekMemoryConfig(llm_name='deepseek-flash',llm_provider='deepseek',
        embed_name='sentence-transformers/all-MiniLM-L6-v2',max_new_tokens=768,temperature=0.7,
        short_term_memory_size=5,torch_seed=42,full_mem_path=str(folder),
        enable_reflection=False,enable_summarization=False)
    cfg.scar_provider=provider
    if method=='A1':
        from agents.fixed_size.short_term_memory_agent import create_short_term_memory_agent
        cls=create_short_term_memory_agent(base)
    elif method=='A2':
        from agents.long_context_agent import create_long_context_agent
        cls=create_long_context_agent(base)
    elif method=='A3':
        from third_party_adapters.adaplanner_agentodyssey import AdaPlanner
        cls=type('AdaPlanner17',(AdaPlanner,base),{})
    elif method=='A4':
        from .dag import DAGPlanner
        cls=type('DAGPlanner17',(DAGPlanner,base),{})
    else:raise ValueError(method)
    agent=cls('agent_adam_davis','adam_davis',cfg)
    agent.cfg.system_prompt+=OBJECTIVE_PREFIX+objective
    if method in ('A1','A2'):
        for h in history:agent.memorize(f"{h['before']['text']}\nAction: {h['action']}\n{h['after']['text']}")
        agent.memorize('Recovery objective: '+objective)
    else:agent.initialize(history,target,objective)
    return agent


def decision_state(agent, method):
    if method=='A0':
        return dict(decision=copy.deepcopy(agent.decision),controller=copy.deepcopy(agent.controller.to_dict()),
                    memory=list(agent.short_term_memory))
    if method=='A1':return dict(memory=list(agent.short_term_memory))
    if method=='A2':return dict(history=agent.memory.context,history_characters=len(agent.memory.context),truncated=False)
    return copy.deepcopy(agent.export())
