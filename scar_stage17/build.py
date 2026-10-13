"""Offline-only task selection. No evaluated policy is imported or run."""
import argparse
import copy
import io
import contextlib
import tempfile
from pathlib import Path
from collections import defaultdict
from scar.environment import snapshot,state_digest,restore,AGENT_ID
from scar.io import digest
from scar_v3.hard import owned
from .environment import create_initial
from .oracle import Witness
from .common import RESULTS,ENGINE_COMMIT,load,write,gzip_rows


def graph(env,target):
    visited={}
    def walk(oid,trail=()):
        if oid in visited or oid in trail:return
        obj=env.world.objects[oid]
        if not obj.craft_ingredients:return
        visited[oid]=dict(name=obj.name,ingredients=dict(obj.craft_ingredients),stations=list(obj.craft_dependencies),ingredient_names={env.world.objects[k].name:v for k,v in obj.craft_ingredients.items()},station_names=[env.world.objects[k].name for k in obj.craft_dependencies])
        for child in obj.craft_ingredients:walk(child,trail+(oid,))
    walk(target)
    def depth(oid,seen=()):
        if oid not in visited or oid in seen:return 0
        return 1+max([depth(n,seen+(oid,)) for n in visited[oid]['ingredients']]+[0])
    return visited,depth(target)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--runtime',required=True);args=parser.parse_args()
    runtime=Path(args.runtime);runtime.mkdir(parents=True,exist_ok=True)
    if (RESULTS/'tasks.json').exists():raise FileExistsError('Frozen candidate task list already exists')
    old=load(RESULTS/'prior_task_inventory.json');sweep=load(RESULTS/'candidate_sweep.json')
    candidates=[];pools=defaultdict(list)
    for row in sweep:
        row=copy.deepcopy(row)
        oldids={x['object_id'] for x in old}
        if row['oid'] in oldids:row.update(ok=False,error='old target object ID in ANY prior game; possible template alias')
        row['scope']='offline native witness only; failure is unverified, not proof of impossibility'
        candidates.append(row)
        if row['ok']:pools[row['game']].append(row)
    # Coverage quotas fixed from feasible candidate counts, before any algorithm evaluation.
    quotas={'robot_kingdom':15,'quarantine':9}
    selected=[]
    for game,quota in quotas.items():
        # Structural witness-length bins plus hash tie-break, not policy performance.
        bins=defaultdict(list)
        for row in pools[game]:bins[min(2,row['steps']//10)].append(row)
        for values in bins.values():values.sort(key=lambda r:digest([game,r['oid'],'stage17-selection-v1']))
        chosen=[]
        while len(chosen)<quota:
            for key in sorted(bins):
                if bins[key] and len(chosen)<quota:chosen.append(bins[key].pop(0))
        selected.extend(chosen)
    tasks=[];truth={};witnesses=[];initial=[]
    for index,row in enumerate(selected):
        game=row['game'];seed=170100+index;folder=runtime/f'build-{index:02d}'
        with contextlib.redirect_stdout(io.StringIO()):env,history=create_initial(game,seed,folder)
        before=snapshot(env);oid=row['oid'];name=row['name'];task_id=f's17-{index+1:02d}-{game}-{name}'
        assert owned(env,oid)==0
        dependencies,depth=graph(env,oid)
        oldids={x['object_id'] for x in old if x['game']==game}
        oldnodes=set()
        for oldid in oldids:
            if oldid in env.world.objects:
                sub,_=graph(env,oldid);oldnodes.update(sub)
                for fact in sub.values():oldnodes.update(fact['ingredients'])
        overlap=sorted(set(dependencies)&oldnodes)
        task=dict(task_id=task_id,game_name=game,target_item=name,target_amount=1,
            objective_text=f'Craft at least 1 {name} during this task and obtain at least 1 {name} in your own possession. A product left on the ground does not count. Achieve this within 100 environment actions. This is the current evaluation objective.',
            initial_seed=seed,initial_state_hash=state_digest(env),initial_public_history_hash=digest(history),
            max_steps=100,source_version=ENGINE_COMMIT,official_tutorial_prefix_actions=len(history),
            selection_reason='new target and seed; unchanged native world; independent offline feasibility witness; structural diversity with fixed coverage quotas',
            family=game+':'+oid,dependency_depth=depth,recipe_nodes=len(dependencies))
        task['task_definition_hash']=digest(task);tasks.append(task)
        initial.append(dict(task_id=task_id,history=history,observation=copy.deepcopy(env.obs[AGENT_ID])))
        (runtime/(task_id+'.pkl')).write_bytes(before)
        with contextlib.redirect_stdout(io.StringIO()):
            witness=Witness(restore(before));trace=witness.solve(oid)
        assert any(t['action'].startswith('craft ') and t['action'].split()[-1]==name for t in trace)
        witnesses.append(dict(task_id=task_id,steps=len(trace),trace=trace,final_owned=owned(witness.env,oid)))
        truth[task_id]=dict(target_id=oid,recipes=dependencies,old_graph_overlap_ids=overlap,
            old_material_overlap_ids=sorted({m for r in dependencies.values() for m in r['ingredients']}&oldnodes),
            scope='BUILDER/EVALUATOR ONLY; never passed to an online method')
    write(RESULTS/'candidate_selection.json',dict(quotas=quotas,candidates=candidates,rule='Native witness <=85; final target actually crafted; old target ID excluded; fixed structural-bin/hash selection; no method outcomes'))
    write(RESULTS/'tasks.json',tasks);write(RESULTS/'evaluator_truth.json',truth)
    gzip_rows(RESULTS/'initial_public_histories.jsonl.gz',initial)
    gzip_rows(RESULTS/'native_feasibility_witnesses.jsonl.gz',witnesses)
    print('built',len(tasks),'tasks',quotas,flush=True)

if __name__=='__main__':main()
