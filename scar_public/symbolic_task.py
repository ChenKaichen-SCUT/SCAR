"""Small checked contingent-PDDL frontend and lazy deterministic transitions.

Supports typed/untyped STRIPS, Boolean preconditions, simultaneous conditional
effects, Boolean observations, and explicit initial oneof/unknown/or constraints.
No probability, nondeterministic effects, quantifiers, or numeric PDDL. Optional
resource costs are declared overlays, never presented as original benchmarks.
"""
from dataclasses import dataclass
from itertools import product
import z3

from scar_public.contingent_benchmarks import sexpr
from scar_public.finite_planner import State


def typed_list(items):
    result={};pending=[];i=0
    while i<len(items):
        if items[i]=='-':
            for name in pending:result[name]=items[i+1]
            pending=[];i+=2
        else:pending.append(items[i]);i+=1
    result.update((name,'object') for name in pending)
    return result


def flatten_and(tree):
    if isinstance(tree,list) and tree and tree[0]=='and':
        return [y for x in tree[1:] for y in flatten_and(x)]
    return [tree]


def ev(expr,bits):
    if type(expr) is bool:return expr
    if type(expr) is int:return bool(bits&(1<<(abs(expr)-1)))==(expr>0)
    op,args=expr
    if op=='and':return all(ev(x,bits) for x in args)
    if op=='or':return any(ev(x,bits) for x in args)
    if op=='not':return not ev(args[0],bits)
    if op=='oneof':return sum(ev(x,bits) for x in args)==1
    raise ValueError(op)


def atoms(expr):
    if type(expr) is bool:return set()
    if type(expr) is int:return {abs(expr)-1}
    return set().union(*(atoms(x) for x in expr[1]))


def ze(expr,variables):
    if type(expr) is bool:return z3.BoolVal(expr)
    if type(expr) is int:
        v=variables[abs(expr)-1]
        return v if expr>0 else z3.Not(v)
    op,args=expr;vs=[ze(x,variables) for x in args]
    if op=='and':return z3.And(vs)
    if op=='or':return z3.Or(vs)
    if op=='not':return z3.Not(vs[0])
    if op=='oneof':return z3.PbEq([(x,1) for x in vs],1)
    raise ValueError(op)


@dataclass(frozen=True)
class Action:
    name: str
    verb: str
    pre: object
    effects: tuple  # (condition, signed literal)
    observation: object
    consumption: tuple


class TaskGoal:
    def __init__(self,task):self.task=task
    def holds(self,state):return ev(self.task.goal_expr,state.symbols[0])


class LazyModel:
    def __init__(self,task,index):
        self.task,self.index,self.name=task,index,f'm{index}'
        self.costs=task.costs
    def step(self,state,action):return self.task.step(state,action)


class SymbolicTask:
    def __init__(self,domain,problem,*,resources=(),resource_costs=None,projection_predicates=(),
                 model_limit=256,ground_limit=20000):
        d,p=sexpr(domain),sexpr(problem)
        self.atom_names=[];ids={}
        self.transition_calls=0
        def field(tree,name,default):return next((x[1:] for x in tree if isinstance(x,list) and x and x[0]==name),default)
        self.name=next(x[1] for x in p if isinstance(x,list) and x[0]=='problem')
        objects=typed_list(field(d,':constants',[])+field(p,':objects',[]))
        self.objects=objects
        def form(x,env=None):
            env={} if env is None else env
            if not x:return True
            op=x[0]
            if op in ('and','or','not','oneof'):
                return op,tuple(form(y,env) for y in x[1:])
            if op=='=':return env.get(x[1],x[1])==env.get(x[2],x[2])
            if op in ('forall','exists','probabilistic','when','unknown','increase','decrease'):
                raise ValueError('unsupported formula '+op)
            key=tuple(env.get(y,y) for y in x)
            if any(str(y).startswith('?') for y in key):raise ValueError('ungrounded atom')
            if key not in ids:ids[key]=len(ids);self.atom_names.append(key)
            return ids[key]+1
        init=[];unknown=set();uncertain=set();positive=set();negative=set()
        for item in field(p,':init',[]):
            for x in flatten_and(item):
                if x[0]=='unknown':
                    v=form(x[1]);unknown.update(atoms(v));continue
                v=form(x);init.append(v)
                if type(v) is int:positive.add(v-1)
                elif v[0]=='not' and type(v[1][0]) is int:negative.add(v[1][0]-1)
                else:uncertain.update(atoms(v))
        uncertain|=unknown
        self.goal_expr=form(field(p,':goal',[['and']])[0])
        self.resources=tuple(resources)
        resource_costs={} if resource_costs is None else resource_costs
        acts=[]
        for schema in d:
            if not isinstance(schema,list) or not schema or schema[0]!=':action':continue
            verb=schema[1];fields=dict(zip(schema[2::2],schema[3::2]))
            if set(fields)-{':parameters',':precondition',':effect',':observe'}:raise ValueError('unsupported action field')
            params=typed_list(fields.get(':parameters',[]))
            choices=[[o for o,t in objects.items() if ty=='object' or t==ty] for ty in params.values()]
            for values in product(*choices):
                env=dict(zip(params,values));effects=[]
                def effect(x,condition=True):
                    if not x:return
                    if x[0]=='and':
                        for y in x[1:]:effect(y,condition)
                    elif x[0]=='when':effect(x[2],('and',(condition,form(x[1],env))))
                    elif x[0]=='not':effects.append((condition,-form(x[1],env)))
                    elif x[0] in ('oneof','probabilistic','forall','increase','decrease'):
                        raise ValueError('unsupported effect '+x[0])
                    else:effects.append((condition,form(x,env)))
                effect(fields.get(':effect',[]))
                consumption=resource_costs.get(verb,(0,)*len(resources))
                if len(consumption)!=len(resources) or any(c<0 for c in consumption):raise ValueError('invalid consumption')
                acts.append(Action(' '.join((verb,)+values),verb,form(fields.get(':precondition',[]),env),tuple(effects),
                    form(fields[':observe'],env) if ':observe' in fields else None,tuple(consumption)))
                if len(acts)>ground_limit:raise ValueError('ground action limit; no truncated task')
        self.dynamic=frozenset(abs(lit)-1 for a in acts for _,lit in a.effects)
        self.dynamic_mask=sum(1<<i for i in self.dynamic)
        self.projection=tuple(i for i,name in enumerate(self.atom_names) if name[0] in projection_predicates and i in self.dynamic)
        self.projection_mask=sum(1<<i for i in self.projection)
        self.zvars=[z3.Bool(f'x{i}') for i in range(len(ids))]
        solver=z3.Solver();solver.add(*(ze(x,self.zvars) for x in init))
        # Closed-world default applies outside uncertain or explicitly true atoms.
        for i in range(len(ids)):
            if i not in uncertain and i not in positive:solver.add(z3.Not(self.zvars[i]))
        states=[]
        while solver.check()==z3.sat:
            model=solver.model();values=[z3.is_true(model.eval(v,model_completion=True)) for v in self.zvars]
            states.append(sum(1<<i for i,v in enumerate(values) if v))
            if len(states)>model_limit:raise ValueError('initial-model limit; no sampling or truncation')
            solver.add(z3.Or(*(v!=b for v,b in zip(self.zvars,values))))
        if solver.check()!=z3.unsat:raise ValueError('initial enumeration incomplete')
        if not states:raise ValueError('empty initial belief')
        states.sort();self.initial_bits=tuple(states)
        self.static_bits=tuple(s&~self.dynamic_mask for s in states)
        # Reject only actions provably inapplicable in every model from static facts.
        common=[]
        for i,v in enumerate(self.zvars):
            values={bool(s&(1<<i)) for s in self.static_bits}
            common.append(z3.BoolVal(next(iter(values))) if i not in self.dynamic and len(values)==1 else v)
        def possible(a):return not z3.is_false(z3.simplify(ze(a.pre,common)))
        self.actions={a.name:a for a in acts if possible(a)}
        self.costs=dict.fromkeys(self.actions,1)
        self.models=[LazyModel(self,i) for i in range(len(states))]
        self.goal=TaskGoal(self);self.allowed=lambda s:s.symbols[1]
        self.belief=frozenset((m.name,State((states[i],True),self.resources)) for i,m in enumerate(self.models))

    def step(self,state,action):
        self.transition_calls+=1
        bits,valid=state.symbols;a=self.actions[action]
        if not valid or not ev(a.pre,bits) or any(r<c for r,c in zip(state.resources,a.consumption)):
            return State((bits,False),state.resources),()
        add=delete=0
        for guard,lit in a.effects:
            if ev(guard,bits):
                if lit>0:add|=1<<(lit-1)
                else:delete|=1<<(-lit-1)
        nxt=(bits&~delete)|add
        obs=() if a.observation is None else (ev(a.observation,nxt),)
        return State((nxt,True),tuple(r-c for r,c in zip(state.resources,a.consumption))),obs

    def project(self,state):return state.resources,state.symbols[0]&self.projection_mask

    def metadata(self):
        return dict(name=self.name,atoms=len(self.atom_names),dynamic_atoms=len(self.dynamic),
                    initial_models=len(self.models),ground_actions=len(self.actions),
                    projection_atoms=[self.atom_names[i] for i in self.projection],resources=self.resources,
                    full_state_graph_constructed=False)
