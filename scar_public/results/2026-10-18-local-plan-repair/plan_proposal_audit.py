"""Post-hoc supplied-proposal audit, not autonomous recovery or new evaluation."""
import contextlib,json,os
from pathlib import Path
from scar.environment import AGENT_ID,restore,snapshot,state_digest
from scar.io import atomic_json
from scar_public.experiments.continuation_branch import ReusingProvider
from scar_public.experiments.core_trial import build_system
from scar_public.plan_repair import PlanRepairAgent
from scar_public.continuation import task_key
from scar_public.provider import usage_summary

read=lambda p:json.loads(p.read_text())
root=Path('/root/scar_plan_v2_20261018');out=root/'audit';out.mkdir(exist_ok=True)
source=root/'evaluation/mark_r1';old=Path('/root/scar_core_valid_20261017/evaluation/mark_r1')
assert os.environ['PYTHONHASHSEED']==read(old/'manifest.json')['hash_seed']
historical=[Path('/root')/v/'evaluation/mark_r1/api' for v in ('scar_plan_20261018','scar_objective_v2_20261018','scar_objective_20261018','scar_hypothesis_v2_20261018','scar_hypothesis_20261018')]
p=ReusingProvider(out/'api','/root/scar_research_20261015/private/deepseek.key',historical=old/'api',additional_historical=[source/'api']+historical)
p.cache_only=True;p.arm='proposal_audit';state=(old/'initial.pkl').read_bytes()
a=PlanRepairAgent(p,build_system(restore(state),p.model));a.max_steps=300
with (out/'audit.log').open('w') as log,contextlib.redirect_stdout(log):
    for step in range(49):
        p.step=step;t=read(source/'trace'/f'{step+1:04d}.json');env=restore(state,out/'private_replay')
        assert state_digest(env)==t['before_digest']
        action,*_=a.act(dict(text=t['observation'],step=step));assert action==t['action']
        if step==48:break
        env=restore(state,out/'private_replay');obs,reward,done,_=env.step({AGENT_ID:action});env.update_scores(reward)
        assert state_digest(env)==t['after_digest'] and obs[AGENT_ID]['text']==t['next_observation']
        state=snapshot(env)
    first=read(Path('/root/scar_plan_20261018/evaluation/mark_r1/trace/0049.json'))
    assert first['before_digest']==t['before_digest'] and first['observation']==t['observation']
    old_event=first['response']['continuation'];new_event=t['response']['continuation'];packet=new_event['packet']
    choices,rejects=a.parse_methods(old_event['proposal'],packet['requirements'],packet['goals'],a.compiler(task_key(a.notebook),48),task_key(a.notebook),48)
    assert choices and choices[0]['compiled']['action']=='pick up key'
    result=dict(qualification=__doc__,world='mark_r1',decision=49,prefix_replays=48,initial_digest=t['before_digest'],
        identical_public_state=True,supplied_proposal_source='p1 Mark-r1 decision 49',
        actual_p2_action=t['action'],actual_p2_reason=new_event['reason'],
        actual_p2_initial_rejections=new_event.get('initial_rejections'),actual_p2_final_rejections=new_event.get('program_rejections'),
        supplied_proposal=old_event['proposal'],p2_accepts_supplied_proposal=True,
        compiled_action=choices[0]['compiled']['action'],rejections=rejects,
        interpretation='The p2 compiler still admits the prior key hypothesis at the identical state. Actual p2 did not generate this method and its correction omitted the required schema. This diagnoses proposal reliability; it does not estimate whole-game improvement or establish causality of the p2 changes.',
        usage=usage_summary(out/'api'))
    atomic_json(out/'result.json',result)
print(json.dumps({k:result[k] for k in ('prefix_replays','p2_accepts_supplied_proposal','compiled_action','usage')}))
