"""Hidden-state evaluation only; never imported by either decision controller."""
from collections import Counter
from scar.environment import AGENT_ID
from scar.io import digest
from scar_v3.hard import owned,base_id
from scar_v3.state import parse_action
from scar_sequence.supplement import goal_reached


def physical(env,task):
    agent=env.agents[0];world=env.world
    area=world.area_instances[env.curr_agents_state['area'][AGENT_ID]]
    relevant=set(task.get('materials',{}))|set(task.get('products',{}))
    if task['goal'].get('object_id'):relevant.add(task['goal']['object_id'])
    global_counts=Counter(agent.items_in_hands)+Counter(agent.equipped_items_in_limb)
    for a in world.area_instances.values():global_counts.update(a.objects)
    for c in world.container_instances.values():global_counts.update(c.inventory)
    names={oid:world.objects[oid].name for oid in relevant if oid in world.objects}
    canonical={oid:sum(n for x,n in global_counts.items() if base_id(env,x)==oid) for oid in relevant}
    conditions={}
    for oid,recipe in task.get('recipe_graph',{}).items():
        conditions[oid]={'ingredients':{k:owned(env,k)>=v for k,v in recipe['ingredients'].items()},
                         'stations':{k:area.objects.get(k,0)>0 for k in recipe['dependencies']}}
    containers={c.name:{'location':next((ar.name for ar in world.area_instances.values() if cid in ar.objects),None),
        'carried':cid in agent.items_in_hands or cid in agent.equipped_items_in_limb,
        'transfer_accessible':cid in area.objects or cid in agent.items_in_hands or cid in agent.equipped_items_in_limb,
        'contents':{world.auxiliary['obj_name_to_id'] and next((name for name,x in world.auxiliary['obj_name_to_id'].items() if x==oid),oid):n for oid,n in c.inventory.items()}}
        for cid,c in world.container_instances.items() if c.inventory or cid in area.objects or cid in agent.items_in_hands or cid in agent.equipped_items_in_limb}
    accessible={names.get(oid,oid):owned(env,oid) for oid in relevant}
    state={'location':area.name,'hands':dict(agent.items_in_hands),'equipped':dict(agent.equipped_items_in_limb),
       'accessible':accessible,'world_counts':canonical,'containers':containers,'conditions':conditions,
       'crafted':dict(env.curr_agents_state.get('objects_crafted',{}).get(AGENT_ID,{})),
       'tutorial_stage':env.curr_agents_state.get('tutorial_stage',{}).get(AGENT_ID,0),
       'goal':goal_reached(env,task['goal'])}
    state['resource_hash']=digest({k:state[k] for k in ['location','hands','equipped','accessible','world_counts','containers']})
    return state


def metrics(before,after,action,task,decision):
    p=parse_action(action)
    oid=next((oid for oid in task.get('recipe_graph',{}) if p.target==oid.removeprefix('obj_')),None)
    # Names can differ from IDs. Resolve against evaluator's per-task display map.
    oid=next((k for k,v in task.get('object_names',{}).items() if v==p.target),oid)
    cond=before['conditions'].get(oid,{})
    craft_test=p.verb=='craft' and bool(cond)
    dependency_violation=craft_test and not all(v for group in cond.values() for v in group.values())
    released=sum(not all(v for g in b.values() for v in g.values()) and
                 all(v for g in after['conditions'][o].values() for v in g.values())
                 for o,b in before['conditions'].items())
    target=task['goal'].get('object_id')
    target_name=task['goal'].get('name')
    goal_delta=(after['accessible'].get(target_name,0)-before['accessible'].get(target_name,0)) if target else after['tutorial_stage']-before['tutorial_stage']
    # Detect actual unaccounted destruction, excluding expected crafting inputs.
    expected=task.get('recipe_graph',{}).get(oid,{}).get('ingredients',{}) if p.verb=='craft' else {}
    made=max(0,after['crafted'].get(oid,0)-before['crafted'].get(oid,0)) if oid else 0
    destroyed={k:before['world_counts'][k]-after['world_counts'].get(k,0)-expected.get(k,0)*made
               for k in before['world_counts'] if before['world_counts'][k]-after['world_counts'].get(k,0)>expected.get(k,0)*made+1e-8}
    access_error=False;access_test=False
    if p.verb in {'take out','store','discard'} and p.args:
        name=p.args[-1]
        if name=='inventory':
            access_test=True;access_error=not any(c['carried'] for c in before['containers'].values())
        elif name in before['containers']:
            access_test=True;access_error=not before['containers'][name]['transfer_accessible']
    table=decision.get('structured',{}).get('resource_table',{})
    false_access=[]
    for name,c in table.get('containers',{}).items():
        if name in (table.get('state',{}).get('hands') or {}) or name in (table.get('state',{}).get('equipment') or {}):
            if name in before['containers'] and not before['containers'][name]['carried']:false_access.append(name)
    return {'craft_condition_test':int(craft_test),'dependency_violation':int(dependency_violation),
        'conditions_released':released,'physical_goal_delta':goal_delta,
        'unaccounted_resource_destruction':destroyed,'container_access_test':int(access_test),
        'container_access_error':int(access_error),'false_carried_claims':false_access,
        'transfer_action':p.verb in {'store','take out','drop','pick up','discard'},
        'resource_hash_before':before['resource_hash'],'resource_hash_after':after['resource_hash'],
        'loss_scope':'Actual world quantity disappearance beyond expected recipe consumption; future respawn/alternative solutions not ruled out.'}
