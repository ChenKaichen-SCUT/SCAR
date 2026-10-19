import pathlib,os,sys,json,py_compile
R=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(R/'agentodyssey'))
os.environ['AO_API_BASE_URL']='http://127.0.0.1:8088/preflight/v1'
for name in ['eval.py','providers/deepseek_adapter.py','agents/llm_agent_config.py','agents/fixed_size/fixed_size_memory_agent_config.py','agents/fixed_size/mem1_agent.py','agents/rag/rag_agent_config.py']:
 py_compile.compile(str(R/'agentodyssey'/name),doraise=True)
from eval import build_agent_config,instantiate_agent
from games.base.agent import Agent
opts={'llm_name':'deepseek-flash','llm_provider':'openai','full_mem_path':str(R/'preflight_memory')}
long_cfg=build_agent_config('LongContextAgent',opts)
assert '"memory"' not in long_cfg.system_prompt
class FakeModel:
 def generate(self,**kwargs):return {'response':json.dumps({'memory':'<IS>synthetic memory\nsecond line</IS>','reasoning':'synthetic format validation','action':'wait'}),'num_input_tokens':0,'num_output_tokens':0}
cfg=build_agent_config('Mem1Agent',opts);cfg.get_llm=lambda **kwargs:FakeModel()
agent=instantiate_agent('Mem1Agent',{'id':'test','name':'test','cfg':cfg},Agent)
result=agent._act({'text':'Synthetic format test; no game knowledge.'})
assert result[0]=='wait' and agent.memory.is_text=='synthetic memory\nsecond line'
print('Offline adapter and memory-format checks passed.',flush=True)
# Single non-game connectivity call. No task trajectory is repeated.
from openai import OpenAI
c=OpenAI(base_url=os.environ['AO_API_BASE_URL'],api_key='local-proxy',timeout=300,max_retries=0)
response=c.chat.completions.create(model='deepseek-flash',messages=[{'role':'user','content':'Return the JSON object {"ready":true}.'}],max_tokens=32,temperature=0)
assert json.loads(response.choices[0].message.content)['ready'] is True
(R/'preflight_result.json').write_text(json.dumps({'passed':True,'model':response.model,'usage':response.usage.model_dump(),'non_game_calls':1},indent=2))
print((R/'preflight_result.json').read_text(),flush=True)
