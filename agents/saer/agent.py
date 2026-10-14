import copy
from pathlib import Path
from functools import lru_cache
from agents.agc_v2.agent import AGCv2
from agents.agc.agent import DecisionUnavailable
from scar.agents.scar.repair import valid_syntax
from scar.io import atomic_json,digest
from .state import TaskState
from .reflection import augment,calibrate
from .syntax import diagnose,with_interface_feedback

class SAER(AGCv2):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.task_state=TaskState();self.saer_records=[];self.saer_calls=[]
        self.memory_paths=['memory.json','agc_v2.json','saer.json']
    def _act(self,obs):
        owner=self;original=self.llm;self.saer_records=[];self.saer_calls=[];self.decision={};previous_issue=None
        def call(phase,user,system):
            r=original.generate(user_prompt=user,system_prompt=system)
            owner.saer_calls.append(dict(phase=phase,prompt_hash=digest(user),system_hash=digest(system),response=r['response'],
                input_tokens=r['num_input_tokens'],output_tokens=r['num_output_tokens']))
            return r
        class Reflected:
            def generate(self,user_prompt,system_prompt=None,**kwargs):
                nonlocal previous_issue
                received_feedback=copy.deepcopy(previous_issue)
                user_prompt=with_interface_feedback(user_prompt,received_feedback)
                start=len(owner.saer_calls);goal=owner.control.goal.goal_description if owner.control.goal else ''
                preliminary=owner.task_state.summary(obs,goal)
                output=call('candidate',augment(user_prompt,preliminary),system_prompt);proposal=owner.cfg.json_parser(output['response'])
                syntax=isinstance(proposal,dict) and isinstance(proposal.get('action'),str) and valid_syntax(proposal['action'].strip(),owner.available_actions)
                native_goal_shape=isinstance(proposal,dict) and isinstance(proposal.get('goal_description'),str) and bool(proposal['goal_description'].strip())
                if not syntax or not native_goal_shape:
                    previous_issue=diagnose(proposal,owner.available_actions)
                    owner.saer_records.append(dict(candidate=proposal,skipped_reason='Native action/goal format invalid; passed unchanged to AGC-v2 repair.',risk_veto=False,
                        first_call=start+1,last_call=len(owner.saer_calls),base_prompt=user_prompt,
                        syntax_feedback_received=received_feedback,returned_format_issues=copy.deepcopy(previous_issue)))
                    return output
                summary=owner.task_state.summary(obs,goal,proposal)
                final,record=calibrate(proposal,user_prompt,system_prompt,summary,call)
                record.update(first_call=start+1,last_call=len(owner.saer_calls),base_prompt=user_prompt,
                    final_proposal=owner.cfg.json_parser(final['response']))
                previous_issue=diagnose(record['final_proposal'],owner.available_actions)
                record.update(syntax_feedback_received=received_feedback,returned_format_issues=copy.deepcopy(previous_issue))
                owner.saer_records.append(record);calls=owner.saer_calls[start:]
                return dict(final,num_input_tokens=sum(x['input_tokens'] for x in calls),num_output_tokens=sum(x['output_tokens'] for x in calls))
        self.llm=Reflected()
        try:return super()._act(obs)
        finally:
            self.llm=original
            self.decision.update(saer_records=copy.deepcopy(self.saer_records),saer_calls=copy.deepcopy(self.saer_calls),saer_risk_veto=False,saer_generated_action=False)
    def observe_transition(self,before,action,after):
        goal=self.control.goal.goal_description if self.control.goal else ''
        super().observe_transition(before,action,after)
        self.task_state.observe(before,action,after,goal,self.control.to_dict())
    def save_memory(self,directory):
        super().save_memory(directory);atomic_json(Path(directory)/'saer.json',dict(schema=1,state=self.task_state.to_dict()))
    def load_memory(self,directory):
        import json
        super().load_memory(directory);d=json.loads((Path(directory)/'saer.json').read_text());assert d['schema']==1
        self.task_state=TaskState.from_dict(d['state'])

@lru_cache(None)
def create_saer(base):return type('SAER__'+base.__module__+'.'+base.__name__,(SAER,base),{'__module__':base.__module__,'__agent__':base})
