"""Post-policy, zero-model, one-switch audit of every committed decision.

All branches share recorded history, controller state, public observation, and
base proposal. Only one flag is changed. Physical counterfactuals run the original
full environment step (including step rules). Never used to update a policy.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor
import contextlib
import copy
import gzip
import json
import multiprocessing as mp
from pathlib import Path
import tempfile
from scar.environment import restore,state_digest,AGENT_ID
from scar.diagnostics.scoring import score_candidate
from scar_sequence.evaluate import physical
from scar_unknown17.evaluate import one_action
from scar_unknown17_stage7.controller import Stage7Controller,FLAGS
from scar_unknown17_stage7.offline import save_state
from scar.io import atomic_json
from scar_v3.state import parse_action


def full_step(raw,action,case,tmp):
    env=restore(raw,tmp);before=physical(env,case);truth=score_candidate(env,action)
    after,_,done,_=env.step({AGENT_ID:action})
    return {'action':action,'rejected':truth['semantic_rejection'],'action_feedback':truth['feedback'],
        'public_feedback':after[AGENT_ID],'physical_before':before,'physical_after':physical(env,case),
        'state_hash':state_digest(env),'game_done':bool(done)}


def audit(job):
    folder,case=job;folder=Path(folder);records=[];metrics=[];changes={};errors=[]
    key={case['object_names'][x] for x in case['recipe_graph']};goal=case['goal']['name'];prefix=[]
    with tempfile.TemporaryDirectory() as tmp,open('/dev/null','w') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        numeric_history=Stage7Controller(resource_goal_guard=True)
        for h in case['history']:numeric_history.observe(h['before'],h['action'],h['after'])
        numeric_history.set_goal(case['target_action'],case['public_goal'])
        paths=sorted((folder/'steps').glob('*/transition.json'))
        for i,path in enumerate(paths):
            r=json.loads(path.read_text());raw=(folder/'initial.pkl' if i==0 else paths[i-1].parent/'environment.pkl').read_bytes()
            state=r['stage7_state_before'];base=r['proposed_action'];env=restore(raw,tmp)
            original=Stage7Controller.from_dict(state);decision=original.choose(r['observation'],base)
            if decision!=r['executed_action']:errors.append({'index':i,'reproduced':decision,'actual':r['executed_action']})
            cache={};actual=r['executed_action']
            def effect(action):
                if action not in cache:cache[action]=full_step(raw,action,case,tmp)
                return cache[action]
            actual_effect=effect(actual)
            for flag in FLAGS:
                clone=Stage7Controller.from_dict(state);clone.flags[flag]=not clone.flags[flag]
                policy_error=None
                try:alternate=clone.choose(r['observation'],base)
                except Exception as exc:
                    alternate=None;policy_error={'kind':type(exc).__name__,'message':str(exc)}
                changed=alternate!=actual
                e=effect(alternate) if alternate is not None else None
                records.append({'task_id':folder.name,'case_id':case['id'],'index':i,'flag':flag,
                    'original_flags':state['flags'],'alternate_flags':clone.flags,'base_action':base,
                    'original_action':actual,'alternate_action':alternate,'changed':changed,'alternate_policy_error':policy_error,
                    'public_observation_identical':True,'controller_start_identical_except_flag':True,
                    'original_mechanism':original.stage7_decision,'alternate_mechanism':clone.stage7_decision,
                    'starting_physical_hash':state_digest(restore(raw,set_rng=False)),
                    'original_effect':actual_effect if changed else None,'alternate_effect':e if changed else None,
                    'goal_delta':int(e['physical_after']['goal'])-int(actual_effect['physical_after']['goal']) if e is not None else None,
                    'rejection_delta':int(e['rejected'])-int(actual_effect['rejected']) if e is not None else None,
                    'scope':'single full-step intervention, fixed recorded base proposal; prior module history held fixed, not full episode ablation'})
                if changed and flag not in changes:
                    changes[flag]={'case_id':case['id'],'task_id':folder.name,'index':i,'flag':flag,
                        'state':save_state(raw,folder.name+'-'+str(i)+'-'+flag),
                        'prefix_actions':list(prefix),'base_action':base,'original_action':actual,'alternate_action':alternate,
                        'controller_before':state,'public_observation':r['observation'],'alternate_policy_error':policy_error}
            # Independent engine truth for opportunity and final-collection metrics.
            public=Stage7Controller.from_dict(state);public.table.observe(r['observation']);t=public.table
            ready=[]
            for item in sorted(key):
                need=public.public_demand(item) if public.flags['resource_goal_guard'] else (public.amount if item==goal else public.queue_needs.get(item,1))
                if not t.recipes.get(item,{}).get('ingredients') or (t.count(item) or 0)>=need:continue
                truth=score_candidate(restore(raw,tmp), 'craft 1 '+item)
                if not truth['semantic_rejection']:ready.append(item)
            p=parse_action(actual);productive=p.verb=='craft' and 'successfully crafted' in r['action_rule_feedback']
            ground=t.state.get('ground') or {}; collection=[]
            if ground.get(goal,0)>0:
                collection.append('pick up '+goal)
                if t.inventory:collection.extend([f'store {n} {goal} inventory' for n in [1,2,3,4]])
            for name,c in t.containers.items():
                if t.access(name) and (c.get('counts') or {}).get(goal,0)>0:collection.append(f'take out {goal} {name}')
            final_options=[action for action in collection if effect(action)['physical_after']['goal'] and not effect(action)['rejected']]
            actual_goal_gain=r['physical_after']['accessible'].get(goal,0)>r['physical_before']['accessible'].get(goal,0)
            # Audit expired old forward trial eligibility with public condition release;
            # does not assert the item is essential or retry would finish the episode.
            missed=[]
            for product,n in public.trials.items():
                recipe=t.recipes.get(product,{});stations=recipe.get('stations',[])
                if n<1 or not stations or not all(ground.get(x,0)>0 for x in stations):continue
                if (t.count(product) or 0)>0 or any(d['objects'].get(product,0)>0 for d in t.places.values()):continue
                prior=[x for x in metrics if x.get('failed_trial_target')==product]
                if prior and not score_candidate(restore(raw,tmp),'craft 1 '+product)['semantic_rejection'] and not (p.verb=='craft' and p.target==product):missed.append(product)
            probe=r.get('structured',{}).get('mechanisms',{}).get('exploration') or {}
            failed_trial=p.target if p.verb=='craft' and r['semantic_rejection'] and probe.get('reason')=='bounded forward recipe trial' else None
            # Exact consumption of an input reserved for a different known downstream
            # subgoal: count avoidable depletion when a smaller productive action
            # preserves more of the same material. No global impossibility claim.
            resource_conflicts=[]
            # Common evaluation criterion across flags: numerically disclosed
            # public recipes are available in model observations for every method.
            public.public_quantity_rules=copy.deepcopy(numeric_history.public_quantity_rules)
            reserves=public.reservations(p.target)
            if productive:
                act=one_action(raw,actual,tmp);amount=int(p.args[0])
                smaller=[one_action(raw,f'craft {n} {p.target}',tmp) for n in range(1,amount)]
                if p.target!=goal and act['consumed'].get(goal,0)>0 and (t.count(goal) or 0)<=public.amount:
                    resource_conflicts.append({'material':goal,'reserved_public_floor':public.amount,
                        'actual_consumed':act['consumed'][goal],'less_consuming_productive_actions':[],
                        'scope':'consumed already-owned final-goal copy still required by explicit possession objective; delayed exploration gain may exist'})
                # A production can be unnecessary even at quantity1: already
                # visible ground copies may satisfy the public subgoal demand.
                # Verify acquisition in the same actual engine state, then detect
                # consumption of inputs publicly reserved for other downstream uses.
                demand=public.public_demand(p.target)
                if (t.count(p.target) or 0)<demand and (t.count(p.target) or 0)+ground.get(p.target,0)>=demand:
                    acquire=public._acquire(p.target,demand,set(public._all_needed(goal)))
                    acquisition=effect(acquire) if acquire else None
                    if acquisition is not None and not acquisition['rejected'] and acquisition['physical_after']['accessible'].get(p.target,0)>r['physical_before']['accessible'].get(p.target,0):
                        for material,reserve in reserves.items():
                            if act['consumed'].get(material,0)>0 and (t.count(material) or 0)-act['consumed'][material]<reserve:
                                resource_conflicts.append({'material':material,'reserved_public_floor':reserve,
                                    'actual_consumed':act['consumed'][material],'alternative_acquisition':acquire,
                                    'alternative_effect':acquisition,
                                    'scope':'redundant craft despite enough public ground copies; same-state legal acquisition preserves a downstream reserved material'})
                for material,reserve in reserves.items():
                    if act['consumed'].get(material,0)<=0:continue
                    alternative=[v for v in smaller if v['actual_output']>0 and v['consumed'].get(material,0)<act['consumed'][material]]
                    if alternative and (t.count(material) or 0)-act['consumed'][material]<reserve:
                        resource_conflicts.append({'material':material,'reserved_public_floor':reserve,'actual_consumed':act['consumed'][material],
                            'less_consuming_productive_actions':[v['action'] for v in alternative],
                            'scope':'avoidable reserve depletion, not proof of permanent task failure'})
            metrics.append({'task_id':folder.name,'case_id':case['id'],'index':i,'known_engine_ready_nodes':ready,
                'ready_executed':bool(productive and p.target in ready),
                'final_collection_options':final_options,'final_available_unrelated_action':bool(final_options and not r['diagnostic_goal_reached'] and not actual_goal_gain and not (p.target==goal and p.verb in {'pick up','store','take out'})),
                'missed_retry_candidates':missed,'failed_trial_target':failed_trial,
                'avoidable_known_reserve_depletion':resource_conflicts})
            numeric_history.observe(r['observation'],actual,r['next_observation']);numeric_history.events.clear()
            prefix.append(actual)
    return {'task_id':folder.name,'records':records,'metrics':metrics,'examples':list(changes.values()),'reproduction_errors':errors}


def main():
    p=argparse.ArgumentParser();p.add_argument('--runtime',required=True);p.add_argument('--workers',type=int,default=8);a=p.parse_args()
    root=Path(a.runtime);out=Path('results/stage7');tasks=json.loads((root/'tasks.json').read_text());cs={c['id']:c for c in json.loads((out/'cases.json').read_text())}
    totals={'api_calls':0,'episodes':0,'decisions':0,'one_flag_comparisons':0,'changes':{k:0 for k in FLAGS},'counterfactual_policy_errors':[],'reproduction_errors':[]}
    with ProcessPoolExecutor(max_workers=a.workers,mp_context=mp.get_context('spawn')) as pool, gzip.open(out/'decision_counterfactuals.jsonl.gz','wt') as cf,gzip.open(out/'opportunity_audit.jsonl.gz','wt') as mf,gzip.open(out/'decision_examples.jsonl.gz','wt') as ef:
        for result in pool.map(audit,[(str(root/'runs'/t['task_id']),cs[t['id']]) for t in tasks]):
            totals['episodes']+=1;totals['decisions']+=len(result['metrics']);totals['one_flag_comparisons']+=len(result['records'])
            totals['reproduction_errors'] += [{'task_id':result['task_id'],**e} for e in result['reproduction_errors']]
            for r in result['records']:
                cf.write(json.dumps(r,ensure_ascii=False)+'\n');totals['changes'][r['flag']]+=int(r['changed'])
                if r.get('alternate_policy_error'):totals['counterfactual_policy_errors'].append({k:r[k] for k in ['task_id','index','flag','alternate_policy_error']})
            for r in result['metrics']:mf.write(json.dumps(r,ensure_ascii=False)+'\n')
            for r in result['examples']:ef.write(json.dumps(r,ensure_ascii=False)+'\n')
    totals['passed']=not totals['reproduction_errors'] and totals['episodes']==102
    atomic_json(out/'decision_audit_summary.json',totals);print(json.dumps(totals));assert totals['passed']

if __name__=='__main__':main()
