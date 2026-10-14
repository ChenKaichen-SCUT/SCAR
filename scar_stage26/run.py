"""One predeclared native action intervention; unchanged AGC-v2 afterwards."""
import argparse
import contextlib
import copy
import io
import shutil
import time
import traceback
from .common import *
from .provider import BranchProvider
from scar_stage25.integration import make_agent
from scar_stage22.run import checkpoint

def save_origin(start):
    rr=rows(SOURCE/'trajectory.jsonl.gz');suffix=rr[start-1:];out=RESULTS/'runs'/case_id(start)/'Original'
    write(out/'summary.json',dict(case=case_id(start),variant='Original',start=start,steps=len(suffix),last_step=300,status='reused_original_suffix',
        scores=suffix[-1]['scores'],main_quest_progress=suffix[-1]['main_quest_progress'],new_model_calls=0,cost_usd=0,
        source_trajectory='results/stage25/runs/remnant__s42__AGC-v2/trajectory.jsonl.gz',source_lines=[start,300],independent_parent_episodes=1))

def execute(start,key):
    from scar.environment import restore,state_digest
    from scar.io import digest
    from agents.agc.agent import DecisionUnavailable
    check_freeze();folder=RUNTIME/'runs'/case_id(start);out=RESULTS/'runs'/case_id(start)/'Oracle'
    if (out/'summary.json').exists():return read(out/'summary.json')
    folder.mkdir(parents=True,exist_ok=True);(folder/'steps').mkdir(exist_ok=True)
    provider=BranchProvider(folder,start,key)
    with contextlib.redirect_stdout(io.StringIO()):agent=make_agent('remnant',42,provider,folder/'memory')
    cp=RESULTS/'checkpoints'/case_id(start);source=rows(SOURCE/'trajectory.jsonl.gz');began=time.time();error=None;status='infrastructure_error'
    if (folder/'latest.json').exists():
        saved=folder/read(folder/'latest.json')['checkpoint']
        with contextlib.redirect_stdout(io.StringIO()):agent.load_memory(saved)
        env=restore(saved/'physical.pkl',folder,agent);assert state_digest(env)==read(saved/'meta.json')['state_hash']
    else:
        with contextlib.redirect_stdout(io.StringIO()):agent.load_memory(cp)
        env=restore(gzip.decompress((cp/'physical.pkl.gz').read_bytes()),folder,agent)
        assert env.steps==start-1 and state_digest(env)==read(cp/'meta.json')['state_hash']
        checkpoint(folder,env,agent)
    env.config.update(game_name='remnant',seed=42,max_steps=MAX_STEPS,agent='Stage25-AGC-v2',stage26_oracle_diagnostic=True);env.update_config()
    done=bool(env.steps>=start and read(folder/'steps'/f'{env.steps:03d}.json')['done'])
    try:
        while env.steps<MAX_STEPS and not done:
            n=env.steps+1;provider.begin_step(n);before=copy.deepcopy(env.obs[AGENT_ID]);before_hash=state_digest(env)
            memory_before=copy.deepcopy(agent.short_term_memory)
            with contextlib.redirect_stdout(io.StringIO()):proposed,tin,tout,response=agent.act(before)
            decision=copy.deepcopy(agent.decision);memory_after_act=digest(agent.short_term_memory);goal_after_act=digest(agent.control.to_dict())
            action=CASES[start]['action'] if n==start else proposed
            if n==start:
                expected=read(cp/'post_decision.json')
                assert proposed==source[n-1]['action'] and digest(decision)==digest(expected['decision'])
                assert agent.short_term_memory==expected['memory'] and agent.control.to_dict()==expected['control']
            # Exact treatment: change only the native action string, leave the
            # frozen model's just-written STM entry and goal state untouched.
            assert digest(agent.short_term_memory)==memory_after_act and digest(agent.control.to_dict())==goal_after_act
            with contextlib.redirect_stdout(io.StringIO()):obs,reward,done,info=env.step({AGENT_ID:action});env.update_scores(reward)
            after=copy.deepcopy(obs[AGENT_ID]);agent.observe_transition(before,action,after)
            row=dict(case=case_id(start),variant='Oracle',step=n,continuation_step=n-start+1,observation=before,feedback=after,
                action=action,proposed_action=proposed,oracle_replacement=n==start,decision=decision,response=response,
                reward=vars(reward[AGENT_ID]),scores=copy.deepcopy(env.scores[AGENT_ID]),done=bool(done),info=info,
                invalid_action=bool(info.get('step_invalid_action',{}).get(AGENT_ID,False)),state_hash_before=before_hash,state_hash=state_digest(env),
                memory_before=memory_before,memory_after_act_hash=memory_after_act,goal_after_act_hash=goal_after_act,
                control_after=copy.deepcopy(agent.control.to_dict()),transition=copy.deepcopy(agent.transition),input_tokens=tin,output_tokens=tout,
                main_quest_progress=copy.deepcopy(env.curr_agents_state.get('main_quest_progress',{}).get(AGENT_ID)))
            if n==start:
                probe=read(cp/'oracle_probe.json');assert row['state_hash']==probe['state_hash'] and after==probe['feedback']
            dest=folder/'steps'/f'{n:03d}.json'
            if dest.exists():assert read(dest)==row,'Resume diverged; stop without resampling.'
            else:write(dest,row)
            agent.control.events.clear();checkpoint(folder,env,agent);env.update_config()
            write(folder/'progress.json',dict(case=case_id(start),step=n,remaining=MAX_STEPS-n,scores=row['scores'],
                new_requests=len(provider.paid.cache),cost_usd=provider.paid.episode.total(),updated=time.time()))
        status='native_done' if done else 'step_limit'
    except DecisionUnavailable as exc:
        status='agent_decision_exhausted';error=str(exc)
        write(folder/'decision_exhausted.json',dict(step=env.steps+1,decision=agent.decision,observation=env.obs[AGENT_ID]))
    except Exception as exc:
        error=dict(type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc());print(error['traceback'],flush=True)
    env.update_config();out.mkdir(parents=True,exist_ok=True)
    rr=[read(p) for p in sorted((folder/'steps').glob('*.json'))]
    qq=[json.loads(s) for s in provider.paid.audit.read_text().splitlines()] if provider.paid.audit.exists() else []
    gzwrite(out/'trajectory.jsonl.gz',rr);gzwrite(out/'requests.jsonl.gz',qq);gzwrite(out/'source_reuse.jsonl.gz',list(provider.reuses.values()))
    agent.save_memory(out/'final_memory')
    for name in ['config.json','decision_exhausted.json']:
        if (folder/name).exists():shutil.copyfile(folder/name,out/name)
    result=dict(case=case_id(start),variant='Oracle',start=start,status=status,error=error,steps=len(rr),last_step=env.steps,max_absolute_step=MAX_STEPS,
        scores=env.scores[AGENT_ID],main_quest_progress=copy.deepcopy(env.curr_agents_state.get('main_quest_progress',{}).get(AGENT_ID)),
        new_requests=len(qq),source_requests_reused=len(provider.reuses),input_tokens=sum(q.get('usage',{}).get('prompt_tokens',0) for q in qq),
        output_tokens=sum(q.get('usage',{}).get('completion_tokens',0) for q in qq),cost_usd=sum(q.get('cost_usd',0) for q in qq),
        charged_or_reserved_usd=sum(q['charged_or_reserved_usd'] for q in qq),elapsed_seconds=time.time()-began,
        intervention_count=sum(r['oracle_replacement'] for r in rr),independent_parent_episodes=1)
    write(out/'summary.json',result);print(json.dumps(result),flush=True);return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--start',type=int,choices=CASES,required=True);p.add_argument('--key',default=str(ROOT.parent/'miyao.txt'))
    args=p.parse_args();save_origin(args.start);execute(args.start,args.key)
