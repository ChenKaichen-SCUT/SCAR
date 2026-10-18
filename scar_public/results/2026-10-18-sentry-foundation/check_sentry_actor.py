"""No-API equality smoke against the pinned upstream LongContext actor."""
import json
from types import SimpleNamespace
from agents.long_context_agent import create_long_context_agent
from scar_public.sentry_evidence import LongContextActor

class Provider:
    def __init__(self):self.calls=[]
    def generate(self,user_prompt,system_prompt):
        self.calls.append((user_prompt,system_prompt))
        return dict(response=json.dumps(dict(reasoning='Observe the actual item.',action='inspect item')),
            num_input_tokens=0,num_output_tokens=0)
class Physical:
    def __init__(self,id,name):self.available_actions=[]

a=Provider();b=Provider()
cfg=SimpleNamespace(available_actions=[],__post_init__=lambda:None,get_llm=lambda:a,
    enable_reflection=False,enable_summarization=False,action_prompt='What should I do next? Return only the JSON object.',
    system_prompt='Same game action schema',response_parser=json.loads,
    format_response=lambda p:'Reasoning: '+p['reasoning']+'\nAction: '+p['action'])
original=create_long_context_agent(Physical)('actor','actor',cfg)
ours=LongContextActor(b,cfg.system_prompt)
for text in ('First public observation','Second public observation','Third public observation'):
    x=original._act({'text':text});y=ours.act(text)
    assert x[0]==y[0]['action'] and a.calls[-1]==b.calls[-1]
    assert original.memory.context==ours.memory
print(json.dumps(dict(upstream_prompt_memory_action_matches=3,paid_calls=0)))
