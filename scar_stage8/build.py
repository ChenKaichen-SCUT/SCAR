"""Evaluator-only new families after policy freeze. No tested-policy imports.

Native recipes and action/step rules unchanged. One candidate per official target,
fixed seed, structural exclusion before witness validation; never score selection.
"""
import argparse,contextlib,copy,gzip,hashlib,json,math,os,tempfile
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp
from pathlib import Path
from scar.io import atomic_json,digest
from scar.environment import AGENT_ID,snapshot,restore,state_digest
from scar_sequence.build import controlled_world,dependency_graph,static_environment
from scar_sequence.planner import q
from scar.diagnostics.build import transition
from scar_sequence.supplement import goal_reached
from scar_unknown17.audit import initial
OUT=Path('results/stage8')
GAMES=['robot_kingdom','remnant','metropolis']

def shape(graph,target):
    # Canonical rooted tree preserves nominal edge weights and station arity.
    # Shared-DAG signature added so duplicated leaves cannot hide input sharing.
    def subtree(node,seen):
        if node in seen:return 'cycle'
        r=graph.get(node)
        if not r:return 'leaf'
        return [len(r['dependencies']),sorted([[float(n),subtree(x,seen|{node})] for x,n in r['ingredients'].items()],key=lambda x:json.dumps(x))]
    uses={}
    for r in graph.values():
        for x,n in r['ingredients'].items():uses.setdefault(x,[]).append(float(n))
    return digest([subtree(target,set()), sorted([sorted(v) for v in uses.values()])])

def previous():
    targets={g:set() for g in GAMES};shapes=set();details=[];sources={}
    # Published complete datasets include development, previous formal and probes.
    paths=[p for p in Path('results').rglob('cases.json') if 'stage8' not in p.parts]
    for p in paths:
        data=json.loads(p.read_text());sources[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
        for c in data:
            g=c.get('game');goal=c.get('goal',{});target=goal.get('object_id')
            if g in targets and target:targets[g].add(target)
            graph=c.get('recipe_graph',{})
            if graph and target:
                signature=shape(graph,target);shapes.add(signature)
                details.append({'game':g,'target':target,'shape':signature,'family':c.get('family')})
    return targets,shapes,details,sources

def construct(job):
    game,target,seed,graph_signature,folder=job;folder=Path(folder)/f'{game}-{target}';folder.mkdir(parents=True,exist_ok=True)
    with (folder/'engine.log').open('w') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        try:
            env,areas,original=controlled_world(game,seed,folder/'world');graph,leaves,products,order=dependency_graph(env,target)
            if not 2<=len(graph)<=6:raise ValueError('requires2..6recipe nodes')
            if any(env.world.objects[x].category=='container' or env.world.objects[x].usage=='writable' or env.world.objects[x].size is None for x in set(leaves)|set(products)):raise ValueError('nonportable recipe')
            container=max(env.world.container_instances.values(),key=lambda x:x.capacity)
            if sum(env.world.objects[x].size*n for x,n in leaves.items())>container.capacity:raise ValueError('raw allocation exceeds native capacity')
            areas[0].objects[container.id]=1;areas[0].objects[target]=1
            # Public transport variants fixed by official graph hash, not outcomes.
            reverse=int(graph_signature[:2],16)%2;alloc={}
            for i,(oid,n) in enumerate(sorted(leaves.items())):
                area=areas[(i+reverse)%2];area.objects[oid]=n;alloc[oid]=area.id
            stations=sorted({x for r in graph.values() for x in r['dependencies']})
            for x in stations:areas[2].objects[x]=1
            transition(env,'wait');history=[]
            def public(a):
                r=transition(env,a);history.append({k:r[k] for k in ['before','action','after']});return r
            for a in ['inspect '+q(container.name),'pick up '+q(container.name),'equip '+q(container.name),
                'pick up '+q(env.world.objects[target].name),'enter '+q(areas[1].name),'enter '+q(areas[2].name),
                'enter '+q(areas[1].name),'enter '+q(areas[0].name)]:
                if public(a)['semantic_rejection']:raise ValueError('history action rejected: '+a)
            target_action='craft 1 '+q(env.world.objects[target].name)
            if not public(target_action)['semantic_rejection']:raise ValueError('initial failed craft required')
            raw=snapshot(env);goal={'kind':'possess','object_id':target,'name':env.world.objects[target].name,'amount':2}
            witness=[];trial=restore(raw)
            def execute(a):
                r=transition(trial,a)
                if r['semantic_rejection']:raise ValueError('witness rejected: '+a)
                witness.append(a)
            for area in areas[:2]:
                if trial.curr_agents_state['area'][AGENT_ID]!=area.id:execute('enter '+q(area.name))
                for oid,n in sorted(leaves.items()):
                    if alloc[oid]==area.id:execute(f'store {n} {q(env.world.objects[oid].name)} inventory')
            execute('enter '+q(areas[2].name))
            for oid in order:
                execute(f'craft {products[oid]} {q(env.world.objects[oid].name)}')
                execute(('pick up '+q(env.world.objects[oid].name)) if oid==target else f'store {products[oid]} {q(env.world.objects[oid].name)} inventory')
            if len(witness)>35 or not goal_reached(trial,goal):raise ValueError('witness goal or length failed')
            hashes=[];trace=[]
            for repeat in range(2):
                e=restore(raw);run=[]
                for a in witness:run.append(dict(transition(e,a),state_hash=state_digest(e)))
                if not goal_reached(e,goal):raise ValueError('independent witness failed')
                hashes.append(state_digest(e));trace=run
            assert hashes[0]==hashes[1]
            family=digest([game,target,graph,'stage8-native-new-target'])
            case={'id':'stage8-'+family[:16],'family':family,'game':game,'seed':seed,'kind':'craft','cohort':'new',
                'source_cluster':game,'mechanism_cluster':graph_signature,'source':'synthetic_public_allocation_native_rules',
                'types':['multi_stage_craft','capacity','cross_location_transport'],'knowledge':'interaction_discovery',
                'knowledge_limit':'no crafting demonstration; initial acquisition can disclose public numerical target description; dependency closure still requires discovery',
                'target_action':target_action,'goal':goal,'public_goal':f'Obtain at least 2 {goal["name"]} in your possession in total. You already hold one. The previous craft failed. Any valid route is allowed.',
                'history':history,'state_hash':state_digest(restore(raw)),'snapshot_sha256':hashlib.sha256(raw).hexdigest(),
                'initial_snapshot':'initial_states/'+('stage8-'+family[:16])+'.pkl.gz',
                'initialization':{'source_world_hash':original,'areas':[x.id for x in areas],'leaves':leaves,'products':products,
                    'allocations':alloc,'container_id':container.id,'stations':stations,'layout_variant':reverse,
                    'edits':['optional online expansion disabled','original three-area line, light/access enabled','clear initial loose objects,NPCs,combat,hands',
                    'tutorial completion flag','native recipe supply allocation; no action/step rule or recipe modification']},
                'recipe_graph':graph,'materials':leaves,'products':products,'object_names':{k:o.name for k,o in env.world.objects.items()},
                'witness':witness,'witness_length':len(witness),'witness_replay':trace,'witness_replay_hashes':hashes,
                'validated':True,'recoverable':True,'max_steps':40,'split':'test','selection':'predeclared structural order and witness; no policy calls'}
            (folder/'initial.pkl').write_bytes(raw);atomic_json(folder/'case.json',case)
            return {'valid':True,'case':case,'snapshot':str(folder/'initial.pkl')}
        except Exception as e:return {'valid':False,'game':game,'target':target,'reason':str(e)}

def build(runtime,workers):
    policy=json.loads((OUT/'policy_freeze.json').read_text())
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in policy['code_hashes'].items())
    root=Path(runtime);root.mkdir(parents=True,exist_ok=True)
    targets,oldshapes,details,sources=previous();jobs=[];excluded=[]
    with (root/'catalog.log').open('w') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        for gi,g in enumerate(GAMES):
            with tempfile.TemporaryDirectory() as tmp:
                env,_=static_environment(g,82000+gi,tmp)
                for ix,obj in enumerate(sorted(env.world.objects.values(),key=lambda x:x.id)):
                    if not obj.craft_ingredients:continue
                    try:
                        if obj.id in targets[g]:raise ValueError('historical target')
                        graph,_,_,_=dependency_graph(env,obj.id);sig=shape(graph,obj.id)
                        if not 2<=len(graph)<=6:raise ValueError('requires2..6recipe nodes')
                        if sig in oldshapes:raise ValueError('nameless weighted structure matches historical recipe tree')
                        jobs.append((g,obj.id,83000+gi*1000+ix,sig,str(root/'candidates')))
                    except Exception as e:excluded.append({'game':g,'target':obj.id,'reason':str(e)})
    plan={'policy_frozen_at':policy['time_utc'],'games':GAMES,'target_max_per_game':6,'target_total':18,'candidate_order':jobs,
        'historical_sources':sources,'historical_targets':{k:sorted(v) for k,v in targets.items()},
        'rule':'first6 valid native targets pergame, ascending IDs; unique canonical nameless weighted recipe DAG signature acrossnew and historical graphs; one candidate seed, no replacements based on policy score',
        'late_user_override':'old regression Robot10 only; new10-20 families2-3games allowed',
        'source_game_novelty':'all source games previously used; within-game task/state generalization, not new-game generalization'}
    atomic_json(OUT/'selection_plan.json',plan)
    with ProcessPoolExecutor(max_workers=workers,mp_context=mp.get_context('spawn')) as pool:results=list(pool.map(construct,jobs))
    selected=[];seen=set(oldshapes);counts={g:0 for g in GAMES};novel=[]
    for r in results:
        if not r['valid']:excluded.append(r);continue
        c=r['case'];sig=c['mechanism_cluster'];g=c['game']
        if sig in seen:excluded.append({'game':g,'target':c['goal']['object_id'],'reason':'nameless structural duplicate of already selected family'});continue
        if counts[g]>=6:excluded.append({'game':g,'target':c['goal']['object_id'],'reason':'predeclared pergame quota filled'});continue
        counts[g]+=1;seen.add(sig);selected.append(c)
        novel.append({'case_id':c['id'],'game':g,'target':c['goal']['object_id'],'nameless_structure':sig,
            'historical_target_overlap':False,'historical_nameless_structure_overlap':False,
            'resource_distribution_digest':digest(c['initialization']['allocations']),'public_history_digest':digest(c['history']),
            'mother_family':'native target/recipe DAG; shares game engine and synthetic3area template, not independent sourcegame sample'})
        path=OUT/'initial_states'/f'{c["id"]}.pkl.gz';path.parent.mkdir(parents=True,exist_ok=True)
        with gzip.GzipFile(filename=str(path),mode='wb',mtime=0) as f:f.write(Path(r['snapshot']).read_bytes())
    old=[]
    for c in json.loads(Path('results/stage7/cases.json').read_text()):
        if c['game']!='robot_kingdom':continue
        c=copy.deepcopy(c);c['cohort']='regression';old.append(c)
        path=OUT/'initial_states'/f'{c["id"]}.pkl.gz'
        with gzip.GzipFile(filename=str(path),mode='wb',mtime=0) as f:f.write(initial(c))
    assert len(old)==10
    atomic_json(OUT/'cases.json',old+selected)
    atomic_json(OUT/'novelty.json',{'new_count':len(selected),'new_by_game':counts,'new':novel,'excluded':excluded,
        'history_source_graphs':details,'valid_candidates_before_dedup':sum(x['valid'] for x in results),
        'actual_count_not_padded':True,'history_overlap_checks':'target, weighted anonymous structure, allocation+history hashes; unique native target per family',
        'limitations':['Controlled states retain original action/step rules; not natural-reset benchmark.','Sourcegame clusters reused from earlier project; no unseen-game claim.','Same3area initialization template induces dependence; family bootstrap descriptive, source-cluster sensitivity reported.']})
    print(json.dumps({'regression':10,'new':len(selected),'new_by_game':counts,'episodes':5*(10+len(selected))}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--runtime',required=True);p.add_argument('--workers',type=int,default=8);a=p.parse_args();build(a.runtime,a.workers)
