"""Authoritative evaluator only; hidden truth never passed to an agent."""
import copy
import re
from collections import Counter
from scar.environment import AGENT_ID,state_digest
from scar_v3.hard import owned,base_id
from scar_v3.state import parse_action
from scar.agents.scar.state import feedback_text


def physical(env,target):
    world=env.world;agent=env.agents[0];all_counts=Counter(agent.items_in_hands)+Counter(agent.equipped_items_in_limb)
    for area in world.area_instances.values():all_counts.update(area.objects)
    for container in world.container_instances.values():all_counts.update(container.inventory)
    canonical=Counter()
    for oid,count in all_counts.items():canonical[base_id(env,oid)]+=count
    return dict(state_hash=state_digest(env),health=agent.hp,
        possessed={oid:owned(env,oid) for oid in world.objects},world_counts=dict(canonical),
        crafted=copy.deepcopy(env.curr_agents_state.get('objects_crafted',{}).get(AGENT_ID,{})),
        target_owned=owned(env,target))


def transition(before,after,action,obs,world):
    p=parse_action(action);fb=feedback_text(obs['text']);oid=world.auxiliary['obj_name_to_id'].get(p.target)
    made={o:n-before['crafted'].get(o,0) for o,n in after['crafted'].items() if n>before['crafted'].get(o,0)}
    recipe=world.objects.get(oid) if oid else None
    losses={o:n-after['world_counts'].get(o,0) for o,n in before['world_counts'].items() if n>after['world_counts'].get(o,0)+1e-8}
    expected={o:v*made.get(oid,0) for o,v in recipe.craft_ingredients.items()} if recipe and p.verb=='craft' else {}
    excess={o:n-expected.get(o,0) for o,n in losses.items() if n>expected.get(o,0)+1e-8}
    return dict(invalid=bool(re.search(r'Cannot |Invalid |blocked the way out|not enough|do not have|not found',fb,re.I)),
        craft=p.verb=='craft',craft_failed=p.verb=='craft' and not made,
        material_rejection=p.verb=='craft' and bool(re.search(r'not enough|insufficient|do not have sufficient|missing.*material',fb,re.I)),
        station_rejection=p.verb=='craft' and 'Missing necessary' in fb,
        requested_quantity=int(p.args[0]) if p.verb=='craft' and p.args and p.args[0].isdigit() else None,
        actual_production=made,actual_world_quantity_decrease=losses,
        carried_quantity_decrease={o:n-after['possessed'].get(o,0) for o,n in before['possessed'].items() if n>after['possessed'].get(o,0)+1e-8},
        excess_loss_beyond_nominal=excess,
        consumption_scope='world decrease includes environmental dynamics; carried decrease includes transfers; neither alone proves causal craft consumption')


def native_step(env,action,target):
    """Read-only dispatch observer isolates action effects from later step dynamics.

    Original dispatch is called once with unchanged arguments. No RNG is drawn.
    The observer is removed before snapshots; uninstrumented replay checks parity.
    """
    original=env.action_rule_engine.dispatch;action_effect={}
    def observed(*args,**kwargs):
        before=physical(env,target)
        result=original(*args,**kwargs)
        after=physical(env,target)
        action_effect.update(before=before,after=after)
        return result
    env.action_rule_engine.dispatch=observed
    try:result=env.step({AGENT_ID:action})
    finally:env.action_rule_engine.dispatch=original
    return result,action_effect
