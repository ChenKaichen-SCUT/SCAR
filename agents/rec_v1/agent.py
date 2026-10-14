"""AGC-v2 plus bounded ALLOW/RECONSIDER; no replacement action or goal."""
import copy
import json
from pathlib import Path
from functools import lru_cache
from agents.agc_v2.agent import AGCv2
from agents.agc.agent import DecisionUnavailable
from scar.agents.scar.repair import valid_syntax
from scar.io import atomic_json,digest
from .state import Tracker

MAX_REC_RECONSIDER=2

class REC(AGCv2):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.rec=Tracker();self.rec_records=[]
        self.memory_paths=['memory.json','agc_v2.json','rec_v1.json']

    def initialize_official(self,obs):
        super().initialize_official(obs);self.rec.ingest(obs)

    def _act(self,obs):
        self.rec.ingest(obs);owner=self;original=self.llm;self.rec_records=[];retries=0;self.decision={}
        class Checked:
            def generate(self,user_prompt,system_prompt=None,**kwargs):
                nonlocal retries
                current=owner.control.goal.goal_description if owner.control.goal else ''
                summary=owner.rec.summary(current)
                prompt=user_prompt+'\n\nREC public execution state:\n'+json.dumps(summary,ensure_ascii=False)
                tin=tout=0
                while True:
                    result=original.generate(user_prompt=prompt,system_prompt=system_prompt,**kwargs)
                    tin+=result['num_input_tokens'];tout+=result['num_output_tokens']
                    proposal=owner.cfg.json_parser(result['response'])
                    syntax=isinstance(proposal,dict) and isinstance(proposal.get('action'),str) and valid_syntax(proposal['action'].strip(),owner.available_actions)
                    check=owner.rec.assess(proposal) if syntax else dict(decision='ALLOW',reasons=[],requirements=None)
                    owner.rec_records.append(dict(proposal=proposal,response=result['response'],check=check,
                        prompt_hash=digest(prompt),base_prompt_hash=digest(user_prompt),summary=summary,
                        passed_to_agc=check['decision']=='ALLOW'))
                    if check['decision']=='ALLOW':return dict(result,num_input_tokens=tin,num_output_tokens=tout)
                    if retries>=MAX_REC_RECONSIDER:raise DecisionUnavailable('REC exhausted two reconsiderations; no fallback action generated')
                    retries+=1
                    prompt=user_prompt+'\n\nREC public execution state:\n'+json.dumps(summary,ensure_ascii=False)
                    prompt+='\n\nREC RECONSIDER:\n'+json.dumps(dict(previous_proposal=proposal,evidence=check['reasons'],
                        request='Reconsider action consistency using this public evidence. Return the original complete JSON format. No replacement action or goal is prescribed.'),ensure_ascii=False)
        self.llm=Checked()
        try:
            result=super()._act(obs)
            self.decision.update(rec_records=copy.deepcopy(self.rec_records),rec_reconsider_calls=retries,rec_generated_action=False)
            return result
        except DecisionUnavailable:
            self.decision.update(rec_records=copy.deepcopy(self.rec_records),rec_reconsider_calls=retries,rec_generated_action=False,
                executed_action=None,rec_terminal_exhausted=bool(self.rec_records and self.rec_records[-1]['check']['decision']=='RECONSIDER'))
            raise
        finally:self.llm=original

    def observe_transition(self,before,action,after):
        goal=self.control.goal.goal_description if self.control.goal else ''
        super().observe_transition(before,action,after)
        self.rec.observe(before,action,after,goal)

    def save_memory(self,directory):
        super().save_memory(directory);atomic_json(Path(directory)/'rec_v1.json',dict(schema=1,state=self.rec.to_dict()))

    def load_memory(self,directory):
        super().load_memory(directory);saved=json.loads((Path(directory)/'rec_v1.json').read_text());assert saved['schema']==1
        self.rec=Tracker.from_dict(saved['state'])

@lru_cache(None)
def create_rec(base):return type('REC__'+base.__module__+'.'+base.__name__,(REC,base),{'__module__':base.__module__,'__agent__':base})
