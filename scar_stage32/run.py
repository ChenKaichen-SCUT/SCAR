"""Three SAER runs; complete baselines reused without new calls."""
import argparse
import contextlib
import copy
import io
import shutil
import time
import traceback
from .common import *
from .integration import make_agent
from scar_stage24.provider import SharedProvider
from scar_stage22.run import checkpoint


def execute(seed,key):
    method="SAER"
    from scar.environment import restore,state_digest
    from agents.agc.agent import DecisionUnavailable
    check_freeze(light=True);assert read(RESULTS/"offline_summary.json")["complete"];case=ident(seed);folder=RUNTIME/'runs'/case;out=RESULTS/'runs'/case
    if (out/'summary.json').exists():return read(out/'summary.json')
    folder.mkdir(parents=True,exist_ok=True)
    for name in ['steps','native_transitions']:(folder/name).mkdir(exist_ok=True)
    provider=SharedProvider(folder,RUNTIME,key);began=time.time()
    with contextlib.redirect_stdout(io.StringIO()):agent=make_agent(seed,provider,folder/'memory')
    prefix=[]
    historic=[]
    if (folder/'latest.json').exists():
        cp=folder/read(folder/'latest.json')['checkpoint']
        with contextlib.redirect_stdout(io.StringIO()):agent.load_memory(cp)
        env=restore(cp/'physical.pkl',folder,agent);assert state_digest(env)==read(cp/'meta.json')['state_hash']
    else:
        env=restore(gzip.decompress((initial(seed)/'physical.pkl.gz').read_bytes()),folder,agent)
        assert state_digest(env)==read(initial(seed)/'initial_public.json')['initial_state_hash']
        agent.initialize_official(env.obs[AGENT_ID]);checkpoint(folder,env,agent)
    env.config.update(game_name='remnant',seed=seed,max_steps=MAX_STEPS,agent=method,llm_name=MODEL['model'],stage32_research_only=True);env.update_config()
    last=folder/'steps'/f'{env.steps:03d}.json'
    done=bool(read(last)['done']) if last.exists() else False
    status='infrastructure_error';error=None
    try:
        while env.steps<MAX_STEPS and not done:
            n=env.steps+1;provider.begin_step(n);before=copy.deepcopy(env.obs[AGENT_ID]);before_hash=state_digest(env)
            memory=copy.deepcopy(agent.short_term_memory)
            task_before=agent.task_state.to_dict()
            with contextlib.redirect_stdout(io.StringIO()):action,tin,tout,response=agent.act(before)
            decision=copy.deepcopy(agent.decision)
            assert decision['executed_action']==action and not decision['controller_generated_action']
            with contextlib.redirect_stdout(io.StringIO()):obs,reward,done,info=env.step({AGENT_ID:action});env.update_scores(reward)
            after=copy.deepcopy(obs[AGENT_ID])
            row=dict(step=n,game='remnant',seed=seed,method=method,observation=before,feedback=after,action=action,response=response,
                reward=vars(reward[AGENT_ID]),scores=copy.deepcopy(env.scores[AGENT_ID]),done=bool(done),info=info,
                invalid_action=bool(info.get('step_invalid_action',{}).get(AGENT_ID,False)),state_hash_before=before_hash,state_hash=state_digest(env),
                decision=decision,memory_before=memory,input_tokens=tin,output_tokens=tout,
                main_quest_progress=copy.deepcopy(env.curr_agents_state.get('main_quest_progress',{}).get(AGENT_ID)))
            # An ingestion fault must not erase an already executed native action.
            write(folder/'native_transitions'/f'{n:03d}.json',row)
            agent.observe_transition(before,action,after)
            row.update(transition=copy.deepcopy(agent.transition),control_after=copy.deepcopy(agent.control.to_dict()))
            row.update(task_before=task_before,task_after=agent.task_state.to_dict())
            dest=folder/'steps'/f'{n:03d}.json'
            if dest.exists():assert read(dest)==row,'Cached-response resume diverged'
            else:write(dest,row)
            agent.control.events.clear();checkpoint(folder,env,agent);env.update_config()
            write(folder/'progress.json',dict(step=n,scores=row['scores'],new_requests=len(provider.cache),cost_usd=provider.episode.total(),updated=time.time()))
        status='native_done' if done else 'step_limit'
    except DecisionUnavailable as exc:
        status='agent_decision_exhausted';error=str(exc)
        write(folder/'decision_exhausted.json',dict(step=env.steps+1,decision=agent.decision,observation=env.obs[AGENT_ID]))
    except Exception as exc:
        error=dict(type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc());print(error['traceback'],flush=True)
    env.update_config();out.mkdir(parents=True,exist_ok=True)
    new_rows=[read(p) for p in sorted((folder/'steps').glob('*.json'))]
    newq=[json.loads(x) for x in provider.audit.read_text().splitlines()] if provider.audit.exists() else []
    rr=prefix+new_rows;qq=historic+newq
    gzwrite(out/'trajectory.jsonl.gz',rr);gzwrite(out/'requests.jsonl.gz',qq);gzwrite(out/'new_requests.jsonl.gz',newq)
    agent.save_memory(out/'final_memory')
    for name in ['config.json','decision_exhausted.json']:
        if (folder/name).exists():shutil.copyfile(folder/name,out/name)
    shutil.copyfile(initial(seed)/'initial_public.json',out/'initial_public.json')
    summary=dict(game='remnant',method=method,seed=seed,status=status,error=error,steps=len(rr),max_steps=MAX_STEPS,
        scores=env.scores[AGENT_ID],main_quest_progress=copy.deepcopy(env.curr_agents_state.get('main_quest_progress',{}).get(AGENT_ID)),
        requests=len(qq),new_requests=len(newq),new_actions=len(new_rows),historical_requests=len(historic),historical_actions=len(prefix),
        input_tokens=sum(q.get('usage',{}).get('prompt_tokens',0) for q in qq),output_tokens=sum(q.get('usage',{}).get('completion_tokens',0) for q in qq),
        cost_usd=sum(q.get('cost_usd',0) for q in qq),new_cost_usd=sum(q.get('cost_usd',0) for q in newq),
        historical_cost_usd=sum(q.get('cost_usd',0) for q in historic),charged_or_reserved_usd=sum(q['charged_or_reserved_usd'] for q in newq),
        elapsed_seconds=time.time()-began,initial_state_hash=read(initial(seed)/'initial_public.json')['initial_state_hash'],
        baseline_prefix_source=str(baseline(seed).relative_to(ROOT)) if prefix else None)
    write(out/'summary.json',summary);print(json.dumps(summary),flush=True);return summary


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--seed',type=int,choices=SEEDS,required=True);
    p.add_argument('--key',default=str(ROOT.parent/'miyao.txt'));a=p.parse_args();execute(a.seed,a.key)
