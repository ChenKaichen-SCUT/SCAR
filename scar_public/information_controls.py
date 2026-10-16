"""Explicit stronger controls: pair policy projection and incompatible-leaf count.

These are research controls, not claimed reproductions of a published planner.
Pair-policy projection follows the established small-belief relaxation principle.
Leaf conflicts are proved by exhausting a resource-blind synchronous pair graph;
unfinished work NEVER creates a conflict. A clique of k conflicts needs k leaves.
"""
from collections import deque
from itertools import combinations
from math import inf
from time import perf_counter
from scar_public.finite_planner import State


class ControlLimit(Exception):
    pass


class InformationControls:
    def __init__(self, task, work_limit=150000, pair_limit=4096):
        self.task=task;self.work_limit=work_limit;self.pair_limit=pair_limit
        self.stats=dict(work=0,conflict_pairs=0,unknown_pairs=0,compatible_pairs=0,
            conflict_seconds=0.,pair_seconds=0.,pair_calls=0,pair_fallbacks=0,
            leaf_calls=0,leaf_prunes=0,largest_clique=1)
        self.transition_cache={};self.conflicts={m.name:set() for m in task.models}
        self.conflicts_built=False;self.policy_cache={};self.clique_cache={}
        senses=[a for a in task.actions.values() if a.observation is not None]
        self.has_observations=bool(senses)
        self.sensor_min=tuple(min((a.consumption[i] for a in senses),default=0)
            for i in range(len(task.resources)))

    def charge(self):
        if self.stats['work']>=self.work_limit:raise ControlLimit()
        self.stats['work']+=1

    def step(self,state,action):
        key=state,action
        if key not in self.transition_cache:
            self.charge();self.transition_cache[key]=self.task.step(state,action)
        return self.transition_cache[key]

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
                        for action in self.task.actions:
                            a,_=self.step(pair[0],action)
                            if not self.task.allowed(a):continue
                            b,_=self.step(pair[1],action)
                            if not self.task.allowed(b):continue
                            nxt=(a,b)
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

    def clique(self,names):
        names=frozenset(names)
        if names in self.clique_cache:return self.clique_cache[names]
        # Any greedily constructed clique is a valid lower bound on chromatic
        # number; greedy COLORING would instead give an unsafe upper bound.
        order=sorted(names,key=lambda n:(-len(self.conflicts[n]&names),n));best=()
        for first in order:
            chosen=[first];eligible=names&self.conflicts[first]
            for n in order:
                if n in eligible:chosen.append(n);eligible&=self.conflicts[n]
            if len(chosen)>len(best):best=tuple(chosen)
        value=max(1,len(best));self.clique_cache[names]=value
        self.stats['largest_clique']=max(self.stats['largest_clique'],value)
        return value

    def leaf_lower(self,belief,horizon):
        if all(self.task.goal.holds(s) for _,s in belief):return 0
        self.build_conflicts();self.stats['leaf_calls']+=1
        k=self.clique(n for n,_ in belief);required=(k-1).bit_length()
        observations=horizon if self.has_observations else 0
        # Every actual branch shares the same fixed action consumptions.
        for _,s in belief:
            for r,c in zip(s.resources,self.sensor_min):
                if c:observations=min(observations,r//c)
        if required>observations:self.stats['leaf_prunes']+=1;return inf
        return required

    def pair_value(self,belief,horizon):
        if any(not self.task.allowed(s) for _,s in belief):return inf
        if all(self.task.goal.holds(s) for _,s in belief):return 0
        if horizon==0:return inf
        key=belief,horizon
        if key in self.policy_cache:return self.policy_cache[key]
        self.charge();best=inf
        for action in self.task.actions:
            branches={}
            for name,state in sorted(belief,key=lambda w:w[0]):
                child,obs=self.step(state,action)
                if not self.task.allowed(child):break
                branches.setdefault(obs,set()).add((name,child))
            else:
                branches=[frozenset(ws) for ws in branches.values()]
                if len(branches)==1 and branches[0]==belief:continue
                worst=0
                for b in branches:
                    worst=max(worst,self.pair_value(b,horizon-1))
                    if 1+worst>=best:break
                best=min(best,1+worst)
        self.policy_cache[key]=best
        return best

    def pair_lower(self,belief,horizon):
        start=perf_counter();self.stats['pair_calls']+=1;lower=0
        worlds=sorted(belief,key=lambda w:w[0])
        try:
            for pair in combinations(worlds,min(2,len(worlds))):
                lower=max(lower,self.pair_value(frozenset(pair),horizon))
                if lower==inf:break
        except ControlLimit:self.stats['pair_fallbacks']+=1
        finally:self.stats['pair_seconds']+=perf_counter()-start
        return lower
