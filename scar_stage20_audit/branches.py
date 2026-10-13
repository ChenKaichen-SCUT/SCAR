"""Bounded native one-step branches selected using public data before outcomes."""
from .common import *
deny_network()
import tempfile
from collections import defaultdict
from scar.environment import restore,snapshot,state_digest,AGENT_ID
from scar_stage17.environment import create_initial
from scar_stage17.evaluate import physical
from scar_stage14.knowledge import Knowledge
from scar.agents.scar.repair import valid_syntax
from scar_v3.state import parse_action,PublicState


def hp(obs):
    match=__import__('re').search(r'My health is at ([\d.]+)',obs['text'])
    return float(match[1]) if match else None


def select():
    stalls=read_gzip(RESULTS/'terminal_states.jsonl.gz');plans=read_gzip(RESULTS/'planning_states.jsonl.gz');selected=[]
    for s in stalls:
        eligible=[r for r in s['candidates'] if r['eligible_public_trial'] and r['possible_new_knowledge']]
        inspect=sorted((r for r in eligible if r['action'].startswith('inspect ')),key=lambda r:(not r['public_blocker_related'],r['action']))[:3]
        move=sorted((r for r in eligible if r['action'].startswith('enter ')),key=lambda r:(not bool(r['route_witnesses']),r['action']))
        for r in inspect+move[:4-len(inspect)]:
            selected.append(dict(id=f"{s['task_id']}:terminal:{len(selected):03d}",task_id=s['task_id'],at_completed_step=s['terminal_step'],
                action=r['action'],state_hash=s['physical_state_hash'],source='terminal_public_candidate',
                selection='up to 3 novel public inspections, then public-route moves; max4/task; public-related then lexical',
                candidate=r,checkpoint=s['checkpoint']))
    # Three structurally distinct citation witnesses, then the direct dependency
    # membership rejection in a stalled task. Selection precedes native outcomes.
    seen=set();stalled_ids={s['task_id'] for s in stalls}
    for r in plans:
        rejected=r['old_evidence_reason']=='evidence_unrelated_to_execution_entry'
        direct_D=r['task_id'] in stalled_ids and r['plan']['acceptance']['reason']=='not_a_current_dependency_or_blocker' and r['shadow']['category']=='II'
        field=next((f for rel in r['shadow'].get('field_relations',[]) for f in rel['entry_fields']
                    if f in ('from_location','object_location','public_entries.reachable')),None)
        if not direct_D and not (rejected and r['shadow']['category'] in ('I','II') and field and field not in seen):continue
        c=controller(r['controller']);p=r['plan']['proposal'];action=r['shadow']['first_action']
        if p['type'] in ('ACQUIRE_MATERIAL','CRAFT_PRECONDITION'):
            action=copy.deepcopy(c).known_step(p['target'],1)
            if not action and p['target'] in (c.table.state.get('ground') or {}):action='pick up '+p['target']
        if not action or c.assess(action)['status']=='REJECT':continue
        if field:seen.add(field)
        selected.append(dict(id=r['id']+':native',task_id=r['task_id'],at_completed_step=r['decision_step']-1,action=action,
            state_hash=r['physical_state_hash'],source='saved_rejected_proposal',planning_state_id=r['id'],
            selection='first witness of typed citation field; or direct dependency-gate hypothesis in stalled task',
            public_controller=r['controller'],observation=r['observation'],proposal=p,shadow=r['shadow']))
    assert len(selected)<=50
    return selected


def branch(case,data):
    with tempfile.TemporaryDirectory(prefix='scar20audit-single-',dir=RUNTIME) as directory:
        env=restore(data,Path(directory));assert state_digest(env)==case['state_hash']
        assert valid_syntax(case['action'],env.agents[0].available_actions)
        before=copy.deepcopy(env.obs[AGENT_ID]);c=controller(case.get('public_controller') or next(s['controller'] for s in read_gzip(RESULTS/'terminal_states.jsonl.gz') if s['task_id']==case['task_id']))
        assert before==case.get('observation',before)
        k=Knowledge.from_dict(c.table.knowledge.to_dict());kb=k.view()
        from scar.io import digest
        public_state_hash=digest(c.to_dict());before_hp=hp(before)
        # Native simulator alone reads its hidden world to execute the public
        # action. No hidden recipe is read by selection or knowledge attribution.
        out,reward,done,info=env.step({AGENT_ID:case['action']});env.update_scores(reward)
        after=out[AGENT_ID];d=k.observe(after,case['action'],cutoff=after['step'])
        fb=PublicState.observe(after);prior=PublicState.observe(before)
        invalid=bool(info.get('step_invalid_action',{}).get(AGENT_ID,False))
        rejected=invalid or bool(__import__('re').search(r'Cannot |Invalid ',fb.feedback))
        public_gains={name:n-(prior.hands or {}).get(name,0) for name,n in (fb.hands or {}).items() if n>(prior.hands or {}).get(name,0)}
        result=dict(id=case['id'],task_id=case['task_id'],action=case['action'],at_completed_step=case['at_completed_step'],
            source=case['source'],initial_state_hash=case['state_hash'],final_state_hash=state_digest(env),
            public_controller_hash=public_state_hash,before_observation=before,after_observation=after,feedback=fb.feedback,
            done=bool(done),death=bool(getattr(reward[AGENT_ID],'death',0)),native_invalid=invalid,native_rejected=rejected,
            native_action_accepted=not rejected,knowledge_before=kb,knowledge_after=k.view(),knowledge_delta=d,
            public_hand_gains=public_gains,location_before=prior.location,location_after=fb.location,
            health_before=before_hp,health_after=hp(after),player_hp_loss=max(0,(before_hp or 0)-(hp(after) or 0)),
            reward={key:vars(val) for key,val in reward.items()},info=info,
            model_calls=0,tokens=0,cost_usd=0,steps=1,interpretation='local one-action effect only; no task-success extrapolation')
        assert digest(c.to_dict())==public_state_hash
        return result


def main():
    RUNTIME.mkdir(parents=True,exist_ok=True)
    chosen=select();write(RESULTS/'counterfactual_plan.json',chosen)
    # Save selection before any native alternative is executed.
    results=[];factual=0;restores=[];by_task=defaultdict(list)
    for case in chosen:
        if case['source']=='terminal_public_candidate':
            data=(ROOT/case['checkpoint']/'physical.pkl').read_bytes();results.append(branch(case,data))
        else:by_task[case['task_id']].append(case)
    tasks={t['task_id']:t for t in load(SOURCE/'tasks.json')}
    for tid,cases in by_task.items():
        task=tasks[tid];rows=read_gzip(folder(tid)/'trajectory.jsonl.gz');last=max(c['at_completed_step'] for c in cases)
        with tempfile.TemporaryDirectory(prefix='scar20audit-factual-',dir=RUNTIME) as directory:
            env,history=create_initial(task['game_name'],task['initial_seed'],Path(directory))
            from scar.io import digest
            assert state_digest(env)==task['initial_state_hash'] and digest(history)==task['initial_public_history_hash']
            for completed in range(last+1):
                data=snapshot(env)
                for case in cases:
                    if case['at_completed_step']==completed:
                        results.append(branch(case,data));env=restore(data,Path(directory)/'resumed')
                if completed==last:break
                row=rows[completed];assert env.obs[AGENT_ID]==row['observation']
                out,reward,done,info=env.step({AGENT_ID:row['action']});env.update_scores(reward);factual+=1
                assert state_digest(env)==row['state_hash'] and out[AGENT_ID]==row['feedback']
            restores.append(dict(task_id=tid,factual_prefix_actions=last,initial_history_actions=len(history),passed=True))
    assert len(results)==len(chosen) and not NETWORK_ATTEMPTS
    gzip_rows(RESULTS/'counterfactual_results.jsonl.gz',sorted(results,key=lambda r:r['id']))
    write(RESULTS/'counterfactual_receipt.json',dict(passed=True,single_step_branches=len(results),factual_prefix_actions=factual,
        factual_prefixes=restores,complete_closed_loop_tasks_rerun=0,new_model_calls=0,tokens=0,cost_usd=0,
        network_attempts=NETWORK_ATTEMPTS,selection_plan_sha256=sha(RESULTS/'counterfactual_plan.json')))
    print(json.dumps(dict(branches=len(results),factual_actions=factual,accepted=sum(r['native_action_accepted'] for r in results))))


if __name__=='__main__':main()
