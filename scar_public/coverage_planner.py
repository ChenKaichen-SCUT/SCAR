"""Strong contingent search, general terminal observations, and k-world controls.

The old observable-completion solver is left intact. Here actions may continue
in already-goal worlds while other worlds are unfinished; stopping still requires
the actual goal in EVERY world. Failed preconditions are represented as forbidden
successors by the benchmark adapter, not as free informative observations.
"""
from itertools import combinations
from math import inf

from scar_public.control_capacity import ControlCapacity
from scar_public.information_bound import InformationBoundPlanner


class PolicyCoverage(ControlCapacity):
    """Optimistically absorb goal worlds without leaking goal truth to search."""
    def __init__(self,models,goal,allowed,symbol_indices=(),forget_resources=False):
        self.indices=tuple(symbol_indices)
        if len(set(self.indices))!=len(self.indices) or any(type(i)!=int or i<0 for i in self.indices):
            raise ValueError('invalid control projection')
        if any(i>=len(m.domains) for m in models for i in self.indices):
            raise ValueError('projection outside schema')
        self.forget_resources=forget_resources
        self.models,self.goal,self.allowed=models,goal,allowed
        self.model_count=len(models)
        self.channels,self.cache,self.fallback={},{},None
        self._stats=dict(compiled_transitions=0,dp_nodes=0,lower_calls=0,
            inapplicable_queries=0,disabled_reason=None,abstract_states=0,
            action_channels=0,observation_channels=0)
        if any(cost!=1 for m in models for cost in m.costs.values()):
            self._stats['disabled_reason']='requires unit costs';return
        temporary={}
        for m in models:
            for (state,action),case in m.lookup.items():
                if not allowed(state) or goal.holds(state):continue
                self._stats['compiled_transitions']+=1
                successor=case.apply(state)
                if not allowed(successor):continue
                record=temporary.setdefault((self.project(state),action),[set(),{}])
                if goal.holds(successor):record[0].add(m.name)
                else:
                    bucket=record[1].setdefault(case.observation,[set(),set()])
                    bucket[0].add(m.name);bucket[1].add(self.project(successor))
        for (key,action),(goals,observations) in temporary.items():
            if any(len(states)!=1 for _,states in observations.values()):
                self._stats['disabled_reason']='ambiguous nonterminal successor projection'
                self.channels.clear();return
            channels=tuple((len(names),next(iter(states))) for names,states in observations.values())
            self.channels.setdefault(key,[]).append((action,len(goals),channels))
            self._stats['action_channels']+=1
            self._stats['observation_channels']+=len(channels)
        self._stats['abstract_states']=len(self.channels)

    def project(self,state):
        return (() if self.forget_resources else state.resources),tuple(state.symbols[i] for i in self.indices)

    def lower(self,belief,horizon):
        self._stats['lower_calls']+=1
        if any(not self.allowed(s) for _,s in belief):return inf
        # Removing already-goal worlds relaxes obligations. The real search must
        # still execute its policy in them, and verify their final goals/constraints.
        live=[(name,s) for name,s in belief if not self.goal.holds(s)]
        if not live:return 0
        keys={self.project(s) for _,s in live}
        if self._stats['disabled_reason'] or len(keys)!=1:
            self._stats['inapplicable_queries']+=1;return 0
        key=next(iter(keys));required=len({n for n,_ in live})
        for t in range(1,horizon+1):
            if self.capacity(key,t)>=required:return t
        return inf


class CoveragePlanner(InformationBoundPlanner):
    """Identical minimax search and exact singleton tails; alternative bounds."""
    MODES=('single','pair_exact','k3','coverage','resource_blind')

    def __init__(self,models,goal,allowed=lambda s:True,*,mode='coverage',indices=()):
        if mode not in self.MODES:raise ValueError(mode)
        super().__init__(models,goal,allowed,mode='single' if mode in ('coverage','resource_blind','k3') else mode)
        self.variant=mode
        self.k_cache={};self.k_nodes=self.k_queries=0
        if mode in ('coverage','resource_blind'):
            self.coverage=PolicyCoverage(models,goal,allowed,indices,forget_resources=mode=='resource_blind')

    def branches(self,belief,action):
        outcomes={}
        for name,state in sorted(belief,key=lambda w:(w[0],repr(w[1]))):
            successor,obs=self.models[name].step(state,action)
            outcomes.setdefault(obs,set()).add((name,successor))
        return {obs:frozenset(worlds) for obs,worlds in outcomes.items()}

    def subset_value(self,belief,horizon):
        key=belief,horizon
        if key in self.k_cache:return self.k_cache[key]
        terminal=self._terminal(belief,horizon)
        if terminal is not None:return terminal
        self.k_nodes+=1;best=inf
        for action,cost in self.costs.items():
            if cost>=best:continue
            worst=0
            for child in self.branches(belief,action).values():
                worst=max(worst,self.subset_value(child,horizon-1))
                if cost+worst>=best:break
            best=min(best,cost+worst)
        self.k_cache[key]=best
        return best

    def information_lower(self,belief,horizon):
        if self.variant in ('coverage','resource_blind'):
            key=belief,horizon
            if key not in self.bound_cache:
                self.bound_stats['calls']+=1
                lower=self.coverage.lower(belief,horizon)
                # A completed coverage certificate makes expensive tails redundant.
                if lower<inf:
                    lower=max(lower,max(self.singleton(w,horizon) for w in belief))
                self.bound_cache[key]=lower
            return self.bound_cache[key]
        if self.variant!='k3':return super().information_lower(belief,horizon)
        key=belief,horizon
        if key not in self.bound_cache:
            self.bound_stats['calls']+=1
            worlds=tuple(sorted(belief,key=lambda w:(w[0],repr(w[1]))))
            lower=0
            for subset in combinations(worlds,min(3,len(worlds))):
                self.k_queries+=1
                lower=max(lower,self.subset_value(frozenset(subset),horizon))
                if lower==inf:break
            self.bound_cache[key]=lower
        return self.bound_cache[key]

    def verify(self,belief,horizon,policy):
        costs=[]
        for name,state in belief:
            node=policy;count=cost=0
            while not node.get('stop'):
                assert self.allowed(state) and count<horizon
                action=node['action'];state,obs=self.models[name].step(state,action)
                node=node['branches'][obs];count+=1;cost+=self.costs[action]
            assert self.allowed(state) and self.goal.holds(state)
            costs.append(cost)
        return max(costs)

    def statistics(self):
        return dict(super().statistics(),k_nodes=self.k_nodes,k_subset_queries=self.k_queries)
