"""Original STM prompt style plus goal/progress/failure summary, one model."""
import copy
import json
from pathlib import Path
from functools import lru_cache
from agents.fixed_size.short_term_memory_agent import ShortTermMemoryAgent
from scar.agents.scar.repair import valid_syntax
from scar.io import atomic_json
from .control import Control,MAX_RECONSIDER
from .state import extract


class DecisionUnavailable(RuntimeError):pass


class AGC(ShortTermMemoryAgent):
    def __init__(self,id,name,cfg=None):
        super().__init__(id,name,cfg);self.control=Control();self.decision={};self.transition=None
        self.memory_paths=['memory.json','agc.json']
        # User-approved schema extension; preserve original action space/style.
        self.cfg.system_prompt=self.cfg.system_prompt.replace('"action": "<action>"',
            '"action": "<action>",\n  "goal_description": "<current subgoal>",\n  "goal_evidence": "<exact public observation quote>"')

    def initialize_official(self,obs):self.control.initialize(obs)

    def _act(self,obs):
        before=copy.deepcopy(self.control.to_dict());state=extract(obs);step=int(obs['step'])+1
        attempts=[];tin=tout=0;reconsider=None;accepted=None;last_response=''
        for ordinal in range(MAX_RECONSIDER+1):
            summary=self.control.summary(state,reconsider)
            prompt=self.cfg.construct_user_prompt_long_context('\n'.join(self.short_term_memory[-5:]),obs['text'])
            prompt+='\n\nAGC public state summary:\n'+json.dumps(summary,ensure_ascii=False)
            self.last_user_prompt=prompt
            output=self.llm.generate(user_prompt=prompt,system_prompt=self.cfg.system_prompt)
            tin+=output['num_input_tokens'];tout+=output['num_output_tokens'];last_response=output['response']
            proposal=self.cfg.json_parser(last_response)
            action=proposal.get('action','') if isinstance(proposal,dict) else ''
            syntax=isinstance(action,str) and valid_syntax(action.strip(),self.available_actions)
            decision,reasons,hard=self.control.assess(proposal,obs,syntax,step)
            # One reconsider for soft failure/stagnation. Never invent a fallback
            # action. An unresolved hard constraint terminates this agent run.
            terminal=decision=='EXECUTE' or ordinal==MAX_RECONSIDER and not hard
            attempts.append(dict(ordinal=ordinal+1,proposal=proposal,decision=decision,reasons=reasons,
                hard=hard,executed=terminal,summary=summary,response=last_response))
            if terminal:accepted=proposal;break
            reconsider=dict(reasons=reasons,previous_proposal=proposal,
                request='Reconsider using only available public evidence. Return a complete JSON decision. No replacement action is prescribed.')
        self.decision=dict(control_before=before,attempts=attempts,reconsider_calls=len(attempts)-1,
            controller_generated_action=False,executed_action=accepted['action'].strip() if accepted else None,
            bounded_soft_release=bool(accepted and attempts[-1]['decision']=='RECONSIDER'))
        if accepted is None:raise DecisionUnavailable('No valid model decision after bounded reconsideration')
        self.control.accept_goal(accepted,step)
        action=accepted['action'].strip()
        self.memorize(f"{obs['text']}\n\nReasoning: {accepted.get('reasoning','')}\nAction: {action}")
        return action,tin,tout,last_response

    def observe_transition(self,before,action,after):
        self.transition=self.control.progress(before,action,after,int(after['step']))

    def save_memory(self,directory):
        super().save_memory(str(directory))
        atomic_json(Path(directory)/'agc.json',dict(schema=1,control=self.control.to_dict(),system_prompt=self.cfg.system_prompt))

    def load_memory(self,directory):
        super().load_memory(str(directory));saved=json.loads((Path(directory)/'agc.json').read_text())
        assert saved['schema']==1 and saved['system_prompt']==self.cfg.system_prompt
        self.control=Control.from_dict(saved['control'])


@lru_cache(None)
def create_agc(base):return type('AGC__'+base.__module__+'.'+base.__name__,(AGC,base),{'__module__':base.__module__,'__agent__':base})
