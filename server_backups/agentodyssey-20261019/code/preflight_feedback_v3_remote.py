"""Required tests, real adapter with fake models, and protected file hashes."""
import hashlib,json,os,shutil,subprocess,sys,tempfile
from pathlib import Path
from types import SimpleNamespace
R=Path('/root/agentodyssey-benchmark-20261018');repo=R/'agentodyssey'
if sys.prefix!=str(R/'.venv'):os.execv(str(R/'.venv/bin/python'),[str(R/'.venv/bin/python'),str(R/'preflight_feedback_v3_remote.py')])
assert not (R/'feedback_v3_status.json').exists()
protected=[repo/'eval.py',repo/'agents/long_context_agent.py',repo/'agents/llm_agent_config.py',repo/'agents/feedback_control_agent.py',repo/'agents/feedback_control_core.py',repo/'agents/sentry_agent.py',repo/'agents/feedback_v2_core.py',repo/'agents/feedback_v2_agent.py']
before={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
for n in ['feedback_v3_core.py','feedback_v3_agent.py']:shutil.copy2(R/n,repo/'agents'/n)
test=subprocess.run([str(R/'.venv/bin/python'),str(R/'test_feedback_v3.py')],capture_output=True,text=True);assert test.returncode==0,test.stderr
for n in ['feedback_v3_core.py','feedback_v3_agent.py','eval_feedback_v3.py','run_feedback_v3.py','api_proxy_feedback_v3.py','analyze_feedback_v3.py']:compile((R/n).read_text(),str(R/n),'exec')
sys.path.insert(0,str(repo));sys.path.insert(0,str(R));os.environ['AO_API_BASE_URL']='http://127.0.0.1:1/offline_v3/v1'
from agents.feedback_v3_agent import create_feedback_v3_agent,NoAdmissibleAction
from agents.llm_agent_config import LLMAgentConfig
from agents.feedback_v2_core import uid
class FakeAgent:
    def __init__(self,id,name):
        self.id=id;self.name=name;self.available_actions=[SimpleNamespace(verb=v,params=p) for v,p in [('craft',['amount','obj_name']),('inspect',['object_name']),('pick up',['object_name']),('wait',[])]]
class FakeModel:
    def __init__(self,outputs):self.outputs=iter(outputs);self.calls=[]
    def generate(self,**kw):self.calls.append(kw);return {'response':json.dumps(next(self.outputs)),'num_input_tokens':10,'num_output_tokens':5}
with tempfile.TemporaryDirectory(prefix='feedback-v3-offline-') as temp:
    os.environ['AO_CONTROL_AUDIT']=str(Path(temp)/'audit.jsonl');gid=uid('guide|Craft a device.')
    agent=create_feedback_v3_agent(FakeAgent)('fake','fake',LLMAgentConfig(llm_name='deepseek-flash',llm_provider='openai'))
    raw={'reasoning':'assemble','action':'craft 1 device','goal_id':gid,'objective':{'action':'craft 1 device'},'candidates':[{'actions':['craft 1 device']}]}
    agent.llm=FakeModel([raw]);agent.controller_llm=FakeModel([{}])
    observation='Current Location: workshop\nguide says: Main goal: Build.\nCurrent tasks:\n[1] Craft a device.\nI am holding 1 ore.\nI have equipped no objects.\nI see 1 ore near me.\nIt can be used to craft: device (2 ore)\n'
    result=agent._act({'text':observation});assert result[0]=='pick up ore',result
    assert agent.ledger.repairs==0 and len(agent.llm.calls)==1
    assert 'Dispatcher feedback' in agent.memory.context and observation in agent.llm.calls[0]['user_prompt']
    assert 'exactly these keys' not in agent.llm.calls[0]['system_prompt']
    agent.observe_final(observation.replace('holding 1 ore','holding 2 ore')+'I picked up ore.\n');assert len(agent.ledger.history)==1
    agent.save_memory(temp);assert (Path(temp)/'feedback_v3_state.json').exists()
    # Closed candidate set must fail explicitly, never secretly execute repeated inspections.
    second=create_feedback_v3_agent(FakeAgent)('fake2','fake2',LLMAgentConfig(llm_name='deepseek-flash',llm_provider='openai'))
    second.ledger.inspections[('ore',0)]=0
    bad={'reasoning':'repeat','action':'inspect ore','goal_id':gid,'candidates':[{'actions':['inspect ore']}]}
    second.llm=FakeModel([bad,bad]);second.controller_llm=FakeModel([{}])
    try:second._act({'text':observation})
    except NoAdmissibleAction:pass
    else:raise AssertionError('Repeated inspection must not become a fallback action')
    assert len(second.llm.calls)==2 and not second.memory.context
after={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected};assert before==after
receipt={'offline_core_tests_passed':True,'offline_adapter_integration_passed':True,'required_frozen_trace_tests_included':True,'api_calls':0,'real_game_rollouts':0,'protected_files_unchanged':before,'tests':test.stderr}
(R/'feedback_v3_preflight.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
