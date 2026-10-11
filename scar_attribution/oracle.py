"""Evaluator-only action conditions, with no plans or next-action recommendations."""
from collections import Counter
import re

from scar.environment import AGENT_ID
from scar.diagnostics.scoring import score_candidate
from scar_v3.hard import base_id, owned, goal_reached
from scar_v3.state import parse_action
from scar_v3.learning import Prediction


def area_of(env):
    return env.world.area_instances[env.curr_agents_state["area"][AGENT_ID]]


def craft_counts(env, writable=False):
    agent=env.agents[0]
    stores=[agent.items_in_hands]
    if agent.inventory.container:
        stores.append(agent.inventory.items)
    stores += [env.world.container_instances[k].inventory for k in agent.items_in_hands if k in env.world.container_instances]
    counts=Counter()
    for store in stores:
        for k,v in store.items():
            counts[base_id(env,k) if writable else k]+=v
    return counts


def conditions(env, action, truth=None):
    """All simultaneous craft/enter blockers; other actions expose checked facets.

    Acceptance always comes from the original rule dispatch. For unsupported
    verbs, first blocking feedback is retained but no completeness is claimed.
    Craft follows the engine's >=one-copy rule (requested quantities are clamped).
    """
    truth=truth if truth is not None else score_candidate(env,action)
    a=parse_action(action); agent=env.agents[0]; area=area_of(env)
    ids=env.world.auxiliary["obj_name_to_id"]; oid=ids.get(a.target)
    facts={};complete=False
    def add(key,met,**details):facts[key]={"met":bool(met),**details}
    if truth["engine_invalid"]:
        add("signature.valid",False);complete=True
    elif a.verb=="craft" and len(a.args)==2:
        amount=a.args[0]; obj=env.world.objects.get(base_id(env,oid)) if oid else None
        add("amount.positive_integer",amount.isdigit() and int(amount)>0)
        add("recipe.exists",obj is not None and bool(obj.craft_ingredients))
        if obj and obj.craft_ingredients:
            counts=craft_counts(env,obj.usage=="writable")
            for dep in obj.craft_dependencies:
                name=env.world.objects[dep].name
                add("ground:"+name,area.objects.get(dep,0)>0,object_id=dep)
            for ing,n in sorted(obj.craft_ingredients.items()):
                name=env.world.objects[ing].name if ing in env.world.objects else ing
                add(f"resource:{name}>={n:g}",counts[ing]>=n,object_id=ing,required_amount=n,available=counts[ing])
        complete=True
    elif a.verb=="enter" and len(a.args)==1:
        blocking=[npc for npc,cs in env.curr_agents_state.get("active_combats",{}).get(AGENT_ID,{}).items() if cs.get("area_id")==area.id and npc in env.world.npc_instances]
        add("combat.clear",not blocking)
        path=next((v for k,v in area.neighbors.items() if env.world.area_instances[k].name==a.target),None)
        add("target.neighbor",path is not None)
        if path is not None and path.locked:
            # Exact engine requirement is a key in HAND, not in any container.
            add("resource:key>=1","obj_key" in agent.items_in_hands,scope="hand_only")
        complete=True
    elif a.verb=="pick up" and len(a.args)==1:
        add("target.ground",oid and area.objects.get(oid,0)>0)
        add("hands.space",sum(agent.items_in_hands.values())<=1)
        complete=True
    elif a.verb=="drop" and len(a.args)==1:
        add("target.held",oid and agent.items_in_hands.get(oid,0)>0);complete=True
    elif a.verb=="take out" and len(a.args)==2:
        add("hands.space",sum(agent.items_in_hands.values())<=1)
        name=a.args[-1];cid=ids.get(name)
        c=agent.inventory.container if name=="inventory" else env.world.container_instances.get(cid)
        accessible=c is not None and (name=="inventory" or cid in area.objects or cid in agent.items_in_hands or (agent.inventory.container and cid==agent.inventory.container.id))
        add("container.accessible",accessible)
        contents=agent.inventory.items if name=="inventory" else c.inventory if c else {}
        add("container.has_target",oid and contents.get(oid,0)>0);complete=True
    elif a.verb=="equip" and len(a.args)==1:
        add("target.held",oid and agent.items_in_hands.get(oid,0)>0)
        if oid in env.world.container_instances:
            add("inventory.slot_free",not any(x in env.world.container_instances for x in agent.equipped_items_in_limb));complete=True
    if not complete:
        add("action_rule.accepted",not truth["semantic_rejection"],source="official_dispatch_first_feedback")
    conjunction=all(x["met"] for x in facts.values())
    return {"action":action,"rejected":truth["semantic_rejection"],"engine_invalid":truth["engine_invalid"],"feedback":truth["feedback"],"facts":facts,"violated":[k for k,v in facts.items() if not v["met"]],"complete_conditions":complete,"condition_dispatch_match":conjunction==not_rejected(truth) if complete else None}


def not_rejected(truth):return not truth["semantic_rejection"]


class OraclePreconditions:
    """Narrow predict-only adapter. Cannot return routes or candidate actions."""
    def __init__(self, env):self.env,self.cache=env,{}

    def predict(self,action,state=None):
        if action not in self.cache:self.cache[action]=conditions(self.env,action)
        row=self.cache[action]
        return Prediction(status="REJECT" if row["rejected"] else "SUPPORTED",failure_probability=float(row["rejected"]),confidence=1.,violated=row["violated"],support=["offline_original_action_rule_conditions"],rules=["oracle_preconditions"])


def progress(before,after):
    repaired=[k for k,v in before["facts"].items() if not v["met"] and after["facts"].get(k,{}).get("met",False)]
    regressed=[k for k,v in before["facts"].items() if v["met"] and k in after["facts"] and not after["facts"][k]["met"]]
    # Enter's hand-key requirement disappears when the edge is unlocked.
    if "resource:key>=1" in before["violated"] and "resource:key>=1" not in after["facts"] and not after["rejected"]:
        repaired.append("resource:key>=1")
    return {"repaired":repaired,"regressed":regressed,"net_blocker_reduction":len(before["violated"])-len(after["violated"]),"target_released":before["rejected"] and not after["rejected"]}
