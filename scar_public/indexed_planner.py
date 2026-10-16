"""Shared exact-search engineering: static grounding, action index, bounded tails."""
from collections import deque
from itertools import combinations
from math import inf
from time import perf_counter
from scar_public.budgeted_planner import BudgetedPlanner
from scar_public.threshold_search import Record
from scar_public.information_controls import InformationControls,ControlLimit
from scar_public.finite_planner import State
from scar_public.symbolic_task import ev


class IndexedControls(InformationControls):
    def build_conflicts(self):
        if self.conflicts_built:return
        start=perf_counter();self.conflicts_built=True
        worlds=sorted(self.task.belief,key=lambda w:w[0])
        try:
            for (name1,s1),(name2,s2) in combinations(worlds,2):
                initial=(State(s1.symbols,()),State(s2.symbols,()))
                queue=deque([initial]);seen={initial};compatible=False;expanded=0
                try:
                    while queue:
                        pair=queue.popleft()
                        if all(self.task.goal.holds(s) for s in pair):compatible=True;break
                        if expanded>=self.pair_limit:raise ControlLimit()
                        self.charge();expanded+=1
                        for action in self.task.applicable(pair[0]):
                            a,_=self.step(pair[0],action)
                            b,_=self.step(pair[1],action)
                            if not self.task.allowed(b):continue
                            nxt=a,b
                            if nxt not in seen:seen.add(nxt);queue.append(nxt)
                except ControlLimit:
                    self.stats['unknown_pairs']+=1
                    if self.stats['work']>=self.work_limit:break
                    continue
                if compatible:self.stats['compatible_pairs']+=1
                else:
                    self.stats['conflict_pairs']+=1
                    self.conflicts[name1].add(name2);self.conflicts[name2].add(name1)
        finally:self.stats['conflict_seconds']+=perf_counter()-start


class IndexedPlanner(BudgetedPlanner):
    def __init__(self,task):
        super().__init__(task,'leaf');self.control=IndexedControls(task)
        self.tail_steps=0;self.tail_seconds=0.;self.tail_limit=65536
        self.engine_stats=dict(edge_action_candidates=0,uninformative_senses=0,tail_stops=0)

    def hmax(self,state):
        bits=state.symbols[0]
        if bits in self.hmax_cache:return self.hmax_cache[bits]
        if self.cost_stats['hmax_work']>=2000000:
            self.cost_stats['hmax_fallbacks']+=1;return 0
        return super().hmax(state)

    def known_world(self,world,budget):
        rec=self.world_records.setdefault(world,Record())
        if rec.upper<inf or rec.lower>budget:return rec
        if not self.allowed(world[1]):rec.lower=inf;return rec
        if self.goal.holds(world[1]):rec.lower=rec.upper=0;rec.policy={'stop':True};return rec
        rec.lower=max(rec.lower,self.hmax(world[1]))
        if rec.lower>budget:return rec
        if self.bfs_used>=4096 or self.tail_steps>=self.tail_limit or self.tail_seconds>=1.:
            self.cost_stats['bfs_fallbacks']+=1;return rec
        started=perf_counter();deadline=started+min(.05,1.-self.tail_seconds)
        queue=deque([(world,0)]);parents={world:None};expanded=steps=0;found=None
        def stop(depth):
            rec.lower=max(rec.lower,depth);self.engine_stats['tail_stops']+=1
            self.cost_stats['bfs_fallbacks']+=1;return rec
        try:
            while queue:
                current,depth=queue.popleft()
                if expanded>=64 or self.bfs_used>=4096:return stop(depth)
                expanded+=1;self.bfs_used+=1;self.bound_stats['single_nodes']+=1
                if depth>=budget:continue
                for action in self.task.applicable(current[1]):
                    # Information without state change cannot help a known world.
                    if not self.task.actions[action].effects:continue
                    if steps>=4096 or self.tail_steps>=self.tail_limit or perf_counter()>=deadline:return stop(depth)
                    steps+=1;self.tail_steps+=1;child,obs=self._step(current,action)
                    if not self.allowed(child[1]) or child in parents:continue
                    parents[child]=current,action,obs
                    if self.goal.holds(child[1]):found=child;break
                    queue.append((child,depth+1))
                if found is not None:break
            if found is None:rec.lower=max(rec.lower,budget+1);return rec
            current=found;policy={'stop':True};distance=0
            while True:
                suffix=self.world_records.setdefault(current,Record())
                suffix.lower=suffix.upper=distance;suffix.policy=policy
                if parents[current] is None:break
                parent,action,obs=parents[current]
                policy=dict(action=action,branches={obs:policy});distance+=1;current=parent
            return rec
        finally:
            elapsed=perf_counter()-started;self.tail_seconds+=elapsed
            self.search_stats['singleton_seconds']+=elapsed

    def edges(self,belief):
        if belief in self.edge_cache:return self.edge_cache[belief]
        start=perf_counter();edges=[];worlds=sorted(belief,key=lambda w:w[0])
        try:
            for action in self.task.applicable(worlds[0][1]):
                self.engine_stats['edge_action_candidates']+=1;a=self.task.actions[action]
                if not a.effects:
                    if a.observation is None or len({ev(a.observation,s.symbols[0]) for _,s in worlds})<2:
                        self.engine_stats['uninformative_senses']+=1;continue
                branches={}
                for world in worlds:
                    child,obs=self._step(world,action)
                    if not self.allowed(child[1]):break
                    branches.setdefault(obs,set()).add(child)
                else:
                    branches={o:frozenset(ws) for o,ws in branches.items()}
                    if len(branches)==1 and next(iter(branches.values()))==belief:continue
                    edges.append((action,branches))
            self.search_stats['edges_built']+=len(edges);self.edge_cache[belief]=edges;return edges
        finally:self.search_stats['edge_seconds']+=perf_counter()-start

    def statistics(self):
        return dict(super().statistics(),indexed_engine=dict(self.engine_stats,tail_steps=self.tail_steps,
            tail_seconds=self.tail_seconds,applicability=dict(self.task.index_stats)))
