"""Run in a fresh process for each adapter variant; network is replaced by fake models."""
import json,os,tempfile
from pathlib import Path
from types import SimpleNamespace
from agents.mechanism_study_agent import create_mechanism_study_agent,DISABLED,VARIANT
from agents.llm_agent_config import LLMAgentConfig
from agents.feedback_v2_core import uid
class FakeAgent:
    def __init__(self,id,name):
        self.id=id;self.name=name;self.available_actions=[SimpleNamespace(verb=v,params=p) for v,p in [('craft',['amount','obj_name']),('inspect',['object_name']),('pick up',['object_name']),('wait',[])]]
class FakeModel:
    def __init__(self,outputs):self.outputs=iter(outputs);self.calls=[]
    def generate(self,**kw):self.calls.append(kw);return {'response':json.dumps(next(self.outputs)),'num_input_tokens':10,'num_output_tokens':5}
with tempfile.TemporaryDirectory(prefix='study-offline-') as tmp:
    os.environ['AO_CONTROL_AUDIT']=str(Path(tmp)/'audit.jsonl');gid=uid('guide|Craft a device.')
    agent=create_mechanism_study_agent(FakeAgent)('fake','fake',LLMAgentConfig(llm_name='deepseek-flash',llm_provider='openai'))
    raw={'reasoning':'assemble','action':'craft 1 device','goal_id':gid,'objective':{'action':'craft 1 device'},'candidates':[{'actions':['craft 1 device']},{'actions':['pick up ore']}]}
    agent.llm=FakeModel([raw]);agent.controller_llm=FakeModel([{}])
    observation='Current Location: workshop\nguide says: Main goal: Build.\nCurrent tasks:\n[1] Craft a device.\nI am holding 1 ore.\nI have equipped no objects.\nI see 1 ore near me.\nIt can be used to craft: device (2 ore)\n'
    result=agent._act({'text':observation});assert result[0] in ['pick up ore','craft 1 device'],result
    assert agent.ledger.repairs==0 and len(agent.llm.calls)==1
    assert 'Dispatcher feedback' in agent.memory.context
    if 'hypothesis' in DISABLED:
        assert '"hypotheses":' not in agent.llm.calls[0]['user_prompt']
        assert 'Optional hypotheses' not in agent.controller_llm.calls[0]['system_prompt']
    agent.observe_final(observation.replace('holding 1 ore','holding 2 ore')+'I picked up ore.\n')
    agent.save_memory(tmp);assert (Path(tmp)/'feedback_v3_state.json').exists()
print(json.dumps({'variant':VARIANT,'disabled':sorted(DISABLED),'adapter_passed':True,'real_api_calls':0}))
