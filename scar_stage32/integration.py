from scar_stage22.integration import MemoryConfig
from scar_stage22.config import EMBEDDING_PATH
from .common import MODEL,AGENT_ID
def make_agent(seed,provider,memory):
    from agents.saer.agent import create_saer
    from utils import dynamic_load_game_class
    base=dynamic_load_game_class('remnant','agent','Agent')
    cfg=MemoryConfig(llm_name=MODEL['model'],llm_provider='deepseek',max_new_tokens=MODEL['max_tokens'],temperature=MODEL['temperature'],
        top_p=MODEL['top_p'],presence_penalty=MODEL['presence_penalty'],torch_seed=seed,short_term_memory_size=5,embed_name=EMBEDDING_PATH,full_mem_path=str(memory))
    cfg.audited_provider=provider;return create_saer(base)(AGENT_ID,'adam_davis',cfg)
