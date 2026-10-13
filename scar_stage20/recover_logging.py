"""Offline preparation only: recover lost first-step evidence, never resume runs.

Requires exact initial/action/feedback/final-hash agreement with the original
terminal record. Original summaries and empty archives remain untouched.
"""
import copy
import difflib
import importlib.util
import json
from pathlib import Path
import tempfile
from .common import ROOT,RESULTS,REPORTS,load,write,sha,read_gzip,gzip_rows,deny_network
from .agent import make_method
from .controller import Controller20
from .tests.test_mechanisms import CaptureProvider
from .run_errors import MethodStalled
from scar_stage17.environment import create_initial
from scar_stage17.evaluate import physical,native_step,transition
from scar_stage14.knowledge import Knowledge
from scar.environment import AGENT_ID,state_digest,snapshot,restore
from scar.io import digest


def main():
    deny_network()
    frozen=load(RESULTS/'freeze.json')
    assert all(sha(ROOT/p)==v for p,v in frozen['files'].items())
    original=(ROOT/'scar_stage20/run.py').read_text()
    assert original.count('agent.controller.outcome19')==1
    corrected=original.replace('agent.controller.outcome19','agent.controller.outcome20')
    patch=''.join(difflib.unified_diff(original.splitlines(True),corrected.splitlines(True),
        fromfile='a/scar_stage20/run.py',tofile='b/scar_stage20/run.py'))
    (REPORTS/'日志归档修复补丁.diff').write_text(patch)
    prepared=ROOT/'runtime/stage20/recovery_prepared';prepared.mkdir(exist_ok=True)
    recovery=RESULTS/'startup_recovery';recovery.mkdir(exist_ok=True)
    records=[]
    histories={r['task_id']:r['history'] for r in read_gzip(RESULTS/'initial_public_histories.jsonl.gz')}
    tasks=load(RESULTS/'tasks.json')
    for task in tasks:
        tid=task['task_id'];folder=RESULTS/'runs'/f'{tid}__SCAR20';summary=load(folder/'summary.json')
        assert summary['steps']==0 and summary['error']=="AttributeError: 'Controller20' object has no attribute 'outcome19'"
        assert not read_gzip(folder/'trajectory.jsonl.gz') and not read_gzip(folder/'requests.jsonl.gz')
        terminal=load(folder/'terminal_decision.json');decision=terminal['decision'];action=decision['decision']['executed_action']
        assert action and decision['controller']['step16']==1
        with tempfile.TemporaryDirectory(prefix='scar20-recover-') as directory:
            root=Path(directory);env,history=create_initial(task['game_name'],task['initial_seed'],root/'initial')
            assert state_digest(env)==task['initial_state_hash'] and digest(history)==task['initial_public_history_hash']
            target=env.world.auxiliary['obj_name_to_id'][task['target_item']]
            crafted0=copy.deepcopy(env.curr_agents_state['objects_crafted'][AGENT_ID])
            obs=copy.deepcopy(env.obs[AGENT_ID]);before=physical(env,target)
            (out,reward,done,info),effect=native_step(env,action,target);env.update_scores(reward)
            afterobs=out[AGENT_ID];after=physical(env,target)
            assert afterobs==terminal['public_observation'] and state_digest(env)==summary['final_state_hash']
            knowledge=Knowledge()
            for h in history:knowledge.observe(h['after'],h['action'],cutoff=h['after']['step'])
            knowledge.observe(obs,None,cutoff=obs['step']);prior=knowledge.view()
            delta=knowledge.observe(afterobs,action,cutoff=afterobs['step'],source={'evaluation_step':1})
            metrics=transition(before,after,action,afterobs,env.world)
            metrics['engine_invalid_flag']=bool(info.get('step_invalid_action',{}).get(AGENT_ID,False))
            metrics['invalid']=metrics['invalid'] or metrics['engine_invalid_flag']
            if effect:
                eb,ea=effect['before'],effect['after']
                metrics['action_only_consumption']={o:n-ea['possessed'].get(o,0) for o,n in eb['possessed'].items() if n>ea['possessed'].get(o,0)+1e-8} if metrics['craft'] else {}
            metrics['unaccounted_resource_loss']={o:n-metrics.get('action_only_consumption',{}).get(o,0) for o,n in metrics['actual_world_quantity_decrease'].items() if n>metrics.get('action_only_consumption',{}).get(o,0)+1e-8}
            produced=after['crafted'].get(target,0)-crafted0.get(target,0)
            row=dict(task_id=tid,game_name=task['game_name'],method='SCAR20',step=1,seed=task['initial_seed'],
                goal=task['objective_text'],observation=obs,action=action,feedback=afterobs,done=bool(done),
                death=bool(getattr(reward[AGENT_ID],'death',0)),reward={k:vars(v) for k,v in reward.items()},info=info,
                state_hash=after['state_hash'],physical_before=before,physical_after=after,
                # Decision.controller was exported after observe in the terminal
                # record, so recover the actual before-action version from the
                # saved decision and replay the same deterministic choose only.
                decision=None,mechanism_outcome=copy.deepcopy(decision['controller']['outcome20']),
                public_knowledge_before=prior,public_knowledge_after=knowledge.view(),knowledge_delta=delta,
                ambiguous_public_evidence=copy.deepcopy(knowledge.ambiguous),metrics=metrics,
                target_produced_during_task=produced,success=after['target_owned']>=1 and produced>=1,
                recovered_from_terminal=True,recovery_scope='exact deterministic replay, no new policy sample or API call')
            c=Controller20.from_dict(decision['decision']['controller_before'])
            assert c.choose(obs)==action
            before_controller=c.to_dict()
            c.observe(obs,action,afterobs);c.events.clear()
            assert c.to_dict()==decision['controller']
            row['decision']=dict(decision=decision['decision'],controller=before_controller,memory=decision['memory'])
            gzip_rows(recovery/(tid+'.jsonl.gz'),[row])
            provider=CaptureProvider(fail=True)
            agent=make_method('SCAR20',task['game_name'],provider,task['objective_text'],task['target_item'],history,root/'agent')
            agent.facts.observe(obs,action,afterobs)
            agent.controller=Controller20.from_dict(decision['controller']);agent.short_term_memory=copy.deepcopy(decision['memory'])
            cp=prepared/tid/'checkpoint-001';cp.mkdir(parents=True,exist_ok=True);agent.save_memory(cp)
            (cp/'physical.pkl').write_bytes(snapshot(env))
            write(cp/'meta.json',dict(step=1,knowledge=knowledge.to_dict(),initial_crafted=crafted0,state_hash=state_digest(env)))
            restored=restore(cp/'physical.pkl',root/'restored',agent=agent)
            assert state_digest(restored)==summary['final_state_hash']
            records.append(dict(task_id=tid,action=action,actual_actions_before_failure=1,recorded_actions_before_recovery=0,
                final_hash=summary['final_state_hash'],public_feedback_exact=True,controller_state_exact=True,
                prepared_checkpoint=str(cp.relative_to(ROOT)),recovered_row=str((recovery/(tid+'.jsonl.gz')).relative_to(ROOT)),
                new_api_calls=0,formal_run_resumed=False))
    # Exercise the proposed one-field patch through the full runner in isolated
    # output directories, allowing one known action then an explicit fixture stop.
    spec=importlib.util.spec_from_loader('scar_stage20.proposed_runner',loader=None)
    module=importlib.util.module_from_spec(spec);exec(compile(corrected,'proposed_run.py','exec'),module.__dict__)
    checks=[]
    for task in (tasks[0],tasks[15]):
        with tempfile.TemporaryDirectory(prefix='scar20-log-review-') as directory:
            root=Path(directory);module.RESULTS=root/'results';module.RESULTS.mkdir()
            (module.RESULTS/'initial_public_histories.jsonl.gz').write_bytes((RESULTS/'initial_public_histories.jsonl.gz').read_bytes())
            class NoAPI(CaptureProvider):
                def __init__(self,*args,**kwargs):super().__init__(fail=True)
                def begin_step(self,step):pass
            module.SharedDeepSeekProvider=NoAPI
            factory=make_method
            def one_step(*args,**kwargs):
                agent=factory(*args,**kwargs);real_act=agent.act;count=[0]
                def act(obs):
                    if count[0]:
                        agent.decision=dict(executed_action=None,planning_calls=[])
                        raise MethodStalled('offline one-step archive test fixture')
                    count[0]+=1;return real_act(obs)
                agent.act=act;return agent
            module.make_method=one_step
            result=module.execute(task,'SCAR20',root/'runtime',root/'unused-key')
            assert result['status']=='method_stalled' and result['steps']==1
            archive=module.RESULTS/'runs'/f"{task['task_id']}__SCAR20"
            assert len(read_gzip(archive/'trajectory.jsonl.gz'))==1 and not read_gzip(archive/'requests.jsonl.gz')
            checks.append(dict(game=task['game_name'],full_runner_one_step_archive_passed=True,api_calls=0))
    assert all(sha(ROOT/p)==v for p,v in frozen['files'].items())
    write(RESULTS/'logging_recovery_review.json',dict(passed=True,policy_and_frozen_runner_unchanged=True,
        original_failures_preserved=24,actual_actions_recovered=24,new_api_calls=0,formal_runs_resumed=0,
        proposed_change='one logging attribute outcome19 -> outcome20; no action policy, prompt or model protocol changes',
        patched_runner_checks=checks,runs=records,approval_required_for_continuation=True))
    print('Prepared and verified 24 exact first-step recovery points; proposed logger tested; no formal continuation')


if __name__=='__main__':main()
