"""Same DeepSeek STM call, independently toggled mechanisms; no oracle inputs."""
from functools import lru_cache
import json
from pathlib import Path
from agents.fixed_size.short_term_memory_agent import ShortTermMemoryAgent
from scar.agents.scar.repair import valid_syntax
from scar.agents.scar.state import action_key
from scar.io import atomic_json
from scar_stage15.controller import METHODS, Controller15
make_controller=Controller15
restore_controller=Controller15.from_dict
import copy
from scar_stage15.knowledge import PublicFacts15 as PublicFacts




class UnknownAgent(ShortTermMemoryAgent):
    options=(True,'learned',True,True)
    stage7_flags={}
    method="P1"

    def __init__(self,id,name,cfg=None):
        super().__init__(id,name,cfg)
        directed,batch,self.use_facts,self.use_fifo=self.options
        self.controller=make_controller(self.method);self.facts=PublicFacts()
        self.decision={};self.events=[];self.memory_paths=['memory.json','unknown.json']

    def set_recovery_objective(self,action,goal):
        self.controller.set_goal(action,goal);self.facts.set_goal(action,goal)

    def observe_transition(self,before,action,after):
        self.controller.observe(before,action,after);self.facts.observe(before,action,after)
        self.events+=self.controller.events;self.controller.events.clear()

    def _act(self,obs):
        summary={};original=self.cfg.system_prompt
        if self.use_facts:
            text,summary=self.facts.render(obs)
            self.cfg.system_prompt=original+'\n'+text
        try:
            proposal,tin,tout,response=ShortTermMemoryAgent._act(self,obs)
        finally:self.cfg.system_prompt=original
        pre_decision=copy.deepcopy(self.controller.to_dict())
        actual=self.controller.choose(obs,proposal) if self.use_fifo else proposal
        if not valid_syntax(actual,self.available_actions):
            self.events.append({'event':'format_fallback','actual':actual});actual='wait' if self.method in METHODS else proposal
        self.decision={'proposed_action':proposal,'executed_action':actual,
            'intercepted':action_key(actual)!=action_key(proposal),
            'all_proposals':list(dict.fromkeys([proposal,actual])),'rule_predictions':[],
            'reason':'fifo_simple_mechanisms' if self.use_fifo else 'stm_with_public_facts',
            'structured':self.controller.last_choice if self.use_fifo else {},
            'fact_summary':summary,'extra_repair_call':False, 'stage7_state_before':pre_decision, 'stage7_flags':dict(self.controller.flags), 'stage15_method':self.method}
        self.short_term_memory[-1]=f"{obs['text']}\nProposed: {proposal}\nExecuted action: {actual}"
        self.events+=self.controller.events;self.controller.events.clear()
        return actual,tin,tout,response

    def save_memory(self,directory):
        super().save_memory(directory)
        atomic_json(Path(directory)/'unknown.json',{'controller':self.controller.to_dict(),'facts':self.facts.to_dict()})

    def load_memory(self,directory):
        super().load_memory(directory);data=json.loads((Path(directory)/'unknown.json').read_text())
        self.controller=restore_controller(data['controller']);self.facts=PublicFacts.from_dict(data['facts'])


@lru_cache(None)
def create_agent(base,method):
    return type(f'Unknown{method}__{base.__name__}',(UnknownAgent,base),{'method':method,'__module__':base.__module__})


def make_agent(algorithm,game,provider,settings,memory_dir):
    if algorithm=='P0':
        from scar_stage10.agent import make_agent as frozen
        return frozen('S1',game,provider,settings,memory_dir)
    from scar.integration import DeepSeekMemoryConfig
    from utils import dynamic_load_game_class
    cfg=DeepSeekMemoryConfig(llm_name=settings['model'],llm_provider='deepseek',embed_name=settings['embedding_model'],
        max_new_tokens=settings['max_tokens'],temperature=settings['temperature'],short_term_memory_size=5,
        torch_seed=settings.get('seed',42),full_mem_path=str(memory_dir))
    cfg.scar_provider=provider
    return create_agent(dynamic_load_game_class(game,'agent','Agent'),algorithm)('agent_adam_davis','adam_davis',cfg)
