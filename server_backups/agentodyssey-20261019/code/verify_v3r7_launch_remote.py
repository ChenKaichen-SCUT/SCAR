"""Test the actual runner's constructed command and actual instantiated policy, offline."""
import ast,hashlib,json,os,runpy,socket,sys,tempfile
from pathlib import Path
from unittest.mock import patch
R=Path('/root/agentodyssey-benchmark-20261018');repo=R/'agentodyssey'
if sys.prefix!=str(R/'.venv'):os.execv(str(R/'.venv/bin/python'),[str(R/'.venv/bin/python'),str(R/'verify_v3r7_launch_remote.py')])
sys.path.insert(0,str(repo));sys.path.insert(0,str(R))

def command_for(runner,cfg,folder):
    tree=ast.parse((R/runner).read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run_one')
    node=next(n for n in ast.walk(fn) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='cmd' for t in n.targets))
    return eval(compile(ast.Expression(node.value),str(R/runner),'eval'),{'R':R,'str':str,'cfg':cfg,'folder':folder,'g':'remnant'})

from agents.feedback_v3r7_agent import Model,FeedbackV3R7Agent
seen=[];original=FeedbackV3R7Agent._act
def observe_policy(self,obs):
    seen.append({'agent_module':original.__module__,'ledger_module':type(self.ledger).__module__,'dispatch_module':self.ledger.dispatch.__func__.__module__})
    return original(self,obs)
def fake_generate(self,*args,**kw):return {'response':json.dumps({'action':'wait','reasoning':'offline launch contract'}),'num_input_tokens':0,'num_output_tokens':0}
with tempfile.TemporaryDirectory(prefix='v3r7-launch-contract-') as tmp:
    tmp=Path(tmp);cfg=tmp/'agents.json';folder=tmp/'run'
    cfg.write_text(json.dumps({'agents':[{'agent_type':'LongContextAgent','agent_id':'agent_adam_davis','agent_name':'adam_davis','llm_name':'deepseek-flash','llm_provider':'openai'}]}))
    bad=command_for('run_feedback_v3r2.py',cfg,folder)
    assert Path(bad[2]).name=='eval_feedback_v3r.py' # Frozen historical negative control.
    good=command_for('run_feedback_v3r7.py',cfg,folder)
    assert Path(good[2]).name=='eval_feedback_v3r7.py' and good[good.index('--max_steps')+1]=='300'
    cmd=list(good);cmd[cmd.index('--max_steps')+1]='2'
    os.environ.update({'AO_API_BASE_URL':'http://127.0.0.1:8094/offline/v1','AO_CONTROL_AUDIT':str(tmp/'audit.jsonl'),'AO_CALL_LIMIT':'502','PYTHONHASHSEED':'42','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'})
    os.chdir(repo)
    with patch.object(Model,'generate',fake_generate),patch.object(FeedbackV3R7Agent,'_act',observe_policy),patch.object(socket.socket,'connect',side_effect=AssertionError('Unexpected network')),patch.object(sys,'argv',cmd[2:]):
        runpy.run_path(cmd[2],run_name='__main__')
    policy=[json.loads(x) for x in (tmp/'audit.jsonl').read_text().splitlines() if json.loads(x).get('event')=='policy_loaded']
    assert len(policy)==1 and policy[0]['max_steps']==300
    assert len(seen)==2,seen
    assert all(x['ledger_module']=='agents.feedback_v3r7_core' and x['dispatch_module']=='agents.feedback_v3r7_core' for x in seen),seen
    assert len((folder/'agent_adam_davis/agent_log.jsonl').read_text().splitlines())==2
    saved=list(folder.rglob('feedback_v3r7_state.json'));assert len(saved)==1,saved
result={'passed':True,'original_runner_negative_control_detected':True,'actual_runner_evaluator':Path(good[2]).name,'production_max_steps':300,'offline_steps':2,'instantiated_policy_checks':seen,'saved_v3r7_state':True,'runtime_policy_load_audit':policy,'provider_calls':0,'paid_run_started':False,
 'source_sha256':{n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in ['run_feedback_v3r7.py','eval_feedback_v3r7.py','agentodyssey/agents/feedback_v3r7_agent.py','agentodyssey/agents/feedback_v3r7_core.py']}}
(R/'feedback_v3r7_launch_verification.json').write_text(json.dumps(result,indent=2));print('LAUNCH_VERIFICATION '+json.dumps(result))
