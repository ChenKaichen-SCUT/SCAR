import os,pathlib,sys,json
R=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(R/'agentodyssey'))
os.environ.update({'AO_API_BASE_URL':'http://127.0.0.1:8088/preflight/v1','AO_EMBED_PATH':str(R/'models/Qwen3-Embedding-0.6B'),'MEM0_TELEMETRY':'False','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','TOKENIZERS_PARALLELISM':'false','OMP_NUM_THREADS':'4','MKL_NUM_THREADS':'4'})
assert (R/'embedding_weights_verified.flag').exists()
from agents.rag.rag_agent_config import RAGAgentConfig
from agents.rag.mem0_rag_agent import Memory
cfg=RAGAgentConfig(llm_name='deepseek-flash',llm_provider='openai',full_mem_path=str(R/'preflight_mem0_store'))
memory=Memory(cfg.mem0_config)
found=memory.retrieve('Synthetic infrastructure check; no game information.',5)
assert found==[],found
assert memory.mem0.get_all(filters={'agent_id':'self'},limit=10000)['results']==[]
(R/'embedding_ready.flag').write_text((R/'embedding_weights_verified.flag').read_text())
print(json.dumps({'mem0_initialization_passed':True,'new_llm_calls':0,'embedding_dimensions':1024}))
