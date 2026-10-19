"""Zero-provider integration test: public historical path, scripted proposer.

This tests path preservation, NOT autonomous performance. Fixture names never
enter production code/prompts. No hidden game configuration is inspected.
"""
import hashlib,json,os,re,runpy,socket,sys
from pathlib import Path
from unittest.mock import patch
R=Path('/root/agentodyssey-benchmark-20261018');repo=R/'agentodyssey'
sys.path.insert(0,str(repo));sys.path.insert(0,str(R))
from agents.feedback_v3r6_agent import Model,FeedbackV3R6Agent

segments=[['enter library'],['pick up key','enter library']]
pending=[list(x) for x in segments];state={'agent':None,'proposer_calls':0};executed=[]
folder=R/'offline_v3r6_public_path_checked';folder.mkdir(exist_ok=True)
cfg=folder/'agents.json';run=folder/'run';audit=folder/'audit.jsonl'
assert not run.exists() and not audit.exists(),'Offline fixture already exists; use results, not silent overwrite'
cfg.write_text(json.dumps({'agents':[{'agent_type':'LongContextAgent','agent_id':'agent_adam_davis','agent_name':'adam_davis','llm_name':'deepseek-flash','llm_provider':'openai'}]}))
original_init=FeedbackV3R6Agent.__init__;original_act=FeedbackV3R6Agent._act
def init(self,*args,**kwargs):original_init(self,*args,**kwargs);state['agent']=self
def fake_generate(self,*args,**kwargs):
    state['proposer_calls']+=1;s=state['agent'].ledger
    if kwargs.get('controller'):response={}
    else:
        if s.pending_contact:seq=['talk to '+s.pending_contact]
        else:seq=pending[0] if pending else ['wait']
        response={'action':seq[0],'reasoning':'Offline public-trace path preservation fixture, not autonomous inference.','candidates':[{'actions':seq}]}
    return {'response':json.dumps(response),'num_input_tokens':0,'num_output_tokens':0}
def act(self,obs):
    required=re.search(r'Required action:\s*`([^`]+)`',obs['text'])
    result=original_act(self,obs);a=result[0];source=json.loads(audit.read_text().splitlines()[-1])['dispatch']['source']
    executed.append({'step':self.ledger.step,'action':a,'source':source})
    if not required and not a.startswith('talk to '):
        if pending:
            assert a==pending[0][0],{'expected':pending[0][0],'executed':a,'step':self.ledger.step,'last_gate':self.ledger.control_checks[-4:]}
            pending[0].pop(0)
            if not pending[0]:pending.pop(0)
    return result
os.environ.update({'AO_API_BASE_URL':'http://127.0.0.1:8094/offline/v1','AO_CONTROL_AUDIT':str(audit),'AO_CALL_LIMIT':'502','AO_MAX_STEPS':'300','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'})
cmd=[str(R/'eval_feedback_v3r6.py'),'--agents_config',str(cfg),'--game_name','remnant','--max_steps','30','--seed','42','--run_dir',str(run),'--cumulative_config_save']
os.chdir(repo)
with patch.object(FeedbackV3R6Agent,'__init__',init),patch.object(FeedbackV3R6Agent,'_act',act),patch.object(Model,'generate',fake_generate),patch.object(socket.socket,'connect',side_effect=AssertionError('Unexpected network')),patch.object(sys,'argv',cmd):
    runpy.run_path(cmd[0],run_name='__main__')
rows=[json.loads(x) for x in (run/'agent_adam_davis/agent_log.jsonl').read_text().splitlines()]
gains=[i+1 for i,x in enumerate(rows) if x['reward'].get('quest',0)]
assert not pending,pending
assert sum(x['reward'].get('quest',0) for x in rows)==1,gains
assert any(x['action']=='enter library' and x['source']=='local_committed_continuation' for x in executed)
# Second point: exact observed public states from the old successful episode.
# The environment trajectory above is different; do not invent materials in it.
from agents.feedback_v3r6_core import Ledger
old=[json.loads(x) for x in (R/'runs/remnant__v3r2_verified_20261019/agent_adam_davis/agent_log.jsonl').read_text().splitlines()]
agent=state['agent'];ledger=Ledger();ledger.schemas=agent.schemas
for row in old[:82]:
    ledger.advance(row['observation']['text']);ledger.choose(row['action'],'public historical observation replay',ledger.focus)
agent.ledger=ledger;agent.audit_path=folder/'weapon_audit.jsonl';pending[:]=[['craft 1 wooden_dagger','pick up wooden_dagger']]
with patch.object(Model,'generate',fake_generate),patch.object(socket.socket,'connect',side_effect=AssertionError('Unexpected network')):
    for i in [82,83]:
        expected=old[i]['action'];result=original_act(agent,old[i]['observation'])
        assert result[0]==expected,(expected,result[0])
        assert any(t['status']=='open' and t['scope']=='main' and t['text'].startswith('Arm yourself') for t in ledger.tasks.values())
        pending[0].pop(0)
    agent.observe_final(old[83]['next_observation']['text'])
assert ledger.pending_contact=='bob_johnson'
assert ledger.hands.get('wooden_dagger',0)==1
weapon={'passed':True,'actions':['craft 1 wooden_dagger','pick up wooden_dagger'],'public_feedback_reward':old[83]['reward']['quest'],'interpretation':'Observed-state replay only; not a new environment score.'}
result={'passed':True,'provider_calls':0,'interpretation':'Scripted public-path regression, not autonomous method performance or baseline rerun.','real_environment_quest_gain_steps':gains,'weapon_observed_state_replay':weapon,'executed':executed,'source_sha256':{n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in ['feedback_v3r6_agent.py','feedback_v3r6_core.py','test_v3r6_public_path_remote.py']}}
(R/'feedback_v3r6_public_path_verification.json').write_text(json.dumps(result,indent=2));print('PUBLIC_PATH '+json.dumps(result))
