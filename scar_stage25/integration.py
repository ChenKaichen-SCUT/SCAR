from scar_stage22.integration import MemoryConfig
from scar_stage22.config import EMBEDDING_PATH
from .common import MODEL,AGENT_ID

def make_agent(game,seed,provider,memory,base=None):
    from agents.agc_v2.agent import create_agc_v2
    from utils import dynamic_load_game_class
    base=base or dynamic_load_game_class(game,'agent','Agent')
    cfg=MemoryConfig(llm_name=MODEL['model'],llm_provider='deepseek',max_new_tokens=MODEL['max_tokens'],
        temperature=MODEL['temperature'],top_p=MODEL['top_p'],presence_penalty=MODEL['presence_penalty'],torch_seed=seed,
        short_term_memory_size=5,embed_name=EMBEDDING_PATH,full_mem_path=str(memory))
    cfg.audited_provider=provider
    return create_agc_v2(base)(AGENT_ID,'adam_davis',cfg)
