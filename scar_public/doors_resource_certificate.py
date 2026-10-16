"""Independent domain-specific certificate for Doors with <=4 sensor actions.

Not a general heuristic or a novelty claim. Check that no terminal action
history can complete two models, then use the elementary binary-tree leaf cap.
"""
import argparse,json
from collections import defaultdict,deque
from itertools import combinations
from pathlib import Path
from time import perf_counter
from scar_public.benchmark_suite import configurations,load_case,source_text
from scar_public.contingent_benchmarks import sexpr


def certify(cache):
    started=perf_counter()
    c=next(c for c in configurations() if c['id']=='doors_5_s4')
    task,origin=load_case(cache,c)
    domain,problem,_=source_text(cache,'doors','5')
    schemas={x[1]:dict(zip(x[2::2],x[3::2])) for x in sexpr(domain)
        if isinstance(x,list) and x and x[0]==':action'}
    assert set(schemas)=={'move','sense-door'}
    assert schemas['move'][':precondition']==['and',['adj','?i','?j'],['at','?i'],['opened','?j']]
    assert schemas['move'][':effect']==['and',['not',['at','?i']],['at','?j']]
    assert ':observe' not in schemas['move']
    assert schemas['sense-door'][':precondition']==['and',['at','?i'],['adj','?i','?j']]
    assert schemas['sense-door'][':observe']==['opened','?j'] and ':effect' not in schemas['sense-door']
    facts=[{a for i,a in enumerate(task.atom_names) if b&(1<<i)} for b in task.initial_bits]
    positions=[{a[1] for a in fs if a[0]=='at'} for fs in facts]
    assert len(set(map(frozenset,positions)))==1 and len(positions[0])==1
    start=next(iter(positions[0]));graphs=[{a[1:] for a in fs if a[0]=='adj'} for fs in facts]
    assert all(g==graphs[0] for g in graphs)
    goal=next(x[1] for x in sexpr(problem) if isinstance(x,list) and x and x[0]==':goal')
    if goal[0]=='and':assert len(goal)==2;goal=goal[1]
    assert goal[0]=='at';target=goal[1]
    adj=defaultdict(list)
    for x,y in graphs[0]:adj[x].append(y)
    opened=[{a[1] for a in fs if a[0]=='opened'} for fs in facts]
    conflicts=[]
    for i,j in combinations(range(len(facts)),2):
        allowed=opened[i]&opened[j];queue=deque([start]);seen={start}
        while queue:
            x=queue.popleft()
            for y in adj[x]:
                if y in allowed and y not in seen:seen.add(y);queue.append(y)
        assert target not in seen, 'Not a complete conflict graph; leaf-size-one proof unavailable'
        conflicts.append((i,j))
    sensors=c['sensor_budget'];models=len(task.models)
    assert models>2**sensors
    return dict(config=c,source=origin,models=models,sensor_budget=sensors,
        checked_pair_conflicts=len(conflicts),maximum_models_per_terminal_history=1,
        maximum_boolean_observation_leaves=2**sensors,
        conclusion='NO_STRONG_POLICY_FOR_ANY_H_WITH_THIS_SENSOR_BUDGET',
        elapsed_seconds=perf_counter()-started,
        argument='A common terminal action history must give a move path through cells open in every '
            'remaining model. For every model pair this common-open graph has no start-goal path. '
            'Observations have no effects; removing them cannot create such a path. Thus each terminal '
            'history covers at most one model. A binary observation tree of sensor depth at most four '
            'has at most 16 leaves, fewer than the 25 initial models. All models require completion.',
        scope='Domain-specific independent certificate, not a timed generic baseline or novel bound.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=certify(a.cache);a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2));print(json.dumps(result))
