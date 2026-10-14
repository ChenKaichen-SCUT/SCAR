import argparse
import contextlib
import copy
import io
import shutil
import time
import traceback
from .common import *
from .provider import HierarchyProvider
from scar_stage25.integration import make_agent
from scar_stage22.run import checkpoint

def execute(ident):
    from scar.environment import restore,state_digest
    from agents.agc.agent import DecisionUnavailable
    check_freeze(light=True);out=RESULTS/'runs'/ident/'OracleGoalStack';folder=RUNTIME/'runs'/ident
    if (out/'summary.json').exists():return read(out/'summary.json')
    folder.mkdir(parents=True,exist_ok=True);(folder/'steps').mkdir(exist_ok=True)
    provider=HierarchyProvider(folder,ident,ROOT.parent/'miyao.txt');cp=CHECKPOINTS/ident;meta=read(RESULTS/'checkpoints'/ident/'meta.json');began=time.time()
    with contextlib.redirect_stdout(io.StringIO()):agent=make_agent('remnant',42,provider,folder/'memory')
    if (folder/'latest.json').exists():
        saved=folder/read(folder/'latest.json')['checkpoint']
        with contextlib.redirect_stdout(io.StringIO()):agent.load_memory(saved)
        env=restore(saved/'physical.pkl',folder,agent);assert state_digest(env)==read(saved/'meta.json')['state_hash']
    else:
        with contextlib.redirect_stdout(io.StringIO()):agent.load_memory(cp)
        env=restore(gzip.decompress((cp/'physical.pkl.gz').read_bytes()),folder,agent)
        assert state_digest(env)==meta['state_hash'];checkpoint(folder,env,agent)
    env.config.update(game_name='remnant',seed=42,max_steps=300,agent='Stage25-AGC-v2',stage30_objective_diagnostic=True);env.update_config()
    done=bool(env.steps>=meta['start'] and read(folder/'steps'/f'{env.steps:03d}.json')['done']);error=None;status='infrastructure_error'
    try:
        while env.steps<300 and not done:
            n=env.steps+1;provider.begin_step(n);before=copy.deepcopy(env.obs[AGENT_ID]);before_hash=state_digest(env);memory=copy.deepcopy(agent.short_term_memory)
            with contextlib.redirect_stdout(io.StringIO()):action,tin,tout,response=agent.act(before)
            decision=copy.deepcopy(agent.decision)
            with contextlib.redirect_stdout(io.StringIO()):obs,reward,done,info=env.step({AGENT_ID:action});env.update_scores(reward)
            after=copy.deepcopy(obs[AGENT_ID]);agent.observe_transition(before,action,after)
            row=dict(id=ident,step=n,continuation_step=n-meta['failure_step'],observation=before,feedback=after,
                action=action,decision=decision,response=response,memory_before=memory,
                reward=vars(reward[AGENT_ID]),scores=copy.deepcopy(env.scores[AGENT_ID]),done=bool(done),info=info,
                state_hash_before=before_hash,state_hash=state_digest(env),control_after=copy.deepcopy(agent.control.to_dict()),
                transition=copy.deepcopy(agent.transition),input_tokens=tin,output_tokens=tout,
                main_quest_progress=copy.deepcopy(env.curr_agents_state.get('main_quest_progress',{}).get(AGENT_ID)),
                objective_injected=n==meta['start'],action_overridden=False)
            dest=folder/'steps'/f'{n:03d}.json'
            if dest.exists():assert read(dest)==row,'Cached response resume diverged'
            else:write(dest,row)
            agent.control.events.clear();checkpoint(folder,env,agent);env.update_config()
            write(folder/'progress.json',dict(id=ident,step=n,scores=row['scores'],new_requests=len(provider.paid.cache),cost_usd=provider.paid.episode.total(),updated=time.time()))
        status='native_done' if done else 'step_limit'
    except DecisionUnavailable as exc:
        status='agent_decision_exhausted';error=str(exc)
        write(folder/'decision_exhausted.json',dict(step=env.steps+1,decision=agent.decision,observation=env.obs[AGENT_ID]))
    except Exception as exc:
        error=dict(type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc());print(error['traceback'],flush=True)
    env.update_config();out.mkdir(parents=True,exist_ok=True)
    rr=[read(p) for p in sorted((folder/'steps').glob('*.json'))];qq=[json.loads(x) for x in provider.paid.audit.read_text().splitlines()] if provider.paid.audit.exists() else []
    gzwrite(out/'trajectory.jsonl.gz',rr);gzwrite(out/'requests.jsonl.gz',qq);gzwrite(out/'interventions.jsonl.gz',list(provider.records.values()))
    agent.save_memory(out/'final_memory')
    for name in ['config.json','decision_exhausted.json']:
        if (folder/name).exists():shutil.copyfile(folder/name,out/name)
    result=dict(id=ident,variant='OracleGoalStack',start=meta['start'],failure_step=meta['failure_step'],status=status,error=error,
        steps=len(rr),last_step=env.steps,max_absolute_step=300,scores=env.scores[AGENT_ID],main_quest_progress=copy.deepcopy(env.curr_agents_state.get('main_quest_progress',{}).get(AGENT_ID)),
        new_requests=len(qq),cost_usd=sum(q.get('cost_usd',0) for q in qq),input_tokens=sum(q.get('usage',{}).get('prompt_tokens',0) for q in qq),
        output_tokens=sum(q.get('usage',{}).get('completion_tokens',0) for q in qq),elapsed_seconds=time.time()-began,
        injection_decisions=len({r['step'] for r in provider.records.values() if r['injected']}),independent_parent_episodes=1)
    write(out/'summary.json',result);print(json.dumps(result),flush=True);return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--id',choices=CASES,required=True);a=p.parse_args();execute(a.id)
