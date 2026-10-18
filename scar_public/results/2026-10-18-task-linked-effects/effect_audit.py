"""Cache-only, post-hoc compiler audits. Not independent policy evaluations."""
import contextlib,copy,importlib.util,json,os
from pathlib import Path
from scar.environment import AGENT_ID,restore,snapshot,state_digest
from scar.io import atomic_json
from scar_public.experiments.continuation_branch import ReusingProvider
from scar_public.experiments.core_trial import build_system
from scar_public.plan_repair import PlanRepairAgent
from scar_public.effect_repair import EffectRepairAgent
from scar_public.continuation import task_key
from scar_public.provider import usage_summary

root=Path('/root/scar_effect_v3_20261018');out=root/'audit';out.mkdir(exist_ok=True)
read=lambda p:json.loads(p.read_text());block=Path('/root/scar_core_valid_20261017/evaluation/mark_r1')
assert os.environ['PYTHONHASHSEED']==read(block/'manifest.json')['hash_seed']
def load_class(version):
    path=Path('/root')/version/'frozen/scar_public/effect_repair.py'
    spec=importlib.util.spec_from_file_location(version,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.EffectRepairAgent
e1=load_class('scar_effect_20261018');e2=load_class('scar_effect_v2_20261018')
historical=[Path('/root')/v/'evaluation/mark_r1/api' for v in ('scar_plan_v2_20261018','scar_plan_20261018','scar_objective_v3_20261018','scar_objective_v2_20261018','scar_objective_20261018','scar_hypothesis_v2_20261018','scar_hypothesis_20261018','scar_effect_v2_20261018')]
historical += [Path('/root')/v/'probes/mark_r1/effect/api' for v in ('scar_effect_20261018','scar_effect_v2_20261018','scar_effect_v3_20261018')]
def reconstruct(version,cls,decision):
    source=Path('/root')/version/'evaluation/mark_r1'
    provider=ReusingProvider(out/version/'api','/root/scar_research_20261015/private/deepseek.key',historical=block/'api',additional_historical=historical)
    provider.cache_only=True;provider.arm='audit';state=(block/'initial.pkl').read_bytes();agent=cls(provider,build_system(restore(state),provider.model));agent.max_steps=300
    for step in range(decision):
        provider.step=step;t=read(source/'trace'/f'{step+1:04d}.json');env=restore(state,out/'private_replay')
        assert state_digest(env)==t['before_digest'];action,*_=agent.act(dict(text=t['observation'],step=step));assert action==t['action']
        if step+1==decision:return agent,t,usage_summary(out/version/'api')
        env=restore(state,out/'private_replay');obs,reward,done,_=env.step({AGENT_ID:action});env.update_scores(reward)
        assert state_digest(env)==t['after_digest'] and obs[AGENT_ID]['text']==t['next_observation'];state=snapshot(env)

with (out/'audit.log').open('w') as log,contextlib.redirect_stdout(log):
    a,t,u1=reconstruct('scar_plan_v2_20261018',PlanRepairAgent,49)
    source=read(Path('/root/scar_effect_20261018/probes/mark_r1/result.json'))['results']['effect']['rows'][0]
    assert source['before_digest']==t['before_digest']
    response=source['response']['continuation']['proposal'];comparisons={}
    for label,cls in [('e1',e1),('e3',EffectRepairAgent)]:
        b=copy.deepcopy(a);b.__class__=cls;b.plan=b.root_plan(t['response'],task_key(b.notebook),48);c=b.compiler(task_key(b.notebook),48);frontier=b.expand_known(c)
        choices,rejections=b.ground_methods(response,frontier,c,task_key(b.notebook),48)
        comparisons[label]=dict(accepted=bool(choices),action=choices[0]['compiled'].get('action') if choices else None,
            root=b.plan['root_need'],unmet=frontier['need'],rejections=rejections)
    assert not comparisons['e1']['accepted'] and comparisons['e3']['action']=='pick up key'
    a,t,u2=reconstruct('scar_effect_v2_20261018',e2,52)
    before=a.compiler(task_key(a.notebook),51).compile(a.plan)
    assert before['kind']=='OTHER_TASK_RESOURCE'
    b=copy.deepcopy(a);b.__class__=EffectRepairAgent;old_goals=copy.deepcopy(b.plan['goals'])
    b.plan['goals']=b.distinct_goals(b.plan['goal_quote'],b.plan['goals'])
    after=b.compiler(task_key(b.notebook),51).compile(b.plan)
    assert after['action']=='craft 1 copper_sword'
    result=dict(qualification=__doc__,prefix_replays=48+51,usage=[u1,u2],
        same_proposal=dict(decision=49,digest=source['before_digest'],supplied_response=response,comparisons=comparisons),
        task_alias=dict(decision=52,digest=t['before_digest'],public_task_registry=b.notebook.progress_tasks,
            original_goals=old_goals,distinct_goals=b.plan['goals'],before=before,after=after,
            qualification='Compilation only; the required crafting station is still empirically unknown. No new game score is inferred.'))
    atomic_json(out/'result.json',result)
print(json.dumps(dict(prefix_replays=result['prefix_replays'],usage=result['usage'],same_proposal_actions={k:v['action'] for k,v in comparisons.items()},alias_action=after['action'])))
