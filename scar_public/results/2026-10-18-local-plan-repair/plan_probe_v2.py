"""Matched diagnostic with evaluator-bound inherited trial; not an independent run."""
import contextlib,copy,hashlib,json,os,sys
from pathlib import Path
from scar.environment import AGENT_ID,restore,snapshot,state_digest
from scar.io import atomic_json
from scar_public.experiments.continuation_branch import ReusingProvider
from scar_public.experiments.core_trial import build_system
from scar_public.hypothesis_repair import HypothesisRepairAgent
from scar_public.objective_repair import ObjectiveRepairAgent,TrialEvidence,requirement_catalog,compile_verification
from scar_public.plan_repair import PlanRepairAgent,catalog,need_key
from scar_public.continuation import task_key
from scar_public.provider import usage_summary

name=sys.argv[1];root=Path('/root/scar_plan_v2_20261018');out=root/'probes'/name;out.mkdir(parents=True,exist_ok=True)
legacy=name=='failed_source';world='mark_r1' if legacy else 'mark_r0';prefix=188 if legacy else 59
block=Path('/root/scar_core_valid_20261017/evaluation')/world
historical=[Path('/root/scar_hypothesis_20261018/evaluation')/world/'api',
    Path('/root/scar_hypothesis_v2_20261018/evaluation')/world/'api',
    Path('/root/scar_objective_20261018/evaluation')/world/'api',
    Path('/root/scar_objective_v2_20261018/evaluation')/world/'api']
historical += [Path('/root/scar_plan_20261018/probes')/name/arm/'api' for arm in ('objective','plan')]
source=Path('/root/scar_hypothesis_v2_20261018/evaluation' if legacy else '/root/scar_objective_v2_20261018/evaluation')/world
assert os.environ['PYTHONHASHSEED']==json.loads((block/'manifest.json').read_text())['hash_seed']
key='/root/scar_research_20261015/private/deepseek.key'
provider=ReusingProvider(out/'prefix_api',key,historical=block/'api',additional_historical=historical)
provider.cache_only=True;provider.arm='prefix_reconstruction'
state=(block/'initial.pkl').read_bytes();system=build_system(restore(state),provider.model)
agent=(HypothesisRepairAgent if legacy else ObjectiveRepairAgent)(provider,system)
with (out/'prefix.log').open('w') as log,contextlib.redirect_stdout(log):
    for step in range(prefix):
        row=json.loads((source/'trace'/f'{step+1:04d}.json').read_text());provider.step=step
        env=restore(state,out/'private_replay');assert state_digest(env)==row['before_digest']
        action,*_=agent.act(dict(text=row['observation'],step=step));assert action==row['action']
        env=restore(state,out/'private_replay');obs,reward,done,_=env.step({AGENT_ID:action});env.update_scores(reward)
        assert state_digest(env)==row['after_digest'] and obs[AGENT_ID]['text']==row['next_observation']
        state=snapshot(env)
program=copy.deepcopy(agent.hypothesis_pending['program']);goal=program['goal_quote'];task=task_key(agent.notebook)
if legacy:
    original={**row['response'],'action':row['response']['continuation']['original']}
    needs=requirement_catalog(agent.notebook,original,[goal],agent.continuation)
    need=next(n for n in needs if n['target']=='copper_bar')
    spec={**program,'need_id':need['id'],'verification':dict(mode='source',site='library')}
    compiled,errors=compile_verification(spec,needs);assert not errors
    program['objective']=compiled
else:need=program['objective']['need']
calls_before=len(agent.hypothesis_queries);initial_count=10 if legacy else calls_before
results={}
for arm in ('objective','plan'):
    a=copy.deepcopy(agent);a.__class__=ObjectiveRepairAgent if arm=='objective' else PlanRepairAgent
    p=ReusingProvider(out/arm/'api',key,historical=block/'api',additional_historical=historical);p.arm=arm+'_probe';a.llm=p
    if arm=='objective':
        a.trial_evidence=TrialEvidence();a.revision_due=None;a.hypothesis_queries=a.hypothesis_queries[:initial_count]
        a.hypothesis_pending['program']=copy.deepcopy(program)
    else:
        c=catalog(a.notebook);site_name=program['objective']['test']['location']
        sid=next((k for k,v in c['sites'].items() if v['location']==site_name),None)
        if sid is None:sid=next(k for k,v in c['sites'].items() if v['name']==site_name.split(', ')[-1])
        a.plan=dict(root_need=need,task=task,goal_quote=goal,goals=[goal],bindings={need_key(need):dict(kind='source',site_id=sid)},completed=[],started=prefix-1)
        a.plan_pending=dict(action=row['action'],test=program['steps'][agent.hypothesis_pending['index']]['test'],stage='route',need=need,chain=[need],steps=program['steps'])
        a.plan_ledger=[];a.plan_queries=[dict(step=-999,context='inherited_count') for _ in range(initial_count)]
    branch=state;rows=[];initial_score=restore(state).scores[AGENT_ID]['quest'];fulfilled=False
    with (out/arm/'rollout.log').open('w') as log,contextlib.redirect_stdout(log):
        for step in range(prefix,prefix+8):
            p.step=step;env=restore(branch,out/arm/'environment');text=env.obs[AGENT_ID]['text'];before=state_digest(env)
            action,inp,outp,response=a.act(dict(text=text,step=step));parsed=json.loads(response)
            env=restore(branch,out/arm/'environment');obs,reward,done,_=env.step({AGENT_ID:action});env.update_scores(reward)
            following=obs[AGENT_ID]['text'];after=state_digest(env)
            replay=restore(branch,out/arm/'replay');ro,rr,rd,_=replay.step({AGENT_ID:action});replay.update_scores(rr)
            assert state_digest(replay)==after and ro[AGENT_ID]['text']==following
            rows.append(dict(step=step+1,observation=text,action=action,response=parsed,next_observation=following,
                             before_digest=before,after_digest=after,scores=env.scores[AGENT_ID]))
            branch=snapshot(env)
            from scar_public.public_model import state_from_text
            held=state_from_text(following)['holding'];fulfilled=held is not None and held.get(need['target'],0)>=need['count']
            if fulfilled or done:break
        a.observe_terminal(dict(text=following,step=step+1))
    results[arm]=dict(rows=rows,outcomes=a.obstacle_outcomes[-12:],fulfilled=fulfilled,steps=len(rows),
        score_delta=rows[-1]['scores']['quest']-initial_score,usage=usage_summary(out/arm/'api'),
        proposal_calls_after=len(a.hypothesis_queries if arm=='objective' else a.plan_queries))
result=dict(name=name,qualification=__doc__,prefix_replays=prefix,initial_digest=row['after_digest'],
    source=str(source),requirement=need,goal=goal,evaluator_binding=True,
    legacy_proposal_calls=calls_before,initial_counter=initial_count,
    budget_intervention='Both arms receive two supplemental proposal calls' if legacy else 'None; inherited prior call count',
    results=results,evaluator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
atomic_json(out/'result.json',result)
print(json.dumps({k:{f:v[f] for f in ('fulfilled','steps','score_delta','proposal_calls_after','usage')} for k,v in results.items()}))
