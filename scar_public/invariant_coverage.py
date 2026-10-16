"""Diagnostic refinement: proved static support invariants, without a state graph.

For each dynamic atom v, v implies a static condition explaining either initial
truth or some legal achiever. Dynamic conditions are optimistically erased in
negation normal form. Every retained conjunction is independently checked for
initial validity and inductive preservation; UNKNOWN disables the refinement.
"""
from collections import defaultdict
from time import perf_counter
import z3
from scar_public.symbolic_task import ze
from scar_public.symbolic_coverage import SymbolicCoverage,LazyCoveragePlanner,Unavailable


def next_formulae(task,action,vs):
    adds=defaultdict(list);deletes=defaultdict(list)
    for condition,lit in action.effects:
        (adds if lit>0 else deletes)[abs(lit)-1].append(ze(condition,vs))
    return [z3.simplify(z3.Or(z3.Or(adds[i]),z3.And(v,z3.Not(z3.Or(deletes[i])))))
            if i in adds or i in deletes else v for i,v in enumerate(vs)]


def support_invariants(task):
    started=perf_counter();vs=task.zvars
    def relax(expr,neg=False):
        if type(expr) is bool:return z3.BoolVal(expr!=neg)
        if type(expr) is int:
            if abs(expr)-1 in task.dynamic:return z3.BoolVal(True)
            v=ze(expr,vs);return z3.Not(v) if neg else v
        op,args=expr
        if op=='not':return relax(args[0],not neg)
        if op in ('and','or'):
            use_and=(op=='and')!=neg
            return (z3.And if use_and else z3.Or)(*[relax(x,neg) for x in args])
        return z3.BoolVal(True)  # safe relaxation for other compound forms
    static=sorted(set(range(len(vs)))-task.dynamic);groups=set(task.static_bits)
    cube={b:z3.And(*[v if b&(1<<i) else z3.Not(v) for i,v in enumerate(vs) if i in static]) for b in groups}
    support=defaultdict(list)
    for a in task.actions.values():
        for condition,lit in a.effects:
            if lit>0:support[lit-1].append(z3.And(relax(a.pre),relax(condition)))
    candidates=[]
    for i in sorted(task.dynamic):
        initial={s&~task.dynamic_mask for s in task.initial_bits if s&(1<<i)}
        init=z3.BoolVal(True) if initial==groups else z3.Or(*[cube[b] for b in initial])
        condition=z3.simplify(z3.Implies(vs[i],z3.Or(init,*support[i])))
        if not z3.is_true(condition):candidates.append(condition)
    invariant=z3.simplify(z3.And(candidates));checks=0
    stats=dict(candidate_invariants=len(candidates),verified=False,proof_checks=0,reason=None)
    try:
        for bits in task.initial_bits:
            value=z3.simplify(z3.substitute(invariant,*[(v,z3.BoolVal(bool(bits&(1<<i)))) for i,v in enumerate(vs)]))
            if not z3.is_true(value):raise Unavailable('initial invariant check failed')
            checks+=1
        for a in task.actions.values():
            nxt=next_formulae(task,a,vs)
            after=z3.substitute(invariant,*zip(vs,nxt))
            solver=z3.Solver();solver.set(timeout=1000)
            solver.add(invariant,ze(a.pre,vs),z3.Not(after));answer=solver.check();checks+=1
            if answer!=z3.unsat:raise Unavailable('inductive check '+str(answer))
        stats['verified']=True
    except Unavailable as error:
        invariant=z3.BoolVal(True);stats['reason']=str(error)
    stats.update(proof_checks=checks,seconds=perf_counter()-started)
    return invariant,stats


class InvariantCoverage(SymbolicCoverage):
    def __init__(self,task,use_invariants=True):
        super().__init__(task)
        self.invariant,self.invariant_stats=(support_invariants(task) if use_invariants else
            (z3.BoolVal(True),dict(candidate_invariants=0,verified=False,reason='control: no invariants',seconds=0)))
        self.specialized_invariants={}
        self.common_static=[]
        for i,v in enumerate(task.zvars):
            values={bool(b&(1<<i)) for b in task.static_bits}
            self.common_static.append(z3.BoolVal(next(iter(values))) if i not in task.dynamic and len(values)==1 else v)

    @property
    def stats(self):return dict(super().stats,invariants=self.invariant_stats)

    def pattern(self,static,projected,action):
        key=static,projected,action.name
        if key in self.patterns:return self.patterns[key]
        t=self.task
        if (static,projected) not in self.variable_cache:
            self.variable_cache[static,projected]=[
                z3.BoolVal(bool(static&(1<<i))) if i not in t.dynamic else
                z3.BoolVal(bool(projected&(1<<i))) if i in t.projection else v
                for i,v in enumerate(t.zvars)]
        vs=self.variable_cache[static,projected]
        if (static,projected) not in self.specialized_invariants:
            # The shared no-invariant control needs no O(number-of-atoms)
            # substitution into the constant True. Keep the logical formula.
            self.specialized_invariants[static,projected]=(self.invariant if z3.is_true(self.invariant)
                else z3.simplify(z3.substitute(self.invariant,*zip(t.zvars,vs))))
        invariant=self.specialized_invariants[static,projected]
        condition=z3.simplify(z3.And(invariant,ze(action.pre,vs),z3.Not(ze(t.goal_expr,vs))))
        if z3.is_false(condition):
            self.patterns[key]=(False,());return self.patterns[key]
        nxt=next_formulae(t,action,vs)
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
        solver.push();solver.add(goal);immediate=check();solver.pop();solver.add(z3.Not(goal));outcomes=[]
        while check():
            model=solver.model();values=[z3.is_true(model.eval(v,model_completion=True)) for v in outputs]
            ob=tuple(values[:len(obs)])
            projection=sum(1<<i for i,b in zip(t.projection,values[len(obs):]) if b)
            outcomes.append((ob,projection))
            if len(outcomes)>self.outcome_limit:raise Unavailable('abstract outcome enumeration limit')
            solver.add(z3.Or(*(v!=b for v,b in zip(outputs,values))))
        self._stats['sat_patterns']+=1;self._stats['abstract_outcomes']+=len(outcomes)
        self.patterns[key]=(immediate,tuple(outcomes));self.formula_patterns[signature]=self.patterns[key]
        return self.patterns[key]

    def get_channels(self,key):
        if key in self.channels:return self.channels[key]
        self._stats['channel_queries']+=1;resources,projected=key;result=[]
        common=[z3.BoolVal(bool(projected&(1<<i))) if i in self.task.projection else v
                for i,v in enumerate(self.common_static)]
        for a in self.task.actions.values():
            if any(r<c for r,c in zip(resources,a.consumption)):continue
            if z3.is_false(z3.simplify(ze(a.pre,common))):continue
            successor_resources=tuple(r-c for r,c in zip(resources,a.consumption))
            goals=set();buckets=defaultdict(set)
            for static,names in self.groups.items():
                immediate,outcomes=self.pattern(static,projected,a)
                if immediate:goals.update(names)
                for obs,nxt in outcomes:buckets[obs,nxt].update(names)
            channels=tuple((len(names),(successor_resources,nxt)) for (obs,nxt),names in sorted(buckets.items()))
            result.append((a.name,len(goals),channels))
        self.channels[key]=tuple(result);return self.channels[key]


class InvariantCoveragePlanner(LazyCoveragePlanner):
    def __init__(self,task,mode='symbolic_invariants'):
        super().__init__(task,'symbolic');self.coverage=InvariantCoverage(task,mode=='symbolic_invariants')
