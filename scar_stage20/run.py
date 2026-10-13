"""One isolated process per paired run; atomic step checkpoints and paid-call cache."""
import argparse
import copy
import gzip
import json
import os
import shutil
import time
import traceback
from pathlib import Path
from scar.environment import restore,snapshot,state_digest,AGENT_ID
from scar.io import digest
from scar_stage14.knowledge import Knowledge
from scar.providers.deepseek import BudgetExceeded,ModelResponseError
from scar.agents.scar.state import feedback_text
from .common import ROOT,RESULTS,load,write,gzip_rows,read_gzip,sha
from scar_stage17.environment import create_initial
from .agent import make_method,decision_state
from .config import PROVIDER
from .provider import SharedDeepSeekProvider,UncertainRequest
from .run_errors import MethodStalled
from scar_stage17.evaluate import physical,transition,native_step


def check_freeze():
    freeze=load(RESULTS/'freeze.json')
    for name,value in freeze['files'].items():
        if sha(ROOT/name)!=value:raise ValueError('Frozen file differs: '+name)
    return freeze


def checkpoint(folder,env,agent,knowledge,step,initial_crafted):
    dest=folder/f'checkpoint-{step:03d}';temp=folder/f'.checkpoint-{step:03d}'
    if temp.exists():shutil.rmtree(temp)
    temp.mkdir();agent.save_memory(str(temp));(temp/'physical.pkl').write_bytes(snapshot(env))
    write(temp/'meta.json',dict(step=step,knowledge=knowledge.to_dict(),initial_crafted=initial_crafted,state_hash=state_digest(env)))
    if dest.exists():shutil.rmtree(dest)
    temp.rename(dest);write(folder/'latest.json',dict(checkpoint=dest.name))
    for other in folder.glob('checkpoint-*'):
        if other!=dest:shutil.rmtree(other)


def export_run(folder,output,summary):
    rows=[read_gzip(p)[0] for p in sorted((folder/'steps').glob('*.jsonl.gz'))]
    summary['steps']=len(rows)
    if rows:
        summary['final_state_hash']=rows[-1]['state_hash']
        summary['success']=rows[-1]['success']
    gzip_rows(output/'trajectory.jsonl.gz',rows)
    if (folder/'requests.jsonl').exists():
        requests=[json.loads(s) for s in (folder/'requests.jsonl').read_text().splitlines()]
    else:requests=[]
    gzip_rows(output/'requests.jsonl.gz',requests)
    gzip_rows(output/'normalization_events.jsonl.gz',[dict(request_id=q['request_id'],step=q['step'],
        events=q['normalization_events']) for q in requests if q.get('normalization_events')])
    gzip_rows(output/'recovery.jsonl.gz',[dict(step=r['step'],action=r['action'],
        planning_calls=r['decision']['decision']['planning_calls'],recovery=r['mechanism_outcome']['recovery'],
        lifecycle=r['mechanism_outcome']['lifecycle']) for r in rows])
    gzip_rows(output/'subgoals.jsonl.gz', [dict(step=r['step'], action=r['action'],
        decision=r['decision']['decision'], outcome=r['mechanism_outcome']) for r in rows])
    gzip_rows(output/'preconditions.jsonl.gz', [dict(step=r['step'], action=r['action'],
        public_knowledge=r['public_knowledge_after'], prerequisites=r['mechanism_outcome']['preconditions'],
        feedback=r['feedback']) for r in rows])
    if (folder/'terminal_decision.json').exists():shutil.copyfile(folder/'terminal_decision.json',output/'terminal_decision.json')
    write(output/'summary.json',summary)


def execute(task,method,runtime,key_path):
    folder=Path(runtime)/'runs'/f"{task['task_id']}__{method}";folder.mkdir(parents=True,exist_ok=True)
    output=RESULTS/'runs'/folder.name;output.mkdir(parents=True,exist_ok=True)
    if (output/'summary.json').exists():return load(output/'summary.json')
    (folder/'steps').mkdir(exist_ok=True)
    start=time.time();step=0;status='method_exception';error=None;phase='setup';env=None;success=False
    try:
        assert method=='SCAR20'
        provider=SharedDeepSeekProvider(folder,Path(runtime)/'budget.sqlite',key_path,config=PROVIDER)
        public=next(r for r in read_gzip(RESULTS/'initial_public_histories.jsonl.gz') if r['task_id']==task['task_id'])
        agent=make_method(method,task['game_name'],provider,task['objective_text'],task['target_item'],public['history'],folder/'memory')
        saved=folder/'latest.json';target='';knowledge=Knowledge()
        if saved.exists():
            cp=folder/load(saved)['checkpoint'];meta=load(cp/'meta.json');step=meta['step']
            agent.load_memory(str(cp))
            env=restore(cp/'physical.pkl',folder/'world',agent=agent)
            assert state_digest(env)==meta['state_hash']
            knowledge=Knowledge.from_dict(meta['knowledge']);initial_crafted=meta['initial_crafted']
        else:
            phase='environment'
            if (folder/'initial').exists():shutil.rmtree(folder/'initial')
            fresh,history=create_initial(task['game_name'],task['initial_seed'],folder/'initial')
            assert state_digest(fresh)==task['initial_state_hash'] and digest(history)==task['initial_public_history_hash']
            env=restore(snapshot(fresh),folder/'world',agent=agent)
            assert state_digest(env)==task['initial_state_hash']
            for h in history:knowledge.observe(h['after'],h['action'],cutoff=h['after']['step'])
            knowledge.observe(env.obs[AGENT_ID],None,cutoff=env.obs[AGENT_ID]['step'])
            initial_crafted=copy.deepcopy(env.curr_agents_state['objects_crafted'][AGENT_ID])
            checkpoint(folder,env,agent,knowledge,0,initial_crafted)
        target=env.world.auxiliary['obj_name_to_id'][task['target_item']]
        # A committed post-step checkpoint can precede final export during a crash.
        if step:
            last=read_gzip(folder/'steps'/f'{step:03d}.jsonl.gz')[0]
            success=last['success'];status='success' if success else 'game_failure' if last['done'] or last.get('death',False) or last['physical_after']['health']<=0 else 'step_limit'
            if success or status=='game_failure' or step==100:
                summary=dict(task_id=task['task_id'],method=method,status=status,success=success,steps=step,error=None,
                    initial_state_hash=task['initial_state_hash'],final_state_hash=state_digest(env),started=start,finished=time.time())
                export_run(folder,output,summary);return summary
        for index in range(step+1,101):
            phase='method';obs=copy.deepcopy(env.obs[AGENT_ID]);before=physical(env,target)
            if provider:provider.begin_step(index)
            knowledge_before=knowledge.view()
            action,tin,tout,response=agent.act(obs)
            decision=decision_state(agent,method)
            phase='environment'
            (allobs,reward,done,info),effect=native_step(env,action,target)
            env.update_scores(reward);afterobs=copy.deepcopy(allobs[AGENT_ID]);after=physical(env,target)
            scores=transition(before,after,action,afterobs,env.world)
            scores['engine_invalid_flag']=bool(info.get('step_invalid_action',{}).get(AGENT_ID,False))
            scores['invalid']=scores['invalid'] or scores['engine_invalid_flag']
            if effect:
                eb,ea=effect['before'],effect['after']
                scores['action_only_consumption']={o:n-ea['possessed'].get(o,0) for o,n in eb['possessed'].items() if n>ea['possessed'].get(o,0)+1e-8} if scores['craft'] else {}
            scores['unaccounted_resource_loss']={o:n-scores.get('action_only_consumption',{}).get(o,0) for o,n in scores['actual_world_quantity_decrease'].items() if n>scores.get('action_only_consumption',{}).get(o,0)+1e-8}
            phase='observation'
            observe_error=None
            try:
                if hasattr(agent,'observe_transition'):agent.observe_transition(obs,action,afterobs)
            except Exception as exc:observe_error=type(exc).__name__+': '+str(exc)
            delta=knowledge.observe(afterobs,action,cutoff=afterobs['step'],source={'evaluation_step':index})
            death=bool(getattr(reward[AGENT_ID],'death',0))
            produced=after['crafted'].get(target,0)-initial_crafted.get(target,0)
            success=after['target_owned']>=task['target_amount'] and produced>=task['target_amount']
            row=dict(task_id=task['task_id'],game_name=task['game_name'],method=method,step=index,seed=task['initial_seed'],
                goal=task['objective_text'],observation=obs,action=action,feedback=afterobs,done=bool(done),death=death,
                reward={k:vars(v) for k,v in reward.items()},info=info,state_hash=after['state_hash'],
                physical_before=before,physical_after=after,decision=decision,
                mechanism_outcome=copy.deepcopy(agent.controller.outcome20),
                public_knowledge_before=knowledge_before,public_knowledge_after=knowledge.view(),knowledge_delta=delta,
                ambiguous_public_evidence=copy.deepcopy(knowledge.ambiguous),metrics=scores,
                target_produced_during_task=produced,success=success,recorded=time.time())
            gzip_rows(folder/'steps'/f'{index:03d}.jsonl.gz',[row])
            step=index
            if observe_error:
                status='method_exception';error=observe_error;break
            checkpoint(folder,env,agent,knowledge,index,initial_crafted)
            write(folder/'progress.json',dict(task_id=task['task_id'],method=method,steps=step,updated=time.time()))
            if success:status='success';break
            if done or death or after['health']<=0:status='game_failure';break
        else:status='step_limit'
    except MethodStalled as exc:
        status='method_stalled';error=str(exc)
        write(folder/'terminal_decision.json',dict(step=step+1,decision=decision_state(agent,method),public_observation=env.obs[AGENT_ID],status=status))
        checkpoint(folder,env,agent,knowledge,step,initial_crafted)
    except BudgetExceeded as exc:status='api_budget_abort';error=str(exc)
    except ModelResponseError as exc:status='model_parse_exception';error=str(exc)
    except UncertainRequest as exc:status='api_uncertain_abort';error=str(exc)
    except Exception as exc:
        status='environment_exception' if phase=='environment' else 'method_exception'
        error=type(exc).__name__+': '+str(exc)
        # SDK error strings are not saved: they can contain request metadata.
        if phase in ('method','setup') and ('API' in type(exc).__name__ or 'API rejected' in str(exc)):error=type(exc).__name__+': API request failure; see audit'
        (folder/'exception.txt').write_text(traceback.format_exc() if 'API' not in type(exc).__name__ else error)
    if env is not None and 'agent' in locals():
        write(folder/'terminal_decision.json',dict(step=step+1,decision=decision_state(agent,method),
            public_observation=env.obs[AGENT_ID],status=status,
            decision_scope='last selected action or stalled choice; check executed_action and status'))
    summary=dict(task_id=task['task_id'],method=method,status=status,success=success,steps=step,error=error,
        initial_state_hash=task['initial_state_hash'],final_state_hash=state_digest(env) if env else None,started=start,finished=time.time())
    export_run(folder,output,summary);return summary


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--task',required=True);parser.add_argument('--method',required=True)
    parser.add_argument('--runtime',required=True);parser.add_argument('--key-path',default=str(ROOT.parent/'miyao.txt'));args=parser.parse_args()
    check_freeze();task=next(t for t in load(RESULTS/'tasks.json') if t['task_id']==args.task)
    print(json.dumps(execute(task,args.method,args.runtime,args.key_path)),flush=True)

if __name__=='__main__':main()
