"""One decision's temporary objective; all subsequent prompts are unchanged."""
from scar_stage24.provider import SharedProvider
from scar.io import append_jsonl,digest
from .common import *

class ObjectiveProvider:
    def __init__(self,folder,ident,key):
        self.folder=Path(folder);self.ident=ident;self.meta=read(RESULTS/'checkpoints'/ident/'meta.json')
        self.paid=SharedProvider(folder,RUNTIME,key);self.audit=self.folder/'interventions.jsonl'
        self.records={r['logical_id']:r for r in map(json.loads,self.audit.read_text().splitlines())} if self.audit.exists() else {}
    def begin_step(self,n):self.step=n;self.ordinal=0;self.paid.begin_step(n)
    def generate(self,user_prompt,system_prompt=None,**kw):
        self.ordinal+=1;base=[dict(role='system',content=system_prompt),dict(role='user',content=user_prompt)]
        injected=self.step==self.meta['start']
        if injected and self.ordinal==1:assert base==self.meta['original_first_messages'],'Pre-injection input must equal saved Original.'
        actual=user_prompt+self.meta['suffix'] if injected else user_prompt
        record=dict(logical_id=f'{self.step:03d}:{self.ordinal:03d}',step=self.step,ordinal=self.ordinal,
            injected=injected,base_messages_hash=digest(base),actual_messages_hash=digest([base[0],dict(role='user',content=actual)]))
        key=record['logical_id']
        if key not in self.records:append_jsonl(self.audit,record);self.records[key]=record
        else:assert self.records[key]==record
        return self.paid.generate(actual,system_prompt,**kw)
