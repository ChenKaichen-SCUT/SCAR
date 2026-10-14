"""Three independent 300-action runs, atomic checkpoints, no score retries."""
import argparse
import contextlib
import copy
import io
import shutil
import time
import traceback
from .common import *
from .integration import make_agent
from .provider import SharedProvider
from scar_stage22.run import checkpoint


def execute(game,key):
    from scar.environment import restore,state_digest
    from agents.agc.agent import DecisionUnavailable
    check_freeze();folder=RUNTIME/'runs'/f'{game}__AGC';output=RESULTS/'runs'/folder.name
    if (output/'summary.json').exists():return read(output/'summary.json')
    folder.mkdir(parents=True,exist_ok=True);(folder/'steps').mkdir(exist_ok=True)
    provider=SharedProvider(folder,RUNTIME,key)
    with contextlib.redirect_stdout(io.StringIO()):agent=make_agent(game,provider,folder/'memory')
    initial=RESULTS/'initial'/game;started=time.time();error=None;status='infrastructure_error'
    if (folder/'latest.json').exists():
        cp=folder/read(folder/'latest.json')['checkpoint']
        with contextlib.redirect_stdout(io.StringIO()):agent.load_memory(cp)
        env=restore(cp/'physical.pkl',folder,agent);assert state_digest(env)==read(cp/'meta.json')['state_hash']
    else:
        env=restore(gzip.decompress((initial/'physical.pkl.gz').read_bytes()),folder,agent)
        assert state_digest(env)==read(initial/'initial_public.json')['initial_state_hash']
        agent.initialize_official(env.obs[AGENT_ID]);checkpoint(folder,env,agent)
    env.config.update(game_name=game,seed=SEED,max_steps=300,agent='AGC',llm_name=MODEL['model'],stage24_research_only=True)
    env.update_config()
    done=bool(env.steps and read(folder/'steps'/f'{env.steps:03d}.json')['done'])
    try:
        while env.steps<MAX_STEPS:
            if done:break
            step=env.steps+1;before=copy.deepcopy(env.obs[AGENT_ID]);before_hash=state_digest(env)
            memory_before=list(agent.short_term_memory);provider.begin_step(step)
            with contextlib.redirect_stdout(io.StringIO()):action,tin,tout,response=agent.act(before)
            decision=copy.deepcopy(agent.decision)
            with contextlib.redirect_stdout(io.StringIO()):obs,reward,done,info=env.step({AGENT_ID:action});env.update_scores(reward)
            after=copy.deepcopy(obs[AGENT_ID]);agent.observe_transition(before,action,after)
            row=dict(step=step,game=game,method='AGC',observation=before,feedback=after,action=action,response=response,
                reward=vars(reward[AGENT_ID]),scores=copy.deepcopy(env.scores[AGENT_ID]),done=bool(done),info=info,
                invalid_action=bool(info.get('step_invalid_action',{}).get(AGENT_ID,False)),state_hash_before=before_hash,state_hash=state_digest(env),
                decision=decision,transition=copy.deepcopy(agent.transition),control_after=copy.deepcopy(agent.control.to_dict()),
                memory_before=memory_before,input_tokens=tin,output_tokens=tout,
                main_quest_progress=copy.deepcopy(env.curr_agents_state.get('main_quest_progress',{}).get(AGENT_ID)))
            dest=folder/'steps'/f'{step:03d}.json'
            if dest.exists():assert read(dest)==row,'Resume differs from original saved transition'
            else:write(dest,row)
            agent.control.events.clear();checkpoint(folder,env,agent);env.update_config()
            write(folder/'progress.json',dict(step=step,scores=row['scores'],cost_usd=provider.episode.total(),requests=len(provider.cache),updated=time.time()))
            if done:break
        status='native_done' if done else 'step_limit'
    except DecisionUnavailable as exc:
        status='agent_decision_exhausted';error=str(exc)
        write(folder/'decision_exhausted.json',dict(step=env.steps+1,decision=agent.decision,observation=env.obs[AGENT_ID]))
    except Exception as exc:
        error=dict(type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc());print(error['traceback'],flush=True)
    env.update_config();output.mkdir(parents=True,exist_ok=True)
    rr=[read(p) for p in sorted((folder/'steps').glob('*.json'))]
    qq=[json.loads(x) for x in provider.audit.read_text().splitlines()] if provider.audit.exists() else []
    gzwrite(output/'trajectory.jsonl.gz',rr);gzwrite(output/'requests.jsonl.gz',qq)
    agent.save_memory(output/'final_memory')
    for name in ['config.json','decision_exhausted.json']:
        if (folder/name).exists():shutil.copyfile(folder/name,output/name)
    shutil.copyfile(initial/'initial_public.json',output/'initial_public.json')
    summary=dict(game=game,method='AGC',seed=SEED,status=status,error=error,steps=len(rr),max_steps=300,
        scores=env.scores[AGENT_ID],main_quest_progress=copy.deepcopy(env.curr_agents_state.get('main_quest_progress',{}).get(AGENT_ID)),
        requests=len(qq),reconsider_calls=sum(r['decision']['reconsider_calls'] for r in rr),input_tokens=sum(q.get('usage',{}).get('prompt_tokens',0) for q in qq),
        output_tokens=sum(q.get('usage',{}).get('completion_tokens',0) for q in qq),cost_usd=sum(q.get('cost_usd',0) for q in qq),
        charged_or_reserved_usd=sum(q['charged_or_reserved_usd'] for q in qq),elapsed_seconds=time.time()-started,
        initial_state_hash=read(initial/'initial_public.json')['initial_state_hash'])
    write(output/'summary.json',summary);print(json.dumps(summary),flush=True);return summary


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--game',required=True,choices=GAMES);p.add_argument('--key',default=str(ROOT.parent/'miyao.txt'))
    args=p.parse_args();execute(args.game,args.key)
