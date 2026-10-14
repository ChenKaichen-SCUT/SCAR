"""Reuse only the intervention-step response; sample new changed contexts normally."""
from scar_stage24.provider import SharedProvider
from scar.io import append_jsonl,digest
from .common import *

class BranchProvider:
    def __init__(self,folder,start,key):
        self.folder=Path(folder);self.start=start;self.paid=SharedProvider(folder,RUNTIME,key)
        self.source={(q['step'],q['ordinal']):q for q in rows(SOURCE/'requests.jsonl.gz') if q['status']=='ok'}
        self.reuse_path=self.folder/'source_reuse.jsonl'
        self.reuses={r['logical_id']:r for r in map(json.loads,self.reuse_path.read_text().splitlines())} if self.reuse_path.exists() else {}
    def begin_step(self,n):self.step=n;self.ordinal=0;self.paid.begin_step(n)
    def generate(self,user_prompt,system_prompt=None,**kw):
        self.ordinal+=1
        if self.step!=self.start:return self.paid.generate(user_prompt,system_prompt,**kw)
        q=self.source[self.step,self.ordinal]
        messages=[dict(role='system',content=system_prompt),dict(role='user',content=user_prompt)]
        assert messages==q['messages'],'Oracle must start with unchanged model context.'
        logical=f'{self.step:03d}:{self.ordinal:03d}'
        row=dict(logical_id=logical,step=self.step,ordinal=self.ordinal,source_request_id=q['request_id'],signature=digest(messages),new_cost_usd=0)
        if logical not in self.reuses:append_jsonl(self.reuse_path,row);self.reuses[logical]=row
        else:assert self.reuses[logical]==row
        return self.paid.result(q)
