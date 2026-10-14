from scar_stage22.integration import MemoryConfig
from scar_stage22.config import EMBEDDING_PATH
from scar_stage25.integration import make_agent as original_agent
from .common import MODEL,AGENT_ID

def make_agent(seed,method,provider,memory):
    if method=='AGC-v2':return original_agent('remnant',seed,provider,memory)
    from agents.rec_v1.agent import create_rec
    from utils import dynamic_load_game_class
    base=dynamic_load_game_class('remnant','agent','Agent')
    cfg=MemoryConfig(llm_name=MODEL['model'],llm_provider='deepseek',max_new_tokens=MODEL['max_tokens'],
        temperature=MODEL['temperature'],top_p=MODEL['top_p'],presence_penalty=MODEL['presence_penalty'],torch_seed=seed,
        short_term_memory_size=5,embed_name=EMBEDDING_PATH,full_mem_path=str(memory))
    cfg.audited_provider=provider
    return create_rec(base)(AGENT_ID,'adam_davis',cfg)
