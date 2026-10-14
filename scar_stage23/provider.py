"""Reuse exact conditional samples; bill only new divergent requests."""
import copy
import random
import numpy as np
from .common import *
from scar.io import digest,append_jsonl
from scar_stage22.provider import Provider as PaidProvider


class PairedProvider:
    def __init__(self,folder,pair_folder,key,variant):
        self.folder=Path(folder);self.pair_folder=Path(pair_folder);self.key=key;self.variant=variant
        self.paid=None;self.calls={};self.last=None
        self.original={r['step']:r for r in rows(SOURCE/'requests.jsonl.gz')}
        self.original_states={r['step']:r['state_hash_before'] for r in rows(SOURCE/'trajectory.jsonl.gz')}
        self.audit=self.folder/'requests.jsonl'
        if self.audit.exists():
            self.calls={r['step']:r for r in map(json.loads,self.audit.read_text().splitlines())}

    def begin_step(self,step,state_hash):self.step=step;self.state_hash=state_hash

    def generate(self,user_prompt,system_prompt=None,**kwargs):
        messages=[dict(role='system',content=system_prompt),dict(role='user',content=user_prompt)]
        sig=digest(messages);n=self.step
        if n in self.calls:
            row=self.calls[n]
            assert row['signature']==sig and row['state_hash_before']==self.state_hash
            self.last=row
            return PaidProvider.result(row)
        key=digest(dict(step=n,state_hash=self.state_hash,messages=messages))
        paired=self.pair_folder/'shared_requests'/f'{key}.json'
        original=self.original.get(n)
        if original and self.original_states[n]==self.state_hash and original['messages']==messages:
            raw=copy.deepcopy(original);origin='Stage22-original';charge=0
            source_ref=f'results/stage22/runs/mark__Stage18-Fixed/requests.jsonl.gz:{n}'
        elif paired.exists():
            cached=read(paired);raw=cached['request'];origin='paired-identical-state-and-input';charge=0
            source_ref=cached['source_ref']
            assert raw['messages']==messages
        else:
            # Transport/reuse must not advance native Python/NumPy RNG streams.
            py_state,np_state=random.getstate(),np.random.get_state()
            try:
                if self.paid is None:self.paid=PaidProvider(self.folder/'paid',RUNTIME,self.key)
                self.paid.begin_step(n)
                self.paid.generate(user_prompt=user_prompt,system_prompt=system_prompt,**kwargs)
            finally:
                random.setstate(py_state);np.random.set_state(np_state)
            raw=copy.deepcopy(self.paid.cache[f'{n:03d}:001']);origin='new-model-request';charge=raw['cost_usd']
            source_ref=f'results/stage23/runs/{self.folder.parent.name}/{self.variant}/requests.jsonl.gz:step={n}'
            write(paired,dict(request=raw,source_ref=source_ref))
        row=dict(raw,step=n,signature=sig,state_hash_before=self.state_hash,sample_origin=origin,
            source_ref=source_ref,incremental_cost_usd=charge,source_request_cost_usd=raw.get('cost_usd',0))
        append_jsonl(self.audit,row);self.calls[n]=row;self.last=row
        return PaidProvider.result(row)
