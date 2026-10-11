"""Post-hoc resource accounting correction, independent original-rule dispatch.

The frozen online evaluator subtracted nominal recipe fractions; official engine
floors remaining counts, so 0.5 input may actually consume 1 unit. Preserve those
raw fields, replace publication loss metrics with exact action/step separation.
No policy modification, model calls, trajectory selection or reruns.
"""
import argparse
from collections import Counter,deque
from concurrent.futures import ProcessPoolExecutor
import contextlib
import gzip
import importlib
import json
import multiprocessing as mp
from pathlib import Path
import tempfile
from scar.environment import AGENT_ID,restore
from scar_v3.hard import base_id,owned
from scar_v3.state import parse_action
from scar.io import atomic_json


def census(env,relevant):
    count=Counter()
    for a in env.agents:count.update(a.items_in_hands);count.update(a.equipped_items_in_limb)
    for area in env.world.area_instances.values():count.update(area.objects)
    for c in env.world.container_instances.values():count.update(c.inventory)
    for npc in env.world.npc_instances.values():count.update(npc.inventory)
    return {oid:sum(n for x,n in count.items() if base_id(env,x)==oid) for oid in relevant}


def retrieval(env,oid):
    """Lower bound in actions for a currently existing ground/container item.

    Uses unlocked physical topology; ignores hand capacity and other task costs.
    This is a lower bound, not a guaranteed cheap recovery plan.
    """
    start=env.curr_agents_state['area'][AGENT_ID];queue=deque([(start,0)]);seen={start}
    while queue:
        loc,d=queue.popleft();area=env.world.area_instances[loc]
        if any(base_id(env,x)==oid and n>0 for x,n in area.objects.items()):return {'location':area.name,'moves':d,'action_lower_bound':d+1,'storage':'ground'}
        for cid in area.objects:
            if cid in env.world.container_instances and env.world.container_instances[cid].inventory.get(oid,0)>0:
                return {'location':area.name,'moves':d,'action_lower_bound':d+1,'storage':'ground_container'}
        for nxt,path in area.neighbors.items():
            if not path.locked and nxt not in seen:seen.add(nxt);queue.append((nxt,d+1))
    return None


def audit_task(job):
    folder,case=job;folder=Path(folder);result=[]
    relevant=set(case.get('materials',{}))|set(case.get('products',{}))
    if case['goal'].get('object_id'):relevant.add(case['goal']['object_id'])
    with tempfile.TemporaryDirectory() as tmp,open('/dev/null','w') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        paths=sorted((folder/'steps').glob('*/transition.json'))
        for i,path in enumerate(paths):
            row=json.loads(path.read_text());before_file=folder/'initial.pkl' if i==0 else paths[i-1].parent/'environment.pkl'
            env=restore(before_file,tmp);before_counts=census(env,relevant)
            access_before={oid:owned(env,oid) for oid in relevant}
            module=importlib.import_module(type(env).__module__.rsplit('.',1)[0]+'.rule')
            verb,params=env.parse_action(env.agents[0],row['executed_action'])
            rule_result=module.RuleResult(feedback={AGENT_ID:''},info_flags={'step_invalid_action':{AGENT_ID:False}})
            if verb is not None:
                ctx=module.RuleContext(env=env,world=env.world,agent=env.agents[0],action=verb,params=params,step_index=env.steps)
                env.action_rule_engine.dispatch(ctx,rule_result)
            action_counts=census(env,relevant)
            after=restore(path.parent/'environment.pkl',tmp,set_rng=False);after_counts=census(after,relevant)
            losses={oid:action_counts[oid]-after_counts[oid] for oid in relevant if action_counts[oid]>after_counts[oid]+1e-8}
            consumed={oid:before_counts[oid]-action_counts[oid] for oid in relevant if before_counts[oid]>action_counts[oid]+1e-8}
            temporary=[]
            for oid in relevant:
                diff=access_before[oid]-owned(after,oid)-consumed.get(oid,0)
                if diff>0 and after_counts[oid]>0:
                    temporary.append({'object_id':oid,'lost_access_units':diff,
                        'retrieval_lower_bound':retrieval(after,oid),'world_quantity_remaining':after_counts[oid]})
            result.append({'task_id':folder.name,'case_id':case['id'],'index':row['index'],
                'action':row['executed_action'],'action_rule_feedback':rule_result.feedback[AGENT_ID],
                'actual_action_consumption':consumed,'environment_quantity_destruction':losses,
                'temporary_access_loss':temporary,
                'raw_nominal_loss':row['objective_metrics']['unaccounted_resource_destruction'],
                'source':'original action-only dispatch then compare saved full-step state; counts include NPC inventories',
                'permanent_task_failure_proven':False})
    return result


def audit(runtime,output='results/sequence',workers=8):
    root=Path(runtime);out=Path(output)
    cases={c['id']:c for c in json.loads((root/'dataset/cases.json').read_text())}
    tasks=json.loads((root/'tasks.json').read_text())
    jobs=[(str(root/'runs'/t['task_id']),cases[t['id']]) for t in tasks]
    total=raw=corrected=false_flags=temporary=0
    with ProcessPoolExecutor(max_workers=workers,mp_context=mp.get_context('spawn')) as pool,gzip.open(out/'resource_audit.jsonl.gz','wt') as f:
        for group in pool.map(audit_task,jobs):
            for row in group:
                f.write(json.dumps(row,ensure_ascii=False)+'\n');total+=1
                raw+=bool(row['raw_nominal_loss']);corrected+=bool(row['environment_quantity_destruction'])
                false_flags+=bool(row['raw_nominal_loss']) and not row['environment_quantity_destruction']
                temporary+=len(row['temporary_access_loss'])
    summary={'actions_audited':total,'raw_nominal_loss_steps':raw,'true_environment_quantity_destruction_steps':corrected,
        'raw_flags_explained_by_actual_action_consumption':false_flags,'temporary_access_loss_records':temporary,
        'posthoc_correction':True,'api_calls':0,'policy_changes':False,'recovery_results_changed':False,
        'reason':'Frozen runtime metric subtracted nominal fractional recipe consumption. Engine floors remaining integer counts; original action dispatch also resolves non-recovery crafting and sales.',
        'scope':'Actual item-unit destruction is irreversible for that item, but future supplies or alternative goal routes may exist. No permanent task failure claim.'}
    atomic_json(out/'resource_audit_summary.json',summary);print(json.dumps(summary))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--runtime',required=True);p.add_argument('--output',default='results/sequence');p.add_argument('--workers',type=int,default=8)
    a=p.parse_args();audit(a.runtime,a.output,a.workers)
