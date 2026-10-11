"""Evaluator-only generation; unmodified engine rules, independent new games.

Selection depends on published world structure and executed witnesses, never on
any tested policy score. Initial allocation edits are fully recorded. The builder
is also the portable initial-state reconstruction procedure (no third party code
or unsafe pickle is published).
"""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import contextlib
import hashlib
import json
import math
import os
import multiprocessing as mp
from pathlib import Path
import shlex
import tempfile
from scar.environment import AGENT_ID, create_environment, snapshot, restore, state_digest
from scar.diagnostics.build import transition
from scar_v3.hard import goal_reached, replay, base_id
from scar.io import atomic_json,digest


GAMES = ['saltglass','quarantine','robot_kingdom']


def static_environment(game,seed,folder):
    """Disable optional LLM world expansion before constructing official engine.

    This is an explicitly recorded environment feature setting, identical for all
    methods. No action/step rule or object recipe is modified.
    """
    upstream=Path(os.environ['AGENTODYSSEY_ROOT'])
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)
        config=root/f'assets/env_configs/generated/{game}/initial.json'
        world=root/f'assets/world_definitions/generated/{game}/default.json'
        config.parent.mkdir(parents=True);world.parent.mkdir(parents=True)
        config.write_bytes((upstream/config.relative_to(root)).read_bytes())
        definition=json.loads((upstream/world.relative_to(root)).read_text())
        definition.setdefault('features',{})['online_expansion']=False
        world.write_text(json.dumps(definition))
        return create_environment(game,seed,folder,upstream=root)


def dependency_graph(env, target, depth=2):
    graph = {}; leaves = Counter(); products = Counter(); order = []
    def expand(oid, amount, level, ancestors):
        obj = env.world.objects[oid]
        ing = obj.craft_ingredients
        if oid in ancestors:
            raise ValueError('recipe cycle')
        if not ing or level < 0:
            leaves[oid] += amount
            return
        if any(k not in env.world.objects for k in ing):
            raise ValueError('undefined ingredient')
        products[oid] += amount
        graph[oid] = {'ingredients':dict(ing),'dependencies':list(obj.craft_dependencies)}
        for child, count in sorted(ing.items()):
            expand(child, int(math.ceil(count*amount)),level-1,ancestors+(oid,))
        if oid not in order:
            order.append(oid)
    expand(target,1,depth,())
    return graph,dict(leaves),dict(products),order


def controlled_world(game,seed,folder):
    env,_ = static_environment(game,seed,folder)
    original = state_digest(env)
    areas = sorted([a for a in env.world.area_instances.values() if 'tutorial' not in a.id],key=lambda a:a.id)[:3]
    path_type = type(next(p for a in env.world.area_instances.values() for p in a.neighbors.values()))
    for area in env.world.area_instances.values():
        area.objects,area.npcs,area.neighbors,area.light = {},[],{},True
    for left,right in zip(areas,areas[1:]):
        left.neighbors[right.id] = path_type(to_id=right.id,locked=False,object_to_unlock=None)
        right.neighbors[left.id] = path_type(to_id=left.id,locked=False,object_to_unlock=None)
    for place in env.world.place_instances.values(): place.unlocked = True
    if env.world.auxiliary.get('tutorial_room'):
        env.world.auxiliary['tutorial_room']['removed'] = True
    a = env.agents[0]; a.items_in_hands={};a.equipped_items_in_limb={};a.inventory.container=None;a.hp=100
    env.curr_agents_state['area'][AGENT_ID] = areas[0].id
    if 'active_combats' in env.curr_agents_state: env.curr_agents_state['active_combats'][AGENT_ID] = {}
    for c in env.world.container_instances.values(): c.inventory={}
    return env,areas,original


def craft_case(job):
    game,target,serial,output = job
    folder = Path(output)/'candidates'/f'{game}-{target}';folder.mkdir(parents=True,exist_ok=True)
    if (folder/'case.json').exists():return json.loads((folder/'case.json').read_text())
    with (folder/'engine.log').open('w') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        try:
            seed=51000+serial
            env,areas,original=controlled_world(game,seed,folder/'world')
            graph,leaves,products,order=dependency_graph(env,target)
            if len(graph)<2 or len(graph)>6:raise ValueError('requires 2..6 actual recipe nodes')
            if any(env.world.objects[x].category=='container' or env.world.objects[x].usage=='writable' or
                   env.world.objects[x].size is None for x in set(leaves)|set(products)):
                raise ValueError('portable non-instance crafting cohort')
            container=max(env.world.container_instances.values(),key=lambda c:c.capacity)
            volume=sum(env.world.objects[x].size*n for x,n in leaves.items())
            if volume>container.capacity:raise ValueError('raw supply exceeds existing portable capacity')
            areas[0].objects[container.id]=1
            known = serial%2==0
            allocations={}
            for i,(oid,n) in enumerate(sorted(leaves.items())):
                area=areas[i%2];area.objects[oid]=n*(2 if known else 1);allocations[oid]=area.id
            if not known:areas[0].objects[target]=1
            stations=sorted({x for v in graph.values() for x in v['dependencies']})
            for x in stations:areas[2].objects[x]=1
            transition(env,'wait')
            history=[]
            def public(action):
                r=transition(env,action);history.append({k:r[k] for k in ['before','action','after']});return r
            # A genuine walk reveals the same locations in both strata. Only
            # known-structure histories inspect raw materials to reveal recipes.
            public('inspect '+shlex.quote(container.name))
            public('pick up '+shlex.quote(container.name));public('equip '+shlex.quote(container.name))
            if not known:public('pick up '+shlex.quote(env.world.objects[target].name))
            if known:
                for oid in areas[0].objects.copy():
                    if oid in leaves:public('inspect '+shlex.quote(env.world.objects[oid].name))
            public('enter '+shlex.quote(areas[1].name))
            if known:
                for oid in areas[1].objects.copy():
                    if oid in leaves:public('inspect '+shlex.quote(env.world.objects[oid].name))
            public('enter '+shlex.quote(areas[2].name))
            public('enter '+shlex.quote(areas[1].name));public('enter '+shlex.quote(areas[0].name))
            if known:
                # Real demonstration, with public inventory inspections before
                # and after every craft. The product is kept, and the future
                # physical goal requires TWO copies. No feedback fabrication,
                # time travel, or post-history initial-state edits.
                for area in areas[:2]:
                    if env.curr_agents_state['area'][AGENT_ID]!=area.id:public('enter '+shlex.quote(area.name))
                    for oid,n in sorted(leaves.items()):
                        if allocations[oid]==area.id:public(f'store {n} {shlex.quote(env.world.objects[oid].name)} inventory')
                public('enter '+shlex.quote(areas[2].name))
                for oid in order:
                    public('inspect inventory')
                    r=public(f'craft {products[oid]} {shlex.quote(env.world.objects[oid].name)}')
                    if r['semantic_rejection']:raise ValueError('public demonstration craft failed')
                    public('inspect inventory')
                    public('inspect '+shlex.quote(env.world.objects[oid].name))
                    if oid==target:public('pick up '+shlex.quote(env.world.objects[oid].name))
                    else:
                        r=public(f'store {products[oid]} {shlex.quote(env.world.objects[oid].name)} inventory')
                        if r['semantic_rejection']:raise ValueError('public demonstration transfer failed')
                public('enter '+shlex.quote(areas[1].name));public('enter '+shlex.quote(areas[0].name))
            action='craft 1 '+shlex.quote(env.world.objects[target].name)
            r=public(action)
            if not r['semantic_rejection']:raise ValueError('initial target must fail')
            start=snapshot(env)
            goal={'kind':'possess','object_id':target,'name':env.world.objects[target].name,'amount':2}
            witness=[]
            trial=restore(start)
            def execute(a):
                r=transition(trial,a)
                if r['semantic_rejection']:raise ValueError('witness rejected: '+a)
                witness.append(a)
            for area in areas[:2]:
                if trial.curr_agents_state['area'][AGENT_ID]!=area.id:execute('enter '+shlex.quote(area.name))
                for oid,n in sorted(leaves.items()):
                    if allocations[oid]==area.id:execute(f'store {n} {shlex.quote(env.world.objects[oid].name)} inventory')
            execute('enter '+shlex.quote(areas[2].name))
            for oid in order:
                execute(f'craft {products[oid]} {shlex.quote(env.world.objects[oid].name)}')
                if oid==target:execute('pick up '+shlex.quote(env.world.objects[oid].name))
                else:execute(f'store {products[oid]} {shlex.quote(env.world.objects[oid].name)} inventory')
            valid,trace=replay(start,witness,goal)
            if not valid:raise ValueError('independent witness replay failed')
            if len(witness)>35:raise ValueError('witness longer than predeclared diagnostic design')
            family=digest([game,target,graph,'three_area_sequence_depth2'])
            (folder/'initial.pkl').write_bytes(start)
            edits={'source_world_hash':original,'areas':[a.id for a in areas],
                   'leaves':leaves,'products':products,'allocations':allocations,'container_id':container.id,
                   'stations':stations,'edits':['disable optional online world expansion before engine initialization','clear initial objects, NPCs, hands and combat','three original areas connected in a line',
                   'disable tutorial via original completion flag','enable light and area access','allocate real recipe resources; no action-rule edits']}
            result={'id':'sequence-'+family[:16],'family':family,'game':game,'seed':seed,'kind':'craft',
                'source_cluster':game,'mechanism_cluster':digest(sorted((len(v['ingredients']),sorted(v['ingredients'].values()),len(v['dependencies'])) for v in graph.values())),
                'source':'synthetic_initial_allocations_unmodified_engine','types':['multi_stage_craft','capacity','cross_location_transport'],
                'knowledge': 'demonstrated_rules' if known else 'interaction_discovery',
                'knowledge_limit':'Known stratum has real successful crafting plus before/after inventory observations; quantities are observable sample effects, not guaranteed universal rules. Unknown stratum has no crafting demonstration.',
                'target_action':action,'goal':goal,'public_goal':f'Obtain at least 2 {goal["name"]} in your possession in total. You already hold one. The previous craft failed. Any valid route is allowed.',
                'history':history,'initial_snapshot':str((folder/'initial.pkl').resolve()),'state_hash':state_digest(restore(start)),
                'snapshot_sha256':hashlib.sha256(start).hexdigest(),'initialization':edits,'recipe_graph':graph,
                'materials':leaves,'products':products,'witness':witness,'witness_length':len(witness),
                'witness_replay':trace,'validated':True,'recoverable':True,'max_steps':40,'split':'test',
                'selection':'structural eligibility and true witness only; no policy evaluation'}
        except Exception as exc:
            result={'game':game,'target':target,'validated':False,'reason':str(exc)}
        atomic_json(folder/'case.json',result)
        return result


def build(output,workers=8,per_game=10):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    jobs=[]
    for gi,game in enumerate(GAMES):
        with tempfile.TemporaryDirectory() as tmp,contextlib.redirect_stdout(open('/dev/null','w')):
            env,_=static_environment(game,51000+gi,tmp)
            targets=sorted(o.id for o in env.world.objects.values() if o.craft_ingredients and o.category not in {'container'} and o.usage!='writable' and o.size is not None)
            for i,target in enumerate(targets):jobs.append((game,target,gi*1000+i,str(output)))
    atomic_json(output/'selection_plan.json',{'games':GAMES,'per_game':per_game,'candidate_order':jobs,
          'rule':'first 10 valid target IDs per unseen game; validation never runs candidate agents',
          'holdout':'All three games absent from V1-V3 and Stage4; static common action schemas are shared.',
          'max_steps':40,'no_policy_result_filter':True})
    with ProcessPoolExecutor(max_workers=workers,mp_context=mp.get_context('spawn')) as pool:
        results=list(pool.map(craft_case,jobs))
    selected=[]
    for game in GAMES:
        selected += sorted([r for r in results if r['game']==game and r['validated']],key=lambda r:r['goal']['object_id'])[:per_game]
    atomic_json(output/'cases.json',selected)
    atomic_json(output/'construction.json',{'attempted':len(results),'selected':len(selected),
        'valid_before_selection':sum(r['validated'] for r in results),'exclusions':[r for r in results if not r['validated']],
        'dataset_hash':digest(selected),'knowledge_counts':dict(Counter(r['knowledge'] for r in selected)),
        'limitations':['Known uses real crafting demonstrations with observable resource consumption; histories are longer than STM window.',
                      'Dynamic rule changes not injected. Goal switching and lock release require separate official-mechanism cases.']})
    print(json.dumps({'selected':len(selected),'knowledge':dict(Counter(r['knowledge'] for r in selected))}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--workers',type=int,default=8);p.add_argument('--per-game',type=int,default=10)
    a=p.parse_args();build(a.output,a.workers,a.per_game)
