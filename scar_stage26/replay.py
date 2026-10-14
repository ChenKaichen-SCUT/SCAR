"""Exact saved-response provider for a network-disabled replay."""
from scar.io import digest
from .common import *

class Saved:
    def __init__(self,records):
        self.responses={(q['step'],q['ordinal']):q for q in records if q['status']=='ok'};self.calls=[]
    def begin_step(self,n):self.step=n;self.ordinal=0
    def generate(self,user_prompt,system_prompt=None,**kw):
        self.ordinal+=1;q=self.responses[self.step,self.ordinal]
        assert q['messages']==[dict(role='system',content=system_prompt),dict(role='user',content=user_prompt)],(self.step,self.ordinal,'context')
        self.calls.append((self.step,self.ordinal))
        return dict(response=q['raw_response']['choices'][0]['message']['content'],num_input_tokens=q['usage']['prompt_tokens'],num_output_tokens=q['usage']['completion_tokens'])
