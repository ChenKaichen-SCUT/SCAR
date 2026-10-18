import contextlib,copy,hashlib,json,os
from pathlib import Path
from scar.environment import AGENT_ID,restore,snapshot,state_digest
from scar.io import atomic_json
from scar_public.experiments.continuation_branch import ReusingProvider
from scar_public.experiments.core_trial import build_system
from scar_public.hypothesis_repair import HypothesisRepairAgent
from scar_public.objective_repair import ObjectiveRepairAgent,requirement_catalog
from scar_public.continuation import task_key

root=Path('/root/scar_objective_20261018');out=root/'audit';out.mkdir(exist_ok=True)
old=Path('/root/scar_hypothesis_v2_20261018/evaluation/mark_r1')
block=Path('/root/scar_core_valid_20261017/evaluation/mark_r1')
assert os.environ['PYTHONHASHSEED']==json.loads((block/'manifest.json').read_text())['hash_seed']
provider=ReusingProvider(out/'api','/root/scar_research_20261015/private/deepseek.key',historical=block/'api',
    additional_historical=[Path('/root/scar_hypothesis_20261018/evaluation/mark_r1/api'),old/'api'])
provider.cache_only=True;provider.arm='public_history_audit'
state=(block/'initial.pkl').read_bytes();system=build_system(restore(state),provider.model)
agent=HypothesisRepairAgent(provider,system)
with (out/'replay.log').open('w') as log,contextlib.redirect_stdout(log):
    for step in range(188):
        row=json.loads((old/'trace'/f'{step+1:04d}.json').read_text());provider.step=step
        env=restore(state,out/'private_replay')
        assert state_digest(env)==row['before_digest']
        action,*_=agent.act(dict(text=row['observation'],step=step))
        assert action==row['action'],step
        env=restore(state,out/'private_replay');obs,reward,done,_=env.step({AGENT_ID:action});env.update_scores(reward)
        assert state_digest(env)==row['after_digest'] and obs[AGENT_ID]['text']==row['next_observation']
        state=snapshot(env)
new=ObjectiveRepairAgent(provider,system);new.notebook=copy.deepcopy(agent.notebook);new.continuation=copy.deepcopy(agent.continuation)
event=row['response']['continuation'];old_program=event['contract']
candidate={k:old_program[k] for k in ('goal_quote','blocker','hypothesis','task_link','basis','steps','branches')}
goals=[candidate['goal_quote']];task=task_key(new.notebook)
original={**row['response'],'action':event['original']}
needs=requirement_catalog(new.notebook,original,goals,new.continuation)
need=next(n for n in needs if n['target']=='copper_bar')
candidate.update(need_id=need['id'],verification=dict(mode='source',site='library'))
programs,rejected=new.proposals(dict(hypotheses=[candidate]),task,goals,needs,113,187)
assert programs and not rejected
new.hypothesis_pending=dict(program=programs[0],index=0)
text=row['next_observation'];new.notebook.prompt(text);new.notebook.refresh_tasks();new.continuation.observe(text,188)
new.repair_trigger=lambda *args:None
calls=[]
def fake_query(prompt):
    calls.append(prompt);return dict(action='enter hall',hypotheses=[])
result=new.finalize_decision(dict(action='enter hall',frame={}),dict(text=text),188,'AUDIT_CALLBACK_ONLY',fake_query)
outcome=result['continuation']['previous_repair']
assert outcome['execution_outcome'] is True and outcome['outcome'] is False and outcome['requirement_resolved'] is False
assert len(calls)==1 and new.trial_evidence.records
rejections=new.trial_evidence.objections(programs[0],new.notebook,189)
assert rejections and rejections[0]['reason']=='SOURCE_RECENTLY_TESTED_ABSENT'
audit=dict(qualification='Selected public-history compiler/control-flow audit. Need binding supplied by evaluator. Revision callback is a stub, not evidence of LLM generation or game improvement.',
    replayed_environment_transitions=188,replayed_actions=188,new_api_requests=0,
    before_digest=row['before_digest'],after_digest=row['after_digest'],candidate=candidate,requirement=need,
    observation=text,old_execution_only_test=True,new_outcome=outcome,revision_callback_count=len(calls),
    revision_packet=result['continuation']['packet'],same_source_rejections=rejections,
    evaluator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
atomic_json(out/'audit.json',audit)
print(json.dumps(dict(replays=188,old=True,new=outcome['outcome'],revision_callbacks=len(calls),new_api_requests=0)))
