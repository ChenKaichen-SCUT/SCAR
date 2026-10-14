"""Frozen 300-absolute-step paired continuations; never resample a failure."""
import argparse
import contextlib
import copy
import io
import shutil
import time
import traceback
from .common import *
from .reset import ResetGate,attach
from .provider import PairedProvider
from scar.io import append_jsonl,digest


def checkpoint(folder,env,agent,gate):
    from scar.environment import snapshot,state_digest
    temp=folder/f'.checkpoint-{env.steps:03d}';dest=folder/f'checkpoint-{env.steps:03d}'
    if temp.exists():shutil.rmtree(temp)
    temp.mkdir();agent.save_memory(temp)
    (temp/'physical.pkl').write_bytes(snapshot(env));write(temp/'gate.json',gate.__dict__)
    write(temp/'meta.json',dict(step=env.steps,state_hash=state_digest(env)))
    temp.rename(dest);write(folder/'latest.json',dict(checkpoint=dest.name))
    for p in folder.glob('checkpoint-*'):
        if p!=dest:shutil.rmtree(p)


def save_origin(start,original):
    output=RESULTS/'runs'/case_id(start)/'Stage18-Origin'
    if (output/'summary.json').exists():return read(output/'summary.json')
    rr=original[start-1:]
    data=[]
    for r in rr:
        data.append(dict(step=r['step'],action=r['action'],observation=r['observation'],feedback=r['feedback'],
            reward=r['reward'],scores=r['scores'],main_quest_progress=r['main_quest_progress'],done=r['done'],
            state_hash_before=r['state_hash_before'],state_hash=r['state_hash'],invalid_action=r['invalid_action'],
            decision_reference=f'results/stage22/runs/mark__Stage18-Fixed/trajectory.jsonl.gz:{r["step"]}',
            proposal=r['decision']['proposed_action'],intercepted=r['decision']['intercepted'],
            goal=r['decision']['controller_before']['target'],reset_active=False,
            request_reference=f'results/stage22/runs/mark__Stage18-Fixed/requests.jsonl.gz:{r["step"]}'))
    gzwrite(output/'trajectory.jsonl.gz',data)
    summary=dict(case=case_id(start),variant='Stage18-Origin',start=start,steps=len(rr),last_step=300,
        status='reused_original_suffix',scores=rr[-1]['scores'],main_quest_progress=rr[-1]['main_quest_progress'],
        new_model_requests=0,new_model_cost_usd=0,reset_events=[],independent_parent_episodes=1,
        provenance='Exact original source suffix; 300-step native source replay and 10 checkpoint hashes verified before Stage23.')
    write(output/'summary.json',summary);return summary


def execute(start,variant,key):
    from scar.environment import restore,state_digest
    from scar_stage22.integration import make_agent
    check_freeze()
    case=case_id(start);folder=RUNTIME/'runs'/case/variant;output=RESULTS/'runs'/case/variant
    if (output/'summary.json').exists():return read(output/'summary.json')
    folder.mkdir(parents=True,exist_ok=True);(folder/'steps').mkdir(exist_ok=True)
    cp=RESULTS/'checkpoints'/case;original=rows(SOURCE/'trajectory.jsonl.gz')
    provider=PairedProvider(folder,RUNTIME/'runs'/case,key,variant)
    with contextlib.redirect_stdout(io.StringIO()):agent=make_agent('Stage18-Fixed','mark',provider,folder/'memory')
    gate=ResetGate(variant,start,original[:start-1]);started=time.time();error=None
    try:
        if (folder/'latest.json').exists():
            saved=folder/read(folder/'latest.json')['checkpoint']
            with contextlib.redirect_stdout(io.StringIO()):agent.load_memory(saved)
            env=restore(saved/'physical.pkl',folder,agent)
            gate.__dict__.update(read(saved/'gate.json'))
            for name in ['identity','released']:
                if gate.__dict__[name] is not None:gate.__dict__[name]=tuple(gate.__dict__[name])
            assert state_digest(env)==read(saved/'meta.json')['state_hash']
        else:
            with contextlib.redirect_stdout(io.StringIO()):agent.load_memory(cp)
            env=restore(gzip.decompress((cp/'physical.pkl.gz').read_bytes()),folder,agent)
            assert env.steps==start-1 and state_digest(env)==read(cp/'meta.json')['state_hash']
            checkpoint(folder,env,agent,gate)
        attach(agent,variant)
        while env.steps<MAX_STEPS:
            n=env.steps+1;before=copy.deepcopy(env.obs[AGENT]);before_hash=state_digest(env)
            reset_event=gate.before(n,agent.controller,before)
            provider.begin_step(n,before_hash);attach(agent,variant)
            memory_before=copy.deepcopy(agent.short_term_memory);facts_before=agent.facts.to_dict()
            with gate.enabled(),contextlib.redirect_stdout(io.StringIO()):action,tin,tout,response=agent.act(before)
            decision=copy.deepcopy(agent.decision)
            with contextlib.redirect_stdout(io.StringIO()):obs,reward,done,info=env.step({AGENT:action});env.update_scores(reward)
            after=copy.deepcopy(obs[AGENT])
            row=dict(case=case,variant=variant,step=n,continuation_step=n-start+1,observation=before,
                action=action,feedback=after,reward=vars(reward[AGENT]),scores=copy.deepcopy(env.scores[AGENT]),
                done=bool(done),info=info,invalid_action=bool(info.get('step_invalid_action',{}).get(AGENT,False)),
                state_hash_before=before_hash,state_hash=state_digest(env),decision=decision,
                proposal=decision['proposed_action'],intercepted=decision['intercepted'],
                goal=decision['controller_before']['target'],reset=reset_event,
                main_quest_progress=copy.deepcopy(env.curr_agents_state.get('main_quest_progress',{}).get(AGENT)),
                memory_before=memory_before,facts_before=facts_before,response=response,
                request_id=provider.last['request_id'],sample_origin=provider.last['sample_origin'],
                request_signature=provider.last['signature'],new_cost_usd=provider.last['incremental_cost_usd'],
                input_tokens=tin,output_tokens=tout)
            dest=folder/'steps'/f'{n:03d}.json'
            if dest.exists():
                saved=read(dest)
                for k in ['action','state_hash','state_hash_before','observation','feedback','request_signature']:
                    assert saved[k]==row[k],('resume divergent',n,k)
            else:write(dest,row)
            agent.observe_transition(before,action,after)
            gate.observe(action,after,decision['controller_before'])
            checkpoint(folder,env,agent,gate)
            write(folder/'progress.json',dict(step=n,remaining=300-n,scores=row['scores'],reset_events=gate.events,
                new_model_requests=sum(r['sample_origin']=='new-model-request' for r in provider.calls.values()),
                new_cost_usd=sum(r['incremental_cost_usd'] for r in provider.calls.values()),updated=time.time()))
            if done:break
        status='native_done' if env.steps and read(folder/'steps'/f'{env.steps:03d}.json')['done'] else 'step_limit'
    except Exception as exc:
        status='infrastructure_error';error=dict(type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc())
        print(error['traceback'],flush=True)
    output.mkdir(parents=True,exist_ok=True)
    trajectory=[read(p) for p in sorted((folder/'steps').glob('*.json'))]
    calls=sorted(provider.calls.values(),key=lambda r:r['step'])
    gzwrite(output/'trajectory.jsonl.gz',trajectory);gzwrite(output/'requests.jsonl.gz',calls)
    paid_path=folder/'paid/requests.jsonl'
    paid=[json.loads(s) for s in paid_path.read_text().splitlines()] if paid_path.exists() else []
    gzwrite(output/'paid_requests.jsonl.gz',paid)
    summary=dict(case=case,variant=variant,start=start,status=status,error=error,steps=len(trajectory),
        last_step=trajectory[-1]['step'] if trajectory else start-1,
        scores=trajectory[-1]['scores'] if trajectory else original[start-2]['scores'],
        main_quest_progress=trajectory[-1]['main_quest_progress'] if trajectory else original[start-2]['main_quest_progress'],
        reset_events=gate.events,logical_model_decisions=len(calls),
        new_model_requests=len(paid),new_model_cost_usd=sum(r.get('cost_usd',0) for r in paid),
        charged_or_reserved_usd=sum(r.get('charged_or_reserved_usd',0) for r in paid),
        source_reuses=sum(r['sample_origin']=='Stage22-original' for r in calls),
        paired_reuses=sum(r['sample_origin']=='paired-identical-state-and-input' for r in calls),
        input_tokens_new=sum(r.get('usage',{}).get('prompt_tokens',0) for r in paid),
        output_tokens_new=sum(r.get('usage',{}).get('completion_tokens',0) for r in paid),
        elapsed_seconds=time.time()-started,independent_parent_episodes=1)
    write(output/'summary.json',summary)
    # Final agent memory is diagnostic evidence; native terminal snapshot stays
    # in the local runtime, original fork snapshots are archived in results.
    agent.save_memory(output/'final_memory')
    return summary


def main():
    p=argparse.ArgumentParser();p.add_argument('--start',type=int,choices=CASES,required=True)
    p.add_argument('--key',default=str(ROOT.parent/'miyao.txt'));args=p.parse_args()
    original=rows(SOURCE/'trajectory.jsonl.gz');out=[save_origin(args.start,original)]
    for variant in VARIANTS[1:]:
        result=execute(args.start,variant,args.key);out.append(result)
        print(json.dumps({k:result[k] for k in ['case','variant','status','steps','scores','new_model_requests','new_model_cost_usd']}),flush=True)
        if result['status']=='infrastructure_error':break
    write(RESULTS/'case_completion'/f'{case_id(args.start)}.json',dict(runs=out,complete=len(out)==3 and all(r['status']!='infrastructure_error' for r in out)))


if __name__=='__main__':main()
