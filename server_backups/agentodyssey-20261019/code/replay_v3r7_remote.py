"""Exact frozen v3r6 replay, one-step candidate checks, zero provider calls."""
import copy,hashlib,json,os,socket,sys
from pathlib import Path
from unittest.mock import patch
R=Path('/root/agentodyssey-benchmark-20261018');repo=R/'agentodyssey'
if sys.prefix!=str(R/'.venv'):os.execv(str(R/'.venv/bin/python'),[str(R/'.venv/bin/python'),str(R/'replay_v3r7_remote.py')])
sys.path.insert(0,str(repo));sys.path.insert(0,str(R));os.chdir(repo)
from agents.feedback_v3r6_agent import FeedbackV3R6Agent,Model,create_feedback_v3r6_agent
from agents.feedback_v3r7_core import Ledger as Candidate
from agents.llm_agent_config import LLMAgentConfig
from games.generated.remnant.agent import Agent
rid='remnant__v3r6_300_20261019';log=R/'runs'/rid/'agent_adam_davis/agent_log.jsonl';ap=R/'control_audit'/f'{rid}.jsonl'
trace=[json.loads(x) for x in log.read_text().splitlines()];audit=[json.loads(x) for x in ap.read_text().splitlines()]
ds={x['step']:x for x in audit if x['event']=='decision'};cs={x['step']:x for x in audit if x['event']=='controller'}
protected=[log,ap,R/'feedback_v3r6_300_budget.sqlite'];hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
captured={};calls=[];cases=[]
os.environ.update(AO_API_BASE_URL='http://127.0.0.1:8094/offline/v1',AO_CONTROL_AUDIT='/tmp/v3r7-unused-audit',AO_CALL_LIMIT='502',AO_MAX_STEPS='300')
def emit(self,e):
    if e['event']=='decision':captured[e['step']]=e
def generate(self,*args,controller=False,**kw):
    step=agent.ledger.step;event=(cs if controller else ds)[step];assert event['response'] is not None
    assert (step,controller) not in calls;calls.append((step,controller))
    return {'response':event['response'],'num_input_tokens':0,'num_output_tokens':0}
def shadow(s):
    c=copy.deepcopy(s);c.__class__=Candidate;c.init_repair_fields();return c

original_choose=None
with patch.object(socket.socket,'connect',side_effect=AssertionError('No network')),patch.object(LLMAgentConfig,'get_llm',return_value=None),patch.object(FeedbackV3R6Agent,'emit',emit),patch.object(Model,'generate',generate):
    agent=create_feedback_v3r6_agent(Agent)('agent_adam_davis','adam_davis',LLMAgentConfig(llm_name='deepseek-flash',llm_provider='openai'))
    for step,row in enumerate(trace,1):
        action,_,_,_=agent._act(row['observation']);actual=captured[step];expected=ds[step]
        assert action==row['action']==expected['action'],('divergence',step)
        for key in ['model_calls','local_steps','fallbacks','reviews']:assert actual[key]==expected[key],(step,key)
        assert actual['dispatch']['source']==expected['dispatch']['source']
        if step in [153,157,158,159,160,161,162,163,248,250,252,255,256,258,259]:
            s=shadow(agent.ledger);raw=agent.parse(expected['response']) if expected['response'] else {};candidates=agent.candidates(raw)
            seq=candidates[0]['actions'] if candidates else [action]
            v=s.validate_plan(seq);check,_=s.gate(seq,s.focus,'offline_same_state')
            repair=None
            if v['stop'] and v['stop']['status']=='contradicted':repair=s.repair_plan(seq,v)
            decision=s.dispatch(candidates,s.focus) if candidates else s._select_plan([action],s.focus,'local_committed_continuation')
            cases.append({'step':step,'historical_action':action,'original_sequence':seq,'new_validation':v,'new_first_action_blockers':check['blockers'],
              'new_action':decision[0] if decision else None,'new_dispatch':decision[2] if decision else None,'repair':repair})
            if step==256:
                assert v['stop']['reason']=='capacity_conflict';assert decision is None or decision[0]!='pick up iron_bar'
                assert repair is None or repair[0] is None,'A transfer repair must not discard another active input'
            if step==153:
                assert repair and repair[0],repair
                st=s._resource_state()
                for a in repair[0]:
                    if a.startswith('craft '):break
                    st,why,_=s.conditional_transition(st,a,remembered_only=True);assert st is not None,(a,why)
                assert s._available(st).get('thread',0)>=1,'Intermediate repair lost downstream thread'
            if 157<=step<=163:assert decision and decision[0]==action,('successful path changed',step,action,decision)
    assert len(calls)==173
assert hashes=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
result={'passed':True,'provider_calls':0,'reconstructed_steps':300,'identical_old_actions':True,'recorded_responses_reused':len(calls),
 'capacity_case_256_rejected':True,'successful_path_157_163_preserved':True,'cases':cases,
 'meaning':'Independent one-step interventions at reconstructed old states; no changed action receives historical future feedback; not a rollout score.',
 'protected_unchanged':True,'candidate_sha256':hashlib.sha256((repo/'agents/feedback_v3r7_core.py').read_bytes()).hexdigest()}
(R/'feedback_v3r7_historical_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in result.items() if k!='cases'},ensure_ascii=False))
