"""On-demand conservative channels from Boolean action formulae, not state graphs.

Existential SAT witnesses need not be reachable. Ambiguous projected successors
are optimistically distinguished as additional observations in the BOUND ONLY.
Unknown/time-limited SAT and outcome limits disable the bound; never prove failure.
"""
from collections import defaultdict,deque
from math import inf
import z3

from scar_public.coverage_planner import CoveragePlanner
from scar_public.finite_planner import Result
from scar_public.symbolic_task import ze


class Unavailable(Exception):pass


class SymbolicCoverage:
    def __init__(self,task,forget_resources=False,outcome_limit=512):
        self.task,self.forget_resources,self.outcome_limit=task,forget_resources,outcome_limit
        self.model_count=len(task.models)
        self.channels,self.cache,self.patterns={},{},{}
        self.formula_patterns={};self.variable_cache={}
        self.groups=defaultdict(set)
        for i,bits in enumerate(task.static_bits):self.groups[bits].add(i)
        self._stats=dict(sat_calls=0,sat_patterns=0,abstract_outcomes=0,channel_queries=0,
            lower_calls=0,dp_nodes=0,inapplicable_queries=0,disabled_reason=None,
            concrete_states_enumerated=0,concrete_transitions_enumerated=0)

    @property
    def stats(self):return dict(self._stats,abstract_states=len(self.channels),cached_entries=len(self.cache))

    def project(self,state):
        return (() if self.forget_resources else state.resources),state.symbols[0]&self.task.projection_mask

    def pattern(self,static,projected,action):
        key=static,projected,action.name
        if key in self.patterns:return self.patterns[key]
        t=self.task
        if (static,projected) not in self.variable_cache:
            vs=[]
            for i,v in enumerate(t.zvars):
                if i not in t.dynamic:vs.append(z3.BoolVal(bool(static&(1<<i))))
                elif i in t.projection:vs.append(z3.BoolVal(bool(projected&(1<<i))))
                else:vs.append(v)
            self.variable_cache[static,projected]=vs
        vs=self.variable_cache[static,projected]
        adds=defaultdict(list);deletes=defaultdict(list)
        for condition,lit in action.effects:
            (adds if lit>0 else deletes)[abs(lit)-1].append(ze(condition,vs))
        nxt=[z3.simplify(z3.Or(z3.Or(adds[i]),z3.And(v,z3.Not(z3.Or(deletes[i])))))
             if i in adds or i in deletes else v for i,v in enumerate(vs)]
        condition=z3.simplify(z3.And(ze(action.pre,vs),z3.Not(ze(t.goal_expr,vs))))
        goal=z3.simplify(ze(t.goal_expr,nxt))
        obs=[] if action.observation is None else [z3.simplify(ze(action.observation,nxt))]
        outputs=obs+[nxt[i] for i in t.projection]
        signature=tuple(e.sexpr() for e in [condition,goal]+outputs),len(obs)
        if signature in self.formula_patterns:
            self.patterns[key]=self.formula_patterns[signature];return self.patterns[key]
        solver=z3.Solver();solver.set(timeout=1000);solver.add(condition)
        def check():
            self._stats['sat_calls']+=1;answer=solver.check()
            if answer==z3.unknown:raise Unavailable('SAT query returned unknown')
            return answer==z3.sat
        solver.push();solver.add(goal);immediate=check();solver.pop()
        solver.add(z3.Not(goal))
        outcomes=[]
        while check():
            model=solver.model();values=[z3.is_true(model.eval(v,model_completion=True)) for v in outputs]
            ob=tuple(values[:len(obs)])
            projection=sum(1<<i for i,b in zip(t.projection,values[len(obs):]) if b)
            outcomes.append((ob,projection))
            if len(outcomes)>self.outcome_limit:raise Unavailable('abstract outcome enumeration limit')
            solver.add(z3.Or(*(v!=b for v,b in zip(outputs,values))))
        self._stats['sat_patterns']+=1;self._stats['abstract_outcomes']+=len(outcomes)
        self.patterns[key]=(immediate,tuple(outcomes))
        self.formula_patterns[signature]=self.patterns[key]
        return self.patterns[key]

    def get_channels(self,key):
        if key in self.channels:return self.channels[key]
        self._stats['channel_queries']+=1;resources,projected=key;result=[]
        for a in self.task.actions.values():
            if not self.forget_resources and any(r<c for r,c in zip(resources,a.consumption)):continue
            successor_resources=() if self.forget_resources else tuple(r-c for r,c in zip(resources,a.consumption))
            goals=set();buckets=defaultdict(set)
            for static,names in self.groups.items():
                immediate,outcomes=self.pattern(static,projected,a)
                if immediate:goals.update(names)
                for obs,nxt in outcomes:buckets[obs,nxt].update(names)
            channels=tuple((len(names),(successor_resources,nxt)) for (obs,nxt),names in sorted(buckets.items()))
            result.append((a.name,len(goals),channels))
        self.channels[key]=tuple(result);return self.channels[key]

    def capacity(self,key,horizon):
        if horizon==0:return 0
        memo=key,horizon
        if memo in self.cache:return self.cache[memo]
        self._stats['dp_nodes']+=1;best=0
        for _,immediate,channels in self.get_channels(key):
            count=immediate+sum(min(n,self.capacity(successor,horizon-1)) for n,successor in channels)
            best=max(best,min(self.model_count,count))
            if best==self.model_count:break
        self.cache[memo]=best;return best

    def lower(self,belief,horizon):
        self._stats['lower_calls']+=1
        if any(not self.task.allowed(s) for _,s in belief):return inf
        live=[(n,s) for n,s in belief if not self.task.goal.holds(s)]
        if not live:return 0
        keys={self.project(s) for _,s in live}
        if self._stats['disabled_reason'] or len(keys)!=1:
            self._stats['inapplicable_queries']+=1;return 0
        try:
            key=next(iter(keys))
            for h in range(1,horizon+1):
                if self.capacity(key,h)>=len({n for n,_ in live}):return h
            return inf
        except Unavailable as exc:
            self._stats['disabled_reason']=str(exc);return 0


class LazyCoveragePlanner(CoveragePlanner):
    """Same exact objective; shared lazy search for all comparison variants.

No LP or eager model graph is constructed. Exact known-world tails use BFS for
unit costs. Illegal actions and identical-belief positive-cost loops are omitted
uniformly across variants, since they cannot improve a shortest strong policy.
"""
    MODES=('single','pair_exact','k3','symbolic','resource_blind','explicit_channels')
    def __init__(self,task,mode='symbolic'):
        if mode not in self.MODES:raise ValueError(mode)
        self.task=task;self.models={m.name:m for m in task.models}
        self.goal,self.allowed,self.costs=task.goal,task.allowed,task.costs
        self.use_lp=False;self.relax={};self.memo={};self.expanded=self.pruned=0;self.remaining=None
        self.mode='single' if mode in ('symbolic','resource_blind','k3','explicit_channels') else mode
        self.variant='coverage' if mode in ('symbolic','explicit_channels') else mode
        self.node_limit=None;self.single_cache={};self.pair_cache={};self.bound_cache={}
        self.k_cache={};self.k_nodes=self.k_queries=0
        self.bound_stats=dict(single_nodes=0,pair_nodes=0,transition_lookups=0,calls=0,budget_exhausted=False)
        self.coverage=SymbolicCoverage(task,mode=='resource_blind') if mode in ('symbolic','resource_blind') else None
        if mode=='explicit_channels':self.coverage=ExplicitCoverage(task)

    def singleton(self,world,horizon):
        key=world,horizon
        if key in self.single_cache:return self.single_cache[key]
        term=self._terminal((world,),horizon)
        if term is not None:return term
        queue=deque([(world,0)]);seen={world};value=inf
        while queue:
            current,depth=queue.popleft();self.bound_stats['single_nodes']+=1
            if depth>=horizon:continue
            for a in self.costs:
                child,_=self._step(current,a)
                if not self.allowed(child[1]):continue
                if self.goal.holds(child[1]):value=depth+1;queue.clear();break
                if child not in seen:seen.add(child);queue.append((child,depth+1))
            if value<inf:break
        self.single_cache[key]=value;return value

    def useful_edges(self,belief,horizon):
        for action in self.costs:
            branches=self.branches(belief,action)
            if any(not self.allowed(s) for child in branches.values() for _,s in child):continue
            if len(branches)==1 and next(iter(branches.values()))==belief:continue
            yield action,branches

    def subset_value(self,belief,horizon):
        key=belief,horizon
        if key in self.k_cache:return self.k_cache[key]
        term=self._terminal(belief,horizon)
        if term is not None:return term
        if len(belief)==1:return self.singleton(next(iter(belief)),horizon)
        self.k_nodes+=1;best=inf
        for action,branches in self.useful_edges(belief,horizon):
            worst=0
            for child in branches.values():
                worst=max(worst,self.subset_value(child,horizon-1))
                if 1+worst>=best:break
            best=min(best,1+worst)
        self.k_cache[key]=best;return best

    def pair(self,first,second,horizon):return self.subset_value(frozenset((first,second)),horizon)

    def _search(self,belief,horizon):
        base=self.initial(belief,horizon)
        if base.exact:return base
        if self.remaining is not None and self.remaining<=0:return base
        if self.remaining is not None:self.remaining-=1
        self.expanded+=1;edges=[]
        for action,branches in self.useful_edges(belief,horizon):
            children={o:self.initial(b,horizon-1) for o,b in branches.items()}
            edges.append(dict(action=action,branches=branches,children=children,lower=1+max(x.lower for x in children.values())))
        edges.sort(key=lambda e:(e['lower'],e['action']))
        upper=inf;policy=None
        for e in edges:
            if e['lower']>=upper:self.pruned+=1;continue
            for o in sorted(e['children'],key=lambda o:(e['children'][o].lower,repr(o)),reverse=True):
                if self.remaining is not None and self.remaining<=0:break
                if not e['children'][o].exact:e['children'][o]=self._search(e['branches'][o],horizon-1)
                e['lower']=1+max(c.lower for c in e['children'].values())
                if e['lower']>=upper:break
            if all(c.upper<inf for c in e['children'].values()):
                value=1+max(c.upper for c in e['children'].values())
                if value<upper:
                    upper=value;policy=dict(action=e['action'],branches={o:c.policy for o,c in e['children'].items()})
        lower=max(base.lower,min((e['lower'] for e in edges),default=inf))
        answer=Result(lower,upper,policy);assert lower<=upper
        if answer.exact:self.memo[belief,horizon]=answer
        return answer


class ExplicitCoverage(SymbolicCoverage):
    """Same count recurrence, channels from all concrete reachable states.

This comparison enumerates states/transitions but streams them into the channel
table instead of storing a second graph. Limits are explicit errors, not proofs.
"""
    def __init__(self,task,state_limit=100000):
        super().__init__(task)
        records={}
        for name,initial in sorted(task.belief,key=lambda w:w[0]):
            queue=deque([initial]);seen={initial}
            while queue:
                s=queue.popleft();self._stats['concrete_states_enumerated']+=1
                if self._stats['concrete_states_enumerated']>state_limit:raise RuntimeError('explicit state limit')
                for a in task.actions:
                    successor,obs=task.step(s,a);self._stats['concrete_transitions_enumerated']+=1
                    if not task.allowed(successor):continue
                    if successor not in seen:seen.add(successor);queue.append(successor)
                    if task.goal.holds(s):continue
                    goals,buckets=records.setdefault((self.project(s),a),(set(),defaultdict(set)))
                    if task.goal.holds(successor):goals.add(name)
                    else:buckets[obs,self.project(successor)].add(name)
        for (key,a),(goals,buckets) in sorted(records.items()):
            self.channels.setdefault(key,[]).append((a,len(goals),tuple((len(names),q) for (obs,q),names in sorted(buckets.items()))))

    def get_channels(self,key):return self.channels.get(key,())
