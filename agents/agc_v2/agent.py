"""Single-model AGC-v2; confidence review plus bounded action validation."""
import copy
import json
from functools import lru_cache
from pathlib import Path
from agents.agc.agent import AGC,DecisionUnavailable
from agents.fixed_size.short_term_memory_agent import ShortTermMemoryAgent
from agents.agc.state import extract
from scar.agents.scar.repair import valid_syntax
from scar.io import atomic_json
from .control import Control,MAX_ACTION_RETRIES,INVALID_MESSAGE,GOAL_MESSAGE


class AGCv2(AGC):
    def __init__(self,id,name,cfg=None):
        super().__init__(id,name,cfg);self.control=Control();self.memory_paths=['memory.json','agc_v2.json']

    def _act(self,obs):
        before=copy.deepcopy(self.control.to_dict());state=extract(obs);step=int(obs['step'])+1
        attempts=[];tin=tout=0;accepted=None;feedback=None;reviewed=False;action_retries=0;response=''
        # At most three action repairs and one confidence reconsideration.
        for ordinal in range(MAX_ACTION_RETRIES+2):
            summary=self.control.summary(state)
            prompt=self.cfg.construct_user_prompt_long_context('\n'.join(self.short_term_memory[-5:]),obs['text'])
            prompt+='\n\nAGC public state summary:\n'+json.dumps(summary,ensure_ascii=False)
            if feedback:prompt+='\n\n'+feedback
            self.last_user_prompt=prompt;output=self.llm.generate(user_prompt=prompt,system_prompt=self.cfg.system_prompt)
            tin+=output['num_input_tokens'];tout+=output['num_output_tokens'];response=output['response']
            proposal=self.cfg.json_parser(response);action=proposal.get('action','') if isinstance(proposal,dict) else ''
            syntax=isinstance(action,str) and valid_syntax(action.strip(),self.available_actions)
            check=self.control.assess(proposal,obs,syntax,step)
            terminal=not check['hard'] and (not check['goal_review'] or reviewed)
            attempts.append(dict(ordinal=ordinal+1,proposal=proposal,response=response,summary=summary,executed=terminal,**check))
            if terminal:accepted=proposal;break
            if check['hard']:
                if action_retries==MAX_ACTION_RETRIES:break
                action_retries+=1;feedback=INVALID_MESSAGE
            else:reviewed=True;feedback=GOAL_MESSAGE
        self.decision=dict(control_before=before,attempts=attempts,reconsider_calls=len(attempts)-1,action_retry_calls=action_retries,
            confidence_review_calls=int(reviewed),controller_generated_action=False,executed_action=accepted['action'].strip() if accepted else None,
            bounded_soft_release=bool(accepted and attempts[-1]['goal_review']))
        if accepted is None:raise DecisionUnavailable('AGC-v2 exhausted bounded action retries')
        self.control.accept_goal(accepted,step,attempts[-1]['evidence_verified'])
        action=accepted['action'].strip();self.memorize(f"{obs['text']}\n\nReasoning: {accepted.get('reasoning','')}\nAction: {action}")
        return action,tin,tout,response

    def save_memory(self,directory):
        ShortTermMemoryAgent.save_memory(self,str(directory))
        atomic_json(Path(directory)/'agc_v2.json',dict(schema=2,control=self.control.to_dict(),system_prompt=self.cfg.system_prompt))

    def load_memory(self,directory):
        ShortTermMemoryAgent.load_memory(self,str(directory));saved=json.loads((Path(directory)/'agc_v2.json').read_text())
        assert saved['schema']==2 and saved['system_prompt']==self.cfg.system_prompt
        self.control=Control.from_dict(saved['control'])


@lru_cache(None)
def create_agc_v2(base):return type('AGCv2__'+base.__module__+'.'+base.__name__,(AGCv2,base),{'__module__':base.__module__,'__agent__':base})
