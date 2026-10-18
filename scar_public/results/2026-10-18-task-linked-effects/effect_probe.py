"""Five predeclared matched development branches; no hidden state enters policy."""
import contextlib,copy,hashlib,json,os,sys
from pathlib import Path
from scar.environment import AGENT_ID,restore,snapshot,state_digest
from scar.io import atomic_json
from scar_public.experiments.continuation_branch import ReusingProvider
from scar_public.experiments.core_trial import build_system
from scar_public.hypothesis_repair import HypothesisRepairAgent
from scar_public.objective_repair import ObjectiveRepairAgent,requirement_catalog,compile_verification
from scar_public.plan_repair import PlanRepairAgent,catalog,need_key
from scar_public.effect_repair import EffectRepairAgent
from scar_public.continuation import task_key,feedback_lines
from scar_public.public_model import state_from_text
from scar_public.provider import usage_summary

read=lambda p:json.loads(p.read_text())
name=sys.argv[1];root=Path('/root/scar_effect_20261018');out=root/'probes'/name;out.mkdir(parents=True,exist_ok=True)
settings={'mark_r0':('mark_r0',48,'scar_plan_v2_20261018',PlanRepairAgent,'copper_sword'),
    'mark_r1':('mark_r1',48,'scar_plan_v2_20261018',PlanRepairAgent,'copper_sword'),
    'route_value':('metropolis_r1',114,'scar_plan_v2_20261018',PlanRepairAgent,None),
    'failed_source':('mark_r1',188,'scar_hypothesis_v2_20261018',HypothesisRepairAgent,'copper_bar'),
    'positive_source':('mark_r0',59,'scar_objective_v2_20261018',ObjectiveRepairAgent,'copper_bar')}
world,prefix,version,klass,target=settings[name];legacy=name=='failed_source';bound=name in ('failed_source','positive_source')
block=Path('/root/scar_core_valid_20261017/evaluation')/world;source=Path('/root')/version/'evaluation'/world
assert os.environ['PYTHONHASHSEED']==read(block/'manifest.json')['hash_seed']
historical=[Path('/root')/v/'evaluation'/world/'api' for v in ('scar_plan_v2_20261018','scar_plan_20261018','scar_objective_v3_20261018','scar_objective_v2_20261018','scar_objective_20261018','scar_hypothesis_v2_20261018','scar_hypothesis_20261018')]
if bound:historical += [Path('/root')/v/'probes'/name/'plan/api' for v in ('scar_plan_v2_20261018','scar_plan_20261018')]
key='/root/scar_research_20261015/private/deepseek.key'
p=ReusingProvider(out/'prefix_api',key,historical=block/'api',additional_historical=historical);p.cache_only=True;p.arm='prefix'
state=(block/'initial.pkl').read_bytes();a=klass(p,build_system(restore(state),p.model));a.max_steps=300
with (out/'prefix.log').open('w') as log,contextlib.redirect_stdout(log):
    for step in range(prefix):
        p.step=step;t=read(source/'trace'/f'{step+1:04d}.json');env=restore(state,out/'private_replay')
        assert state_digest(env)==t['before_digest'];action,*_=a.act(dict(text=t['observation'],step=step));assert action==t['action']
        env=restore(state,out/'private_replay');obs,reward,done,_=env.step({AGENT_ID:action});env.update_scores(reward)
        assert state_digest(env)==t['after_digest'] and obs[AGENT_ID]['text']==t['next_observation'];state=snapshot(env)
calls_before=len(a.hypothesis_queries if bound else a.plan_queries)
if bound:
    program=copy.deepcopy(a.hypothesis_pending['program']);goal=program['goal_quote'];task=task_key(a.notebook)
    if legacy:
        original={**t['response'],'action':t['response']['continuation']['original']}
        needs=requirement_catalog(a.notebook,original,[goal],a.continuation);need=next(n for n in needs if n['target']==target)
        compiled,errors=compile_verification({**program,'need_id':need['id'],'verification':dict(mode='source',site='library')},needs);assert not errors
        program['objective']=compiled
    else:need=program['objective']['need']
    c=catalog(a.notebook);site=program['objective']['test']['location']
    sid=next((k for k,v in c['sites'].items() if v['location']==site),None)
    if sid is None:sid=next(k for k,v in c['sites'].items() if v['name']==site.split(', ')[-1])
    a.plan=dict(root_need=need,task=task,goal_quote=goal,goals=[goal],bindings={need_key(need):dict(kind='source',site_id=sid)},completed=[],started=prefix-1)
    a.plan_pending=dict(action=t['action'],test=program['steps'][a.hypothesis_pending['index']]['test'],stage='route',need=need,chain=[need],steps=program['steps'])
    a.plan_ledger=[];a.plan_queries=[dict(step=-999,context='inherited_count') for _ in range(10 if legacy else calls_before)]
results={}
for arm,cls in [('plan',PlanRepairAgent),('effect',EffectRepairAgent)]:
    agent=copy.deepcopy(a);agent.__class__=cls
    provider=ReusingProvider(out/arm/'api',key,historical=block/'api',additional_historical=historical)
    # The old arm is a frozen reference: missing cache must not silently incur cost.
    provider.cache_only=arm=='plan';provider.arm=arm;agent.llm=provider
    branch=state;rows=[];initial_score=restore(state).scores[AGENT_ID]['quest'];fulfilled=False
    with (out/arm/'rollout.log').open('w') as log,contextlib.redirect_stdout(log):
        for step in range(prefix,prefix+8):
            provider.step=step;env=restore(branch,out/arm/'environment');text=env.obs[AGENT_ID]['text'];before=state_digest(env)
            action,inp,outp,response=agent.act(dict(text=text,step=step));parsed=json.loads(response)
            env=restore(branch,out/arm/'environment');obs,reward,done,_=env.step({AGENT_ID:action});env.update_scores(reward)
            following=obs[AGENT_ID]['text'];after=state_digest(env)
            replay=restore(branch,out/arm/'replay');ro,rr,rd,_=replay.step({AGENT_ID:action});replay.update_scores(rr)
            assert state_digest(replay)==after and ro[AGENT_ID]['text']==following
            rows.append(dict(step=step+1,observation=text,action=action,response=parsed,next_observation=following,before_digest=before,after_digest=after,scores=env.scores[AGENT_ID]))
            branch=snapshot(env);held=state_from_text(following)['holding']
            fulfilled=bool(target and held is not None and held.get(target,0)>=1)
            if fulfilled or done:break
        agent.observe_terminal(dict(text=following,step=step+1))
    results[arm]=dict(rows=rows,outcomes=agent.obstacle_outcomes[-16:],fulfilled=fulfilled,steps=len(rows),
        score_delta=rows[-1]['scores']['quest']-initial_score,failures=sum(bool(feedback_lines(t['next_observation'])) for t in rows),
        overrides=sum(t['response']['continuation']['changed'] for t in rows),proposal_calls_after=len(agent.plan_queries),usage=usage_summary(out/arm/'api'))
result=dict(name=name,world=world,source=str(source),prefix_replays=prefix,initial_digest=t['after_digest'],target=target,
    evaluator_binding=bound,legacy_proposal_calls=calls_before,budget_intervention='Two supplemental calls for both arms' if legacy else 'None',
    qualification=__doc__,results=results,evaluator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
atomic_json(out/'result.json',result)
print(json.dumps({k:{f:v[f] for f in ('fulfilled','steps','score_delta','failures','overrides','proposal_calls_after','usage')} for k,v in results.items()}))
