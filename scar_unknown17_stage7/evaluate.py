"""Independent hidden-state audits, strictly after frozen policy execution."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import contextlib
import gzip
import hashlib
import importlib
import json
import multiprocessing as mp
from pathlib import Path
import re
import tempfile
from scar.environment import AGENT_ID,restore,snapshot,state_digest
from scar.io import atomic_json
from scar_sequence.resource_audit import census,retrieval
from scar_v3.hard import owned
from scar_v3.state import parse_action


def dispatch(env,action):
    module=importlib.import_module(type(env).__module__.rsplit('.',1)[0]+'.rule')
    verb,params=env.parse_action(env.agents[0],action)
    result=module.RuleResult(feedback={AGENT_ID:''},info_flags={'step_invalid_action':{AGENT_ID:False}})
    if verb is not None:
        ctx=module.RuleContext(env=env,world=env.world,agent=env.agents[0],action=verb,params=params,step_index=env.steps)
        env.action_rule_engine.dispatch(ctx,result)
    return result


def one_action(raw,action,tmp):
    env=restore(raw,tmp);ids=list(env.world.objects);before=census(env,ids)
    result=dispatch(env,action);after=census(env,ids);fb=result.feedback[AGENT_ID]
    m=re.search(r'successfully crafted (\d+)',fb)
    return {'action':action,'feedback':fb,'actual_output':int(m[1]) if m else 0,
        'consumed':{env.world.objects[k].name:before[k]-after[k] for k in ids if before[k]>after[k]},
        'produced':{env.world.objects[k].name:after[k]-before[k] for k in ids if after[k]>before[k]},
        'before_counts':{env.world.objects[k].name:n for k,n in before.items() if n},
        'after_counts':{env.world.objects[k].name:n for k,n in after.items() if n},
        'action_only_state_hash':state_digest(env),'events':[e.__dict__ for e in result.events]}


def audit_episode(job):
    folder,case=job;folder=Path(folder);resource=[];batches=[];catalog={}
    with tempfile.TemporaryDirectory() as tmp,open('/dev/null','w') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        paths=sorted((folder/'steps').glob('*/transition.json'))
        for i,path in enumerate(paths):
            row=json.loads(path.read_text());start=folder/'initial.pkl' if i==0 else paths[i-1].parent/'environment.pkl'
            raw=start.read_bytes();env=restore(raw,tmp)
            if i==0:
                catalog={o.name:{'ingredients':[env.world.objects[x].name for x in o.craft_ingredients if x in env.world.objects],
                    'weights':{env.world.objects[x].name:v for x,v in o.craft_ingredients.items() if x in env.world.objects},
                    'stations':[env.world.objects[x].name for x in o.craft_dependencies if x in env.world.objects]}
                    for o in env.world.objects.values() if o.craft_ingredients}
            relevant=set(case['materials'])|set(case['products']);before_counts=census(env,relevant)
            access_before={oid:owned(env,oid) for oid in relevant}
            rr=dispatch(env,row['executed_action']);action_counts=census(env,relevant)
            after=restore(path.parent/'environment.pkl',tmp,set_rng=False);after_counts=census(after,relevant)
            lost={o:action_counts[o]-after_counts[o] for o in relevant if action_counts[o]>after_counts[o]}
            consumed={o:before_counts[o]-action_counts[o] for o in relevant if before_counts[o]>action_counts[o]}
            temporary=[]
            for o in relevant:
                diff=access_before[o]-owned(after,o)-consumed.get(o,0)
                if diff>0 and after_counts[o]>0:temporary.append({'object_id':o,'lost_access_units':diff,'retrieval_lower_bound':retrieval(after,o)})
            resource.append({'task_id':folder.name,'case_id':case['id'],'index':i,'action':row['executed_action'],
                'actual_action_consumption':consumed,'environment_quantity_destruction':lost,'temporary_access_loss':temporary,
                'raw_nominal_loss':row['objective_metrics']['unaccounted_resource_destruction'],
                'scope':'exact action-only vs complete-step census, including NPC inventories; no permanent irrecoverability claim'})
            p=parse_action(row['executed_action'])
            if p.verb!='craft':continue
            actual_amount=int(p.args[0]) if p.args and p.args[0].isdigit() else None
            candidates=sorted({1,2,3,4}|({actual_amount} if actual_amount else set()))
            variants=[one_action(raw,f'craft {n} {p.target}',tmp) for n in candidates]
            actual=next((v for v in variants if v['action']==row['executed_action']),one_action(raw,row['executed_action'],tmp))
            dominated=[]
            for v in variants:
                ids=set(v['consumed'])|set(actual['consumed'])
                if v['actual_output']>=actual['actual_output'] and all(v['consumed'].get(k,0)<=actual['consumed'].get(k,0) for k in ids):
                    if v['actual_output']>actual['actual_output'] or any(v['consumed'].get(k,0)<actual['consumed'].get(k,0) for k in ids):dominated.append(v['action'])
            batch=row.get('structured',{}).get('mechanisms',{}).get('batch') or {}
            prediction=batch.get('predicted_consumption');error=None
            if prediction is not None:error=sum(abs(prediction.get(k,0)-actual['consumed'].get(k,0)) for k in set(prediction)|set(actual['consumed']))
            # Independent second dispatch verifies the actual resource effect.
            repeated=one_action(raw,row['executed_action'],tmp)
            assert repeated==actual
            batches.append({'task_id':folder.name,'case_id':case['id'],'index':i,'target':p.target,
                'starting_checkpoint':str(start),'starting_sha256':hashlib.sha256(raw).hexdigest(),
                'actual':actual,'variants':variants,'same_start':True,'dominated_by':dominated,
                'quantity_choice_non_dominated':not dominated,'predicted_consumption':prediction,'prediction_l1_error':error,
                'counterfactual_scope':'one-step original action rules, no step rules; local Pareto criterion, not an optimal task-level batch label',
                'actual_verified_twice':True})
    return {'task_id':folder.name,'case_id':case['id'],'resource':resource,'batches':batches,'catalog':catalog}


def main():
    p=argparse.ArgumentParser();p.add_argument('--runtime',required=True);p.add_argument('--workers',type=int,default=8);a=p.parse_args()
    root=Path(a.runtime);out=Path('results/stage7');tasks=json.loads((root/'tasks.json').read_text())
    cs={c['id']:c for c in json.loads((out/'cases.json').read_text())};catalogs={};n=b=0
    jobs=[(str(root/'runs'/t['task_id']),cs[t['id']]) for t in tasks]
    with ProcessPoolExecutor(max_workers=a.workers,mp_context=mp.get_context('spawn')) as pool, gzip.open(out/'resource_audit.jsonl.gz','wt') as rf,gzip.open(out/'batch_audit.jsonl.gz','wt') as bf:
        for record in pool.map(audit_episode,jobs):
            catalogs[record['case_id']]=record['catalog']
            for r in record['resource']:rf.write(json.dumps(r,ensure_ascii=False)+'\n');n+=1
            for r in record['batches']:bf.write(json.dumps(r,ensure_ascii=False)+'\n');b+=1
    atomic_json(out/'truth_catalog_evaluation_only.json',catalogs)
    atomic_json(out/'mechanism_audit_completion.json',{'episodes':len(jobs),'resource_actions':n,'craft_states':b,'api_calls':0})
    print(json.dumps({'resource_actions':n,'craft_states':b,'api_calls':0}))

if __name__=='__main__':main()
