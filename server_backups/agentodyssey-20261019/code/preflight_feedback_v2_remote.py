"""Install isolated v2 modules and exercise the real adapter using fake models."""
import hashlib,json,os,shutil,subprocess,sys,tempfile
from pathlib import Path
from types import SimpleNamespace
R=Path('/root/agentodyssey-benchmark-20261018');repo=R/'agentodyssey'
if sys.prefix!=str(R/'.venv'):os.execv(str(R/'.venv/bin/python'),[str(R/'.venv/bin/python'),str(R/'preflight_feedback_v2_remote.py')])
assert not (R/'feedback_v2_status.json').exists()
protected=[repo/'eval.py',repo/'agents/long_context_agent.py',repo/'agents/llm_agent_config.py',repo/'agents/feedback_control_agent.py',repo/'agents/feedback_control_core.py',repo/'agents/sentry_agent.py']
before={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
for name in ['feedback_v2_core.py','feedback_v2_agent.py']:shutil.copy2(R/name,repo/'agents'/name)
test=subprocess.run([str(R/'.venv/bin/python'),str(R/'test_feedback_v2.py')],capture_output=True,text=True)
assert test.returncode==0,test.stderr
for name in ['feedback_v2_core.py','feedback_v2_agent.py','eval_feedback_v2.py','run_feedback_v2.py','api_proxy_feedback_v2.py','analyze_feedback_v2.py']:
    compile((R/name).read_text(),str(R/name),'exec')
sys.path.insert(0,str(repo));sys.path.insert(0,str(R))
os.environ['AO_API_BASE_URL']='http://127.0.0.1:1/offline_v2/v1'
from agents.feedback_v2_agent import create_feedback_v2_agent
from agents.llm_agent_config import LLMAgentConfig
class FakeAgent:
    def __init__(self,id,name):
        self.id=id;self.name=name;self.available_actions=[SimpleNamespace(verb='craft',params=['amount','obj_name']),SimpleNamespace(verb='inspect',params=['object_name']),SimpleNamespace(verb='wait',params=[])]
class FakeModel:
    def __init__(self,outputs):self.outputs=iter(outputs);self.calls=[]
    def generate(self,**kw):
        self.calls.append(kw);return {'response':json.dumps(next(self.outputs)),'num_input_tokens':10,'num_output_tokens':5}
with tempfile.TemporaryDirectory(prefix='feedback-v2-offline-') as temp:
    os.environ['AO_CONTROL_AUDIT']=str(Path(temp)/'audit.jsonl')
    agent=create_feedback_v2_agent(FakeAgent)('fake','fake',LLMAgentConfig(llm_name='deepseek-flash',llm_provider='openai'))
    agent.llm=FakeModel([{'reasoning':'try','action':'craft 1 device'},{'reasoning':'quantity absent; inspect','action':'inspect ore'}])
    agent.controller_llm=FakeModel([{'diagnosis':'quantity deficit','plans':[],'hypotheses':[]}])
    observation='Current Location: workshop\nguide says: Main goal: Build.\nCurrent tasks:\n[1] Craft a device.\nI am holding 1 ore.\nI have equipped no objects.\nI see 1 ore near me.\nIt can be used to craft: device (2 ore)\n'
    result=agent._act({'text':observation});assert result[0]=='inspect ore'
    assert agent.ledger.repairs==1 and len(agent.llm.calls)==2
    assert agent.memory.context.strip().endswith(agent.cfg.format_response({'reasoning':'quantity absent; inspect','action':'inspect ore'}).strip())
    assert observation in agent.llm.calls[1]['user_prompt']
    agent.observe_final(observation+'I inspected ore.\n');assert len(agent.ledger.history)==1
    agent.save_memory(temp);assert (Path(temp)/'feedback_v2_state.json').exists()
    # Persistent contradiction after one repair must not reach the environment.
    second=create_feedback_v2_agent(FakeAgent)('fake2','fake2',LLMAgentConfig(llm_name='deepseek-flash',llm_provider='openai'))
    second.llm=FakeModel([{'reasoning':'try','action':'craft 1 device'},{'reasoning':'still try','action':'craft 1 device'}])
    second.controller_llm=FakeModel([{}])
    assert second._act({'text':observation})[0]=='inspect ore'
after={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected};assert before==after
receipt={'offline_core_tests_passed':True,'offline_adapter_integration_passed':True,'api_calls':0,'environment_rollouts':0,'protected_files_unchanged':before,'tests':test.stderr}
(R/'feedback_v2_preflight.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
