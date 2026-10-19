import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile
R=Path('/root/agentodyssey-benchmark-20261018');repo=R/'agentodyssey'
if sys.prefix!=str(R/'.venv'):
    os.execv(str(R/'.venv/bin/python'),[str(R/'.venv/bin/python'),str(R/'preflight_sentry_remote.py')])
assert not (R/'sentry_status.json').exists()
preserve=[repo/'eval.py',repo/'agents/long_context_agent.py',repo/'agents/feedback_control_agent.py',repo/'agents/feedback_control_core.py']
before={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in preserve}
root=R/'sentry_vendor';root.mkdir(exist_ok=True)
with zipfile.ZipFile(R/'sentry_core.zip') as z:
    for name in z.namelist():
        dest=(root/name).resolve();assert dest.is_relative_to(root.resolve())
        dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(name))
manifest=json.loads((R/'sentry_source_manifest.json').read_text())
for rel,digest in manifest['files'].items():assert hashlib.sha256((root/rel).read_bytes()).hexdigest()==digest
shutil.copy2(R/'sentry_agent.py',repo/'agents/sentry_agent.py')
env=os.environ.copy();env['PYTHONPATH']=str(root)+':'+str(repo)+':'+str(R)
result=subprocess.run([str(R/'.venv/bin/python'),str(R/'test_sentry_integration.py')],env=env,capture_output=True,text=True)
assert result.returncode==0,result.stdout+result.stderr
sys.path[:0]=[str(root),str(repo),str(R)]
from agents.sentry_agent import create_sentry_agent
from agents.llm_agent_config import LLMAgentConfig
from Sentry import SentryRunner
from Sentry.config import SentryConfig,ModelConfig
from test_sentry_integration import Judge,NO
from types import SimpleNamespace
class Base:
    def __init__(self,id,name):
        self.id=id;self.name=name;self.available_actions=[SimpleNamespace(verb='inspect',params=['object_name'])]
class Actor:
    def __init__(self):self.prompts=[]
    def generate(self,**kw):
        self.prompts.append(kw)
        return {'response':json.dumps({'reasoning':'Inspect what is visible.','action':'inspect token'}),
                'num_input_tokens':8,'num_output_tokens':5}
with tempfile.TemporaryDirectory(prefix='sentry-offline-') as temp:
    os.environ['AO_API_BASE_URL']='http://127.0.0.1:1/sentry_offline/v1'
    os.environ['AO_SENTRY_ARTIFACTS']=temp
    cfg=LLMAgentConfig(llm_name='deepseek-flash',llm_provider='openai')
    agent=create_sentry_agent(Base)('test','test',cfg)
    actor=Actor();agent.llm=actor
    agent.runner=SentryRunner(Judge([NO]),SentryConfig(model=ModelConfig(model='deepseek-flash')))
    observed='Current Location: facility, room\nI see token near me.'
    assert agent._act({'text':observed})[0]=='inspect token'
    assert not agent.runner.guard.window.steps
    agent.observe_outcome('The token is a small blue object.')
    assert agent.runner.guard.window.steps[0].observation=='The token is a small blue object.'
    agent._act({'text':'The token is a small blue object.'})
    assert observed in actor.prompts[-1]['user_prompt']
    agent.observe_outcome('The token is unchanged.',terminal=True)
    assert agent.runner.guard.task is None
    agent.save_memory(temp)
    assert (Path(temp)/'sentry_playbook_snapshot.json').exists()
source=(repo/'eval.py').read_text()
assert source.count('("agents.long_context_agent",                   "create_long_context_agent")')==1
assert source.count('        env.update_config(cumulative=args.cumulative_config_save)\n')==1
for name in ['sentry_agent.py','eval_sentry.py','run_sentry.py','api_proxy_sentry.py']:
    compile((R/name).read_text(),str(R/name),'exec')
after={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in preserve}
assert before==after
receipt={'upstream_commit':manifest['commit'],'all_official_source_hashes_match':True,
         'official_lifecycle_tests_passed':True,'adapter_integration_passed':True,
         'api_calls':0,'environment_rollouts':0,'existing_files_unchanged':before,
         'tests':result.stderr}
(R/'sentry_preflight.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
