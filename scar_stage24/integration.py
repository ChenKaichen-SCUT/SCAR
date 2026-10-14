from scar_stage22.integration import MemoryConfig
from .common import MODEL,SEED,AGENT_ID


def make_agent(game,provider,memory,base=None):
    from agents.agc.agent import create_agc
    from utils import dynamic_load_game_class
    from scar_stage22.config import EMBEDDING_PATH
    base=base or dynamic_load_game_class(game,'agent','Agent')
    cfg=MemoryConfig(llm_name=MODEL['model'],llm_provider='deepseek',max_new_tokens=MODEL['max_tokens'],
        temperature=MODEL['temperature'],top_p=MODEL['top_p'],presence_penalty=MODEL['presence_penalty'],torch_seed=SEED,
        short_term_memory_size=5,embed_name=EMBEDDING_PATH,full_mem_path=str(memory))
    cfg.audited_provider=provider
    return create_agc(base)(AGENT_ID,'adam_davis',cfg)
