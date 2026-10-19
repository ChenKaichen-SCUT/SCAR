"""Unmodified upstream Sentry core integrated with full-history AgentOdyssey.
Only text observations, declared schema and execution-validity flags are exposed.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import shlex
from functools import lru_cache
from openai import OpenAI
from agents.long_context_agent import LongContextAgent
from Sentry import SentryRunner, agent_step_from_parts
from Sentry.config import SentryConfig, ModelConfig, PlaybookConfig, LoggingConfig

def declared_schema_error(action, schemas):
    action=action.strip()
    for verb,params in sorted(schemas,key=lambda x:-len(x[0])):
        if action==verb or action.startswith(verb+' '):
            try:values=shlex.split(action[len(verb):].strip())
            except ValueError:return 'Unbalanced quotation marks.'
            free=any(p.lower() in {'text','message','content','query'} for p in params)
            if (free and len(values)>=len(params)) or (not free and len(values)==len(params)):
                return None
            return 'Required format: '+verb+' '+' '.join('<'+p+'>' for p in params)
    return 'Unknown verb under the declared action schema.'

class SentryDeepSeekClient:
    model='deepseek-flash'
    def __init__(self, base_url, audit):
        self.client=OpenAI(base_url=base_url,api_key='local-proxy',timeout=300,max_retries=2)
        self.audit=Path(audit);self.audit.parent.mkdir(parents=True,exist_ok=True)
        self.calls=0
    def __call__(self,prompt,*,temperature,max_tokens,response_format=None):
        params={'model':self.model,'messages':[{'role':'user','content':prompt}],
                'temperature':temperature,'max_tokens':max_tokens,'presence_penalty':0.0}
        if response_format is not None:params['response_format']=response_format
        response=self.client.chat.completions.create(**params)
        self.calls+=1
        stage=prompt.splitlines()[0]
        with self.audit.open('a',encoding='utf-8') as f:
            f.write(json.dumps({'call_index':self.calls,'component':stage,
                'response':response.choices[0].message.content,
                'finish_reason':response.choices[0].finish_reason,
                'usage':response.usage.model_dump()},ensure_ascii=False)+'\n')
        return response

class SentryAgent(LongContextAgent):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.schemas=[(a.verb,list(a.params)) for a in self.available_actions]
        self.schema_text='\n'.join(v+' '+' '.join('<'+p+'>' for p in ps) for v,ps in self.schemas)
        root=Path(os.environ['AO_SENTRY_ARTIFACTS']);root.mkdir(parents=True,exist_ok=True)
        self.root=root;self.cycle=0;self.pending=None;self.guidance=None;self.started=False
        base=os.environ['AO_API_BASE_URL'];assert base.endswith('/v1')
        model=SentryDeepSeekClient(base[:-3]+'__sentry/v1',root/'model_calls.jsonl')
        config=SentryConfig(model=ModelConfig(model=self.cfg.llm_name),
            playbook=PlaybookConfig(persist_path=str(root/'playbook.json')),
            logging=LoggingConfig(enabled=True,log_path=str(root/'runtime_events.jsonl')))
        self.runner=SentryRunner(model=model,config=config)

    def _act(self,obs):
        text=obs['text']
        if not self.started:
            self.runner.start_task(objective='Complete the main quest revealed by the environment. Use only observed task instructions. Initial observation:\n'+text,
                                   action_schema=self.schema_text)
            self.started=True
            assert not self.runner.guard.playbook.entries
        prompt=self.construct_user_prompt_long_context(self.memory.get_all_memory(),text)
        guidance=self.guidance
        if guidance is not None:
            prompt+='\n\n'+guidance.prompt_text
        self.guidance=None
        result=self.llm.generate(user_prompt=prompt,system_prompt=self.cfg.system_prompt)
        parsed=self.cfg.response_parser(result['response'])
        raw_json=self.cfg.json_parser(result['response'])
        parsed_ok=isinstance(raw_json,dict) and isinstance(raw_json.get('action'),str) and isinstance(raw_json.get('reasoning'),str)
        error=declared_schema_error(parsed['action'],self.schemas)
        self.pending={'reasoning':parsed['reasoning'],'action':parsed['action'],
            'parsed_ok':parsed_ok,'schema_valid':error is None,'schema_error':error,
            'parser_error':None if parsed_ok else 'Response did not match the required reasoning/action JSON schema.'}
        self.memorize(text+'\n'+self.cfg.format_response(parsed))
        with (self.root/'decisions.jsonl').open('a',encoding='utf-8') as f:
            f.write(json.dumps({'cycle':self.cycle,'action':parsed['action'],'response':result['response'],
                'guidance_route':guidance.route if guidance else None,
                'guidance':guidance.prompt_text if guidance else None},ensure_ascii=False)+'\n')
        return parsed['action'],result['num_input_tokens'],result['num_output_tokens'],result['response']

    def observe_outcome(self,observation,*,invalid_action=False,terminal=False):
        assert self.pending is not None
        p=self.pending;self.pending=None
        # Semantic rejection is NOT evidence of a malformed action schema.
        rejection=any(line.strip().lower().startswith(('cannot ',"can't ",'invalid ','failed ','not enough '))
                      for line in observation.splitlines())
        step=agent_step_from_parts(step_id=self.cycle,reasoning=p['reasoning'],raw_action=p['action'],
            observation=observation,parsed_ok=p['parsed_ok'],schema_valid=p['schema_valid'],
            parser_error=p['parser_error'],schema_error=p['schema_error'],
            accepted_by_environment=not (invalid_action or rejection))
        self.guidance=self.runner.step(step,terminal=terminal)
        self.cycle+=1
        if terminal:self.runner.finalize()

    def save_memory(self,full_memory_dir):
        super().save_memory(full_memory_dir)
        path=Path(full_memory_dir)/'sentry_playbook_snapshot.json'
        path.write_text(json.dumps([e.to_json() for e in self.runner.guard.playbook.entries],ensure_ascii=False),encoding='utf-8')

@lru_cache(maxsize=None)
def create_sentry_agent(Agent):
    return type('SentryAgent__'+Agent.__module__+'.'+Agent.__name__,(SentryAgent,Agent),
                {'__module__':Agent.__module__,'__agent__':Agent})
