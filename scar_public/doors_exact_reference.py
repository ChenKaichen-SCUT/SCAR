"""Independent domain-specific reference for the original Doors source only.

Explicit reachable (position, candidate mask) graph + retrograde min/max Dijkstra.
Not a general planner, not part of the heuristic, and not a timed main baseline.
Returned policy is replayed through the original Boolean action interpreter.
"""
from collections import defaultdict,deque
from heapq import heappop,heappush
from pathlib import Path
from time import perf_counter
import argparse,json
from scar_public.benchmark_suite import configurations,load_case,source_text
from scar_public.contingent_benchmarks import sexpr
from scar_public.symbolic_coverage import LazyCoveragePlanner


def solve(cache):
    start=perf_counter();config=next(c for c in configurations() if c['id']=='doors_5_sNone')
    task,origin=load_case(cache,config);domain,problem,_=source_text(cache,'doors','5')
    schemas={x[1]:dict(zip(x[2::2],x[3::2])) for x in sexpr(domain) if isinstance(x,list) and x and x[0]==':action'}
    assert set(schemas)=={'move','sense-door'}
    assert schemas['move'][':precondition']==['and',['adj','?i','?j'],['at','?i'],['opened','?j']]
    assert schemas['move'][':effect']==['and',['not',['at','?i']],['at','?j']]
    assert schemas['sense-door'][':precondition']==['and',['at','?i'],['adj','?i','?j']]
    assert schemas['sense-door'][':observe']==['opened','?j'] and ':effect' not in schemas['sense-door']
    facts=[{a for i,a in enumerate(task.atom_names) if b&(1<<i)} for b in task.initial_bits]
    common=set.intersection(*facts);adj=defaultdict(list);opened=defaultdict(int)
    for a in sorted(common):
        if a[0]=='adj':adj[a[1]].append(a[2])
    for i,fs in enumerate(facts):
        for a in fs:
            if a[0]=='opened':opened[a[1]]|=1<<i
    initial_positions={a[1] for fs in facts for a in fs if a[0]=='at'};assert len(initial_positions)==1
    goal=next(x[1] for x in sexpr(problem) if isinstance(x,list) and x and x[0]==':goal')
    if goal[0]=='and':assert len(goal)==2;goal=goal[1]
    assert goal[0]=='at'
    initial=(next(iter(initial_positions)),(1<<len(facts))-1);queue=deque([initial]);seen={initial}
    edges=[];reverse=defaultdict(list)
    while queue:
        state=queue.popleft();position,mask=state
        if position==goal[1]:continue
        for target in adj[position]:
            true=mask&opened[target];false=mask&~opened[target]
            options=[]
            if not false:options.append(('move '+position+' '+target,{():(target,mask)}))
            if true and false:options.append(('sense-door '+position+' '+target,{(True,):(position,true),(False,):(position,false)}))
            for action,children in options:
                index=len(edges);edges.append(dict(parent=state,action=action,children=children))
                for child in children.values():
                    reverse[child].append(index)
                    if child not in seen:seen.add(child);queue.append(child)
    built=perf_counter();remaining=[len(e['children']) for e in edges];worst=[0]*len(edges)
    distances={s:0 for s in seen if s[0]==goal[1]};heap=[(0,s) for s in distances];settled=set();chosen={}
    # heapify is required: goal-state insertion follows a set, not sorted order.
    from heapq import heapify
    heapify(heap)
    while heap:
        value,state=heappop(heap)
        if state in settled:continue
        settled.add(state)
        if state==initial:break
        for index in reverse[state]:
            remaining[index]-=1;worst[index]=max(worst[index],value)
            if remaining[index]:continue
            edge=edges[index];parent=edge['parent'];candidate=1+worst[index]
            if candidate<distances.get(parent,float('inf')):
                distances[parent]=candidate;chosen[parent]=index;heappush(heap,(candidate,parent))
    assert initial in settled
    memo={}
    def policy(state):
        if state[0]==goal[1]:return {'stop':True}
        if state not in memo:
            e=edges[chosen[state]]
            memo[state]=dict(action=e['action'],branches={o:policy(child) for o,child in e['children'].items()})
        return memo[state]
    tree=policy(initial);value=LazyCoveragePlanner(task,'single').verify(task.belief,1000,tree)
    assert value==distances[initial]
    certificate=[]
    for s in sorted(memo):
        e=edges[chosen[s]];certificate.append(dict(state=s,value=distances[s],action=e['action'],
            branches=[dict(observation=o,state=child,value=distances[child]) for o,child in e['children'].items()]))
    return dict(config=config,source=origin,optimal_worst_case_depth=value,policy_verified=True,
        explicit_belief_states=len(seen),hyperedges=len(edges),settled_states=len(settled),policy_nodes=len(memo),
        build_seconds=built-start,total_seconds=perf_counter()-start,
        scope='Domain-specific explicit reference, separate from generic planner timing and heuristics.',
        initial=initial,policy_certificate=certificate)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=solve(a.cache);a.output.write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k not in ('policy_certificate','source','config')}))
