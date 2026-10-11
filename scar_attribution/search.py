"""Bounded real-engine search; every positive answer has a twice-replayed path."""
from collections import Counter, deque
import heapq
import math
import shlex
import time

from scar.environment import AGENT_ID, restore, snapshot, state_digest
from scar.io import digest
from scar_v3.hard import base_id, goal_reached, relevant_actions
from scar_attribution.oracle import craft_counts, area_of


def execute(env,action):
    obs,reward,done,info=env.step({AGENT_ID:action})
    env.update_scores(reward)
    return bool(done),bool(info.get("step_invalid_action",{}).get(AGENT_ID,False))


def physical_key(env):
    return digest({"world":env.world.to_dict(),"agents":[a.to_dict() for a in env.agents],"state":env.curr_agents_state})


def key(env):
    # Include clock and complete physical/quest/combat state. Omits observation
    # wording, cumulative scores and provenance-only dependency tracker.
    return digest([physical_key(env),str(env.curr_time),env.steps,env.rng.getstate()])


def recipe_scope(env,goal):
    materials=Counter();products=Counter()
    def visit(oid,n,stack=()):
        if oid in stack or len(stack)>=6:return
        materials[oid]=max(materials[oid],n)
        obj=env.world.objects.get(oid)
        if obj and obj.craft_ingredients:
            products[oid]=max(products[oid],max(1,int(math.ceil(n))))
            for ing,count in obj.craft_ingredients.items():visit(ing,n*count,stack+(oid,))
    if goal["kind"]=="possess":visit(goal["object_id"],goal.get("amount",1))
    materials["obj_key"]=1;materials["obj_torch"]=1
    return dict(materials),dict(products)


def distances(env):
    start=area_of(env).id;ds={start:0};q=deque([start])
    while q:
        current=q.popleft()
        for nxt in env.world.area_instances[current].neighbors:
            if nxt not in ds:ds[nxt]=ds[current]+1;q.append(nxt)
    return ds


def heuristic(env,goal):
    """Non-admissible resource/topology guidance, never a claimed value oracle."""
    if goal_reached(env,goal):return 0
    ds=distances(env);agent=env.agents[0];hands=sum(agent.items_in_hands.values())
    if goal["kind"]=="location":return ds.get(goal["area_id"],30)+(1 if hands>1 and not agent.items_in_hands.get("obj_key") else 0)
    counts=craft_counts(env)
    def cost(oid,n,stack=()):
        if counts[oid]>=n:return 0
        if oid in stack or len(stack)>=5:return 25
        remaining=n-counts[oid];options=[]
        for aid,area in env.world.area_instances.items():
            if sum(v for k,v in area.objects.items() if base_id(env,k)==oid)>=remaining:
                # Bulk store into equipped inventory or hand pickup.
                options.append(ds.get(aid,30)+1+(1 if hands>1 and not agent.inventory.container else 0))
        for cid,c in env.world.container_instances.items():
            if c.inventory.get(oid,0)>=remaining:
                loc=next((aid for aid,ar in env.world.area_instances.items() if cid in ar.objects),None)
                if loc:options.append(ds.get(loc,30)+1+(1 if hands>1 else 0))
        obj=env.world.objects.get(oid)
        if obj and obj.craft_ingredients:
            bench=min((ds.get(aid,30) for aid,area in env.world.area_instances.items() if all(area.objects.get(d,0)>0 for d in obj.craft_dependencies)),default=30)
            ingredients=sum(cost(i,n*v,stack+(oid,)) for i,v in obj.craft_ingredients.items())
            options.append(2+bench+ingredients)
        return min(options,default=30)
    return cost(goal["object_id"],goal.get("amount",1))


def replay_path(start,actions,goal):
    endings=[];histories=[]
    for _ in range(2):
        env=restore(start);rows=[]
        for action in actions:
            done,invalid=execute(env,action)
            rows.append({"action":action,"state_digest":state_digest(env),"physical_goal":goal_reached(env,goal),"engine_invalid":invalid})
            if done and not rows[-1]["physical_goal"]:return {"verified":False,"reason":"terminated_before_goal"}
        endings.append(state_digest(env));histories.append(rows)
    return {"verified":bool(actions and goal_reached(env,goal) and endings[0]==endings[1]),"final_digest":endings[0],"steps":histories[0]}


def bounded(start,goal,max_depth=10,max_expanded=256,max_generated=4096,max_frontier=1024):
    tick=time.monotonic();env=restore(start)
    if goal_reached(env,goal):return {"status":"ALREADY_REACHED","path":[],"distance":0,"expanded":0,"generated":0,"seconds":time.monotonic()-tick}
    materials,products=recipe_scope(env,goal)
    q=[(2*heuristic(env,goal),0,0,start,[])];seen={key(env):0};serial=0;expanded=generated=pruned=0
    best=None
    while q and expanded<max_expanded and generated<max_generated:
        _,g,_,data,path=heapq.heappop(q);env=restore(data);expanded+=1
        if len(path)>=max_depth:continue
        for action in relevant_actions(env,goal,materials,products):
            if generated>=max_generated:break
            child=restore(data);done,invalid=execute(child,action);generated+=1
            if invalid:continue
            newpath=path+[action]
            if goal_reached(child,goal):
                best=newpath;break
            if done:continue
            k=key(child);depth=len(newpath)
            if seen.get(k,10**9)<=depth:continue
            seen[k]=depth;serial+=1
            heapq.heappush(q,(depth+2*heuristic(child,goal),depth,serial,snapshot(child),newpath))
        if best is not None:break
        if len(q)>max_frontier:
            pruned+=len(q)-max_frontier;q=heapq.nsmallest(max_frontier,q);heapq.heapify(q)
    verification=replay_path(start,best,goal) if best else None
    if verification and not verification["verified"]:raise AssertionError("Search path did not replay exactly")
    return {"status":"VERIFIED" if best else "UNKNOWN","path":best,"distance":len(best) if best else None,"expanded":expanded,"generated":generated,"frontier":len(q),"frontier_pruned":pruned,"depth_limit":max_depth,"seconds":time.monotonic()-tick,"verification":verification,"minimality":"Shortest found witness only; bounded weighted search, no impossibility/optimality claim"}
