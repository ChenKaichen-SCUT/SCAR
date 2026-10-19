"""Offline, paired intervention on the exact frozen controller state.

Historical responses replace Model.generate. No environment is stepped, and no
counterfactual action is paired with a historical future observation.
"""
import copy,hashlib,json,os,socket,sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch
R=Path('/root/agentodyssey-benchmark-20261018');repo=R/'agentodyssey';sys.path.insert(0,str(repo));os.chdir(repo)
out=R/'results_feedback_v3r5_hypothesis';out.mkdir(exist_ok=True)
rid='remnant__v3r4_300_20261019'
logpath=R/'runs'/rid/'agent_adam_davis/agent_log.jsonl';auditpath=R/'control_audit'/f'{rid}.jsonl'
protected=[logpath,auditpath,*R.glob('*budget*.sqlite'),*R.glob('*budget*.sqlite-wal'),*repo.glob('agents/feedback_v*.py')]
protected=[p for p in protected if p.name!='feedback_v3r5_core.py']
def hashes():return {str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
before_hashes=hashes()
rows=[json.loads(x) for x in logpath.read_text().splitlines()]
events=[json.loads(x) for x in auditpath.read_text().splitlines()]
decisions={x['step']:x for x in events if x['event']=='decision'}
controllers={x['step']:x for x in events if x['event']=='controller'}
target={(d['step'],r['action']) for d in decisions.values() for r in d['dispatch'].get('rejected',[]) if r['action'].startswith(('attack ','eat ')) and any(b['kind']=='same_failed_action_context' and b['detail'].get('reason')==['no net contract progress on return to relevant state'] for b in r['blockers'])}
os.environ.update(AO_API_BASE_URL='http://127.0.0.1:8094/offline/v1',AO_CONTROL_AUDIT=str(out/'unused_audit.jsonl'),AO_CALL_LIMIT='502',AO_MAX_STEPS='300')
from agents.feedback_v3r4_agent import FeedbackV3R4Agent,Model,create_feedback_v3r4_agent
from agents.feedback_v3r4_core import Ledger as Baseline
from agents.feedback_v3r5_core import Ledger as Candidate,NO_RESOURCE_PROGRESS
from agents.llm_agent_config import LLMAgentConfig
from games.generated.remnant.agent import Agent

captured={};calls=[];comparisons=[];transition_pairs=[];original_gate=Baseline.gate;in_shadow=False
tracker=Candidate()
fields=['threats','observed_max_hp','emergency_progress','emergency_contract','emergency_streaks']
def emit(self,e):
 if e['event']=='decision':captured[e['step']]={k:e[k] for k in ['action','model_calls','local_steps','fallbacks','reviews','dispatch']}
def recorded_generate(self,user_prompt,system_prompt,controller=False):
 step=agent.ledger.step;key=(step,controller);assert key not in calls,('duplicate response use',key)
 source=controllers if controller else decisions
 assert step in source and source[step]['response'] is not None,('unexpected provider request',key)
 calls.append(key);return {'response':source[step]['response'],'num_input_tokens':0,'num_output_tokens':0}
def paired_gate(self,seq,goal,source):
 global in_shadow
 c,v=original_gate(self,seq,goal,source)
 if in_shadow:return c,v
 # gate/action_check/validate_plan only append to control_checks; all physical
 # transitions are on copied resource state. Isolate that audit plus new fields.
 shadow=copy.copy(self);shadow.__class__=Candidate;shadow.init_emergency_fields();shadow.control_checks=[]
 for f in fields:setattr(shadow,f,copy.deepcopy(getattr(tracker,f)))
 try:
  in_shadow=True;nc,nv=shadow.gate(seq,goal,source)
 finally:in_shadow=False
 assert v==nv
 comparisons.append({'step':self.step,'action':seq[0],'sequence':seq,'source':source,'goal':goal,
  'parent_action':self.contract and self.contract['action'],'health':self.hp,
  'scope':shadow.emergency_scope(seq[0]),'old_blockers':copy.deepcopy(c['blockers']),
  'new_blockers':copy.deepcopy(nc['blockers']),'new_warnings':[w for w in nc['warnings'] if w['kind'] in ['parent_progress_not_applicable_to_emergency','healing_effect_positive_but_net_health_not_improving','repeated_emergency_no_effect']],
  'previously_diagnosed':(self.step,seq[0]) in target})
 return c,v

with patch.object(socket.socket,'connect',side_effect=AssertionError('Network forbidden during replay')),patch.object(LLMAgentConfig,'get_llm',return_value=None),patch.object(FeedbackV3R4Agent,'emit',emit),patch.object(Model,'generate',recorded_generate):
 agent=create_feedback_v3r4_agent(Agent)('agent_adam_davis','adam_davis',LLMAgentConfig(llm_name='deepseek-flash',llm_provider='openai'))
 tracker.schemas=agent.schemas
 with patch.object(Baseline,'gate',paired_gate):
  for step,row in enumerate(rows,1):
   tracker.advance(row['observation']['text'])
   action,_,_,_=agent._act(row['observation'])
   expected=decisions[step];got=captured[step]
   assert action==row['action']==expected['action'],('action divergence',step,action,row['action'])
   for k in ['model_calls','local_steps','fallbacks','reviews']:assert got[k]==expected[k],('counter divergence',step,k,got[k],expected[k])
   assert got['dispatch']['source']==expected['dispatch']['source'],('dispatch divergence',step)
   # Here the action is actually recorded as executed, so its next observation
   # is valid for both accumulator evaluations. This is not a changed-action rollout.
   probe=copy.copy(agent.ledger);probe.__class__=Candidate;probe.init_emergency_fields()
   for f in fields:setattr(probe,f,copy.deepcopy(getattr(tracker,f)))
   if probe.emergency_scope(action):
    old=copy.deepcopy(agent.ledger);new=copy.deepcopy(probe)
    seen_before=copy.deepcopy(old.contract['seen']) if old.contract else {}
    old_failed=copy.deepcopy(old.failed_plans)
    new.choose(action,old.pending['reasoning'],old.pending['goal_id'],old.pending.get('test_id'),copy.deepcopy(old.pending['check']))
    old.advance(row['next_observation']['text']);new.advance(row['next_observation']['text'])
    transition_pairs.append({'step':step,'action':action,'parent_action':agent.ledger.contract and agent.ledger.contract['action'],
     'candidate_outcome':new.emergency_progress[-1],
     'old_new_failure_records':{k:v for k,v in old.failed_plans.items() if old_failed.get(k)!=v},
     'candidate_new_failure_records':{k:v for k,v in new.failed_plans.items() if old_failed.get(k)!=v},
     'old_parent_seen_changed':bool(old.contract and old.contract['seen']!=seen_before),
     'candidate_parent_seen_changed':bool(new.contract and new.contract['seen']!=seen_before)})
   tracker.choose(action,'Frozen executed action only',tracker.focus)
  tracker.advance(rows[-1]['next_observation']['text'])
changed=[x for x in comparisons if x['old_blockers']!=x['new_blockers']]
nonemergency=[x for x in comparisons if not x['action'].startswith(('attack ','eat '))]
resource=[x for x in nonemergency if any(b['kind']=='same_failed_action_context' and b['detail'].get('reason')==[NO_RESOURCE_PROGRESS] for b in x['old_blockers'])]
unique=[]
for step,action in sorted(target):
 cells=[x for x in comparisons if x['step']==step and x['action']==action and x['old_blockers']]
 assert cells,('missing target',step,action)
 unique.append({'step':step,'action':action,'health':cells[0]['health'],'parent_action':cells[0]['parent_action'],
   'gate_invocations':len(cells),'old_rejected':all(bool(x['old_blockers']) for x in cells),
   'new_all_admissible':all(not x['new_blockers'] for x in cells),'remaining_blockers':[x['new_blockers'] for x in cells if x['new_blockers']],
   'scope':cells[0]['scope'],'historical_executed':decisions[step]['action']})
after_hashes=hashes();assert before_hashes==after_hashes,'Protected artifact changed'
assert all(x['old_blockers']==x['new_blockers'] for x in nonemergency),'Non-emergency policy changed'
assert all(x['scope'] and all(b['kind']=='same_failed_action_context' and b['detail'].get('reason')==[NO_RESOURCE_PROGRESS] for b in x['old_blockers'] if b not in x['new_blockers']) for x in changed),'Unscoped blocker removed'
summary={'reconstructed_steps':len(rows),'reconstructed_actions_identical':True,
 'recorded_response_reuses':len(calls),'actor_response_reuses':sum(not x[1] for x in calls),'controller_response_reuses':sum(x[1] for x in calls),
 'paid_api_calls':0,'network_connect_attempts':0,'new_game_rollouts':0,
 'gate_invocations':len(comparisons),'changed_gate_invocations':len(changed),
 'nonemergency_gate_invocations':len(nonemergency),'nonemergency_blockers_unchanged':True,
 'nonemergency_resource_no_progress_blocks_preserved':len(resource),
 'historical_target_unique_step_actions':len(unique),'historical_target_released':sum(x['new_all_admissible'] for x in unique),
 'historical_target_action_types':dict(Counter(x['action'].split()[0] for x in unique)),
 'protected_artifacts_unchanged':len(before_hashes),
 'actual_executed_emergency_transition_pairs':len(transition_pairs),
 'prevented_new_resource_failure_records':sum(any(v.get('reason')==[NO_RESOURCE_PROGRESS] for v in x['old_new_failure_records'].values()) and not any(v.get('reason')==[NO_RESOURCE_PROGRESS] for v in x['candidate_new_failure_records'].values()) for x in transition_pairs),
 'scope':'Paired one-step gate checks at reconstructed frozen old states; candidate actions never drive the historical trajectory. Not score evaluation.'}
result={'summary':summary,'historical_cases':unique,'changed_gates':changed,'all_gates':comparisons,'observed_emergency_outcomes':tracker.emergency_progress,'actual_transition_pairs':transition_pairs,
 'protected_sha256_before':before_hashes,'protected_sha256_after':after_hashes,
 'candidate_sha256':hashlib.sha256((repo/'agents/feedback_v3r5_core.py').read_bytes()).hexdigest()}
(out/'historical_replay.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(summary,ensure_ascii=False,indent=2))
