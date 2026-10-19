"""Install isolated new modules and test integration without any API calls."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
R=Path('/root/agentodyssey-benchmark-20261018'); repo=R/'agentodyssey'
if sys.prefix != str(R/'.venv'):
    os.execv(str(R/'.venv/bin/python'), [str(R/'.venv/bin/python'), str(R/'preflight_feedback_remote.py')])
assert json.loads((R/'remaining_status.json').read_text())['completed']
assert not (R/'feedback_status.json').exists()
baseline_paths=[repo/'eval.py',repo/'agents/long_context_agent.py',repo/'agents/llm_agent_config.py']
before={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in baseline_paths}
for name in ['feedback_control_core.py','feedback_control_agent.py']:
    shutil.copy2(R/name,repo/'agents'/name)
sys.path.insert(0,str(repo));sys.path.insert(0,str(R))
result=subprocess.run([str(R/'.venv/bin/python'),str(R/'test_feedback_control.py')],capture_output=True,text=True)
assert result.returncode==0,result.stderr

# The wrapper must change exactly one factory reference and no environment code.
source=(repo/'eval.py').read_text()
old='("agents.long_context_agent",                   "create_long_context_agent")'
assert source.count(old)==1
for name in ['feedback_control_core.py','feedback_control_agent.py','run_feedback.py','eval_feedback.py','api_proxy_feedback.py']:
    compile((R/name).read_text(),str(R/name),'exec')

os.environ['AO_API_BASE_URL']='http://127.0.0.1:1/offline_test/v1'
from agents.feedback_control_agent import create_feedback_control_agent
from agents.llm_agent_config import LLMAgentConfig
from types import SimpleNamespace
class FakeAgent:
    def __init__(self,id,name):
        self.id=id;self.name=name
        self.available_actions=[SimpleNamespace(verb='pick up',params=['object_name']),SimpleNamespace(verb='inspect',params=['object_name']),SimpleNamespace(verb='wait',params=[])]
class FakeModel:
    def __init__(self,outputs):self.outputs=iter(outputs);self.calls=[]
    def generate(self,**kw):
        self.calls.append(kw)
        return {'response':json.dumps(next(self.outputs)), 'num_input_tokens':10,'num_output_tokens':5}
with tempfile.TemporaryDirectory(prefix='feedback-offline-') as tmp:
    os.environ['AO_CONTROL_AUDIT']=str(Path(tmp)/'audit.jsonl')
    cfg=LLMAgentConfig(llm_name='deepseek-flash',llm_provider='openai')
    agent=create_feedback_control_agent(FakeAgent)('fake','fake',cfg)
    actor=FakeModel([{'reasoning':'take object','action':'pick up 2 token'},
                     {'reasoning':'correct argument count','action':'pick up token'},
                     {'reasoning':'inspect observed object','action':'inspect token'}])
    critic=FakeModel([{'diagnosis':'inspect an object after a failed action','rules':[],
        'evidence':[{'step':2,'quote':'Cannot pick up token, capacity exhausted.'}],
        'goal':'inspect the visible object','subgoal':'inspect token',
        'expected_change':'description of token','horizon_steps':6}])
    agent.llm=actor;agent.controller_llm=critic
    first='Current Location: place, room\nI am holding nothing.\nI see token near me.\n'
    got=agent._act({'text':first})
    assert got[0]=='pick up token' and len(actor.calls)==2
    assert 'pick up 2 token' not in agent.memory.context
    assert not agent.control.transitions
    second='Current Location: place, room\nCannot pick up token, capacity exhausted.\nI am holding nothing.\nI see token near me.\n'
    got=agent._act({'text':second})
    assert got[0]=='inspect token' and len(critic.calls)==1
    assert agent.control.transitions[0]['denials']
    assert first in actor.calls[-1]['user_prompt']
    agent.save_memory(tmp)
    assert (Path(tmp)/'content.txt').exists() and (Path(tmp)/'feedback_control.json').exists()
after={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in baseline_paths}
assert before==after
receipt={'offline_core_tests_passed':True,'offline_integration_passed':True,
         'api_calls':0,'environment_rollouts':0,'baseline_files_unchanged':before,
         'core_test_output':result.stderr}
(R/'feedback_preflight.json').write_text(json.dumps(receipt,indent=2))
print(json.dumps(receipt))
