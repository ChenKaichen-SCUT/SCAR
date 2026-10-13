"""Shared audited DeepSeek client, including paid malformed calls and resume cache."""
import json
import time
from pathlib import Path
from scar.io import append_jsonl, digest
from .planning import parse_response, InterfaceError
from scar.providers.deepseek import (BudgetLedger, BudgetExceeded, ModelResponseError,
    concurrency_slot, estimate_cost, read_key)

CONFIG = dict(model='deepseek-flash', base_url='https://api.deepseek.com', temperature=0.7,
              thinking='disabled', max_tokens=768, plan_max_tokens=2048,
              pricing_usd_per_million=dict(cache_hit=0.006, cache_miss=0.3, output=1.2),
              total_budget_usd=200, episode_budget_usd=12, context_window=1000000,
              retries=3)


class UncertainRequest(RuntimeError): pass


class SharedDeepSeekProvider:
    def __init__(self, folder, ledger, key_path, config=None):
        from openai import OpenAI
        self.config = config or CONFIG
        self.folder=Path(folder); self.folder.mkdir(parents=True, exist_ok=True)
        self.audit=self.folder/'requests.jsonl';self.pending=self.folder/'pending_request.json'
        self.ledger=BudgetLedger(ledger,self.config['total_budget_usd'])
        self.episode=BudgetLedger(self.folder/'budget.sqlite',self.config['episode_budget_usd'])
        self.slots=Path(ledger).parent/'api_slots'
        self.client=OpenAI(api_key=read_key(key_path),base_url=self.config['base_url'],timeout=120,max_retries=0)
        self.step=0;self.ordinal=0;self.cache={};self.previous_attempts={}
        if self.audit.exists():
            for line in self.audit.read_text().splitlines():
                row=json.loads(line)
                self.previous_attempts.setdefault(row['logical_id'],[]).append(row)
                if row['status']=='ok':self.cache[row['logical_id']]=row
        if self.pending.exists():
            pending=json.loads(self.pending.read_text())
            rows=[json.loads(s) for s in self.audit.read_text().splitlines()] if self.audit.exists() else []
            if not any(r['request_id']==pending['request_id'] for r in rows):
                raise UncertainRequest('Interrupted API request has uncertain billing; preserve run, do not resample')
            self.pending.unlink()

    def begin_step(self, step): self.step=step;self.ordinal=0

    def generate(self, user_prompt, system_prompt=None, required=('action','reasoning'),
                 phase='action', max_tokens=None, validator=None):
        self.ordinal+=1
        logical=f'{self.step:03d}:{self.ordinal:03d}'
        messages=([dict(role='system',content=system_prompt)] if system_prompt else [])+[dict(role='user',content=user_prompt)]
        maximum=max_tokens or self.config['max_tokens']
        signature=digest(dict(messages=messages,phase=phase,max_tokens=maximum,required=required))
        if logical in self.cache:
            row=self.cache[logical]
            if signature!=row['signature']:raise RuntimeError('Resume changed a frozen request')
            return self.result(row)
        prices=self.config['pricing_usd_per_million']
        upper=((len(json.dumps(messages,ensure_ascii=False).encode())+1024)*prices['cache_miss']+maximum*prices['output'])/1e6
        prior=self.previous_attempts.get(logical,[])
        if any(r['signature']!=signature for r in prior):raise RuntimeError('Resume changed a failed request')
        first_attempt=max([r['attempt'] for r in prior]+[-1])+1
        for attempt in range(first_attempt,self.config['retries']):
            request_id=digest([str(self.folder),logical,attempt])
            self.ledger.reserve(request_id,upper)
            try:self.episode.reserve(request_id,upper)
            except BudgetExceeded:
                self.ledger.settle(request_id,0,'episode_budget_abort');raise
            row=dict(request_id=request_id,logical_id=logical,step=self.step,ordinal=self.ordinal,
                attempt=attempt,signature=signature,phase=phase,start=time.time(),messages=messages,
                model=self.config['model'],temperature=self.config['temperature'],thinking=self.config['thinking'],
                max_tokens=maximum,reserved_usd=upper)
            self.pending.write_text(json.dumps(dict(request_id=request_id,logical_id=logical)))
            charged=upper; status='unknown_billing'; fatal=False;result=None
            try:
                with concurrency_slot(self.slots,12):
                    response=self.client.chat.completions.create(model=self.config['model'],messages=messages,
                        temperature=self.config['temperature'],max_tokens=maximum,
                        response_format={'type':'json_object'},extra_body={'thinking':{'type':self.config['thinking']}})
                raw=response.model_dump();row['raw_response']=raw
                usage=raw.get('usage')
                if not usage or 'prompt_tokens' not in usage:raise ModelResponseError('Missing usage')
                row['usage']=usage;charged=estimate_cost(usage,prices)
                row['cost_usd']=charged
                parsed,normalization=parse_response(raw['choices'][0]['message']['content'])
                row['normalization_events']=normalization
                if not isinstance(parsed,dict) or not all(k in parsed for k in required):raise ModelResponseError('Missing JSON fields')
                if 'action' in required and (not isinstance(parsed['action'],str) or not parsed['action'].strip()):raise ModelResponseError('Invalid action')
                if validator:validator(parsed)
                row['parsed']=parsed;status='ok'
            except Exception as exc:
                code=getattr(exc,'status_code',None)
                row.update(error_type=type(exc).__name__,http_status=code,
                    interface_error_category=exc.category if isinstance(exc,InterfaceError) else 'transport_or_other',
                    interface_error_detail=str(exc) if isinstance(exc,InterfaceError) else None)
                if code is not None and 400<=code<500:charged=0;status='rejected'
                elif 'usage' in row:status='invalid_response'
                fatal=code in (400,401,402,403,404,422)
            finally:
                row.update(status=status,end=time.time(),charged_or_reserved_usd=charged)
                row['latency_seconds']=row['end']-row['start']
                self.ledger.settle(request_id,charged,status);self.episode.settle(request_id,charged,status)
                append_jsonl(self.audit,row);self.pending.unlink(missing_ok=True)
            if status=='ok':self.cache[logical]=row;return self.result(row)
            if status=='unknown_billing':raise UncertainRequest('Transport outcome has uncertain billing; no automatic resampling')
            if fatal:raise RuntimeError('API rejected HTTP '+str(row['http_status']))
            if attempt<2:time.sleep(2**attempt)
        raise ModelResponseError('Three audited API/parse attempts failed')

    @staticmethod
    def result(row):
        u=row['usage'];return dict(response=row['raw_response']['choices'][0]['message']['content'],
            num_input_tokens=u['prompt_tokens'],num_output_tokens=u['completion_tokens'],
            parsed=row['parsed'],usage=u,request_id=row['request_id'])
