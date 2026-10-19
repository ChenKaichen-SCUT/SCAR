"""AgentOdyssey provider adapter: no algorithm or environment information."""
import os
from openai import OpenAI
class DeepSeekLanguageModel:
 def __init__(self,llm_name,max_new_tokens=None,temperature=.7,top_p=.8,presence_penalty=1.5,**kwargs):
  self.client=OpenAI(base_url=os.environ['AO_API_BASE_URL'],api_key='local-proxy',timeout=300,max_retries=2)
  self.llm_name=llm_name;self.max_new_tokens=min(max_new_tokens or 4096,4096)
  self.temperature=temperature;self.presence_penalty=presence_penalty
 def generate(self,user_prompt,system_prompt=None,history=None,**kwargs):
  messages=list(history or [])
  if system_prompt:messages.append({'role':'system','content':system_prompt})
  messages.append({'role':'user','content':user_prompt})
  r=self.client.chat.completions.create(model=self.llm_name,messages=messages,max_tokens=self.max_new_tokens,temperature=self.temperature,presence_penalty=self.presence_penalty)
  content=r.choices[0].message.content
  if not isinstance(content,str) or not content.strip():raise RuntimeError('Empty model content; refusing to silently turn transport failure into a game action')
  return {'response':content,'num_input_tokens':r.usage.prompt_tokens,'num_output_tokens':r.usage.completion_tokens,'reasoning_summary':None,'history':messages+[{'role':'assistant','content':content}]}
