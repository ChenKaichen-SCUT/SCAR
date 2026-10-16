"""Semantics-preserving static joins and applicability index; old frontend retained."""
import z3
from scar_public.symbolic_task import SymbolicTask,Action,TaskGoal,LazyModel,typed_list,flatten_and,atoms,ze,ev
from scar_public.contingent_benchmarks import sexpr
from scar_public.finite_planner import State
from scar_public.static_grounding import StaticGrounder,ActionIndex,conjunction_masks

class CompiledTask(SymbolicTask):
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
        grounder=StaticGrounder(d,objects,self.atom_names,positive,uncertain)
        acts=[]
        for schema in d:
            if not isinstance(schema,list) or not schema or schema[0]!=':action':continue
            verb=schema[1];fields=dict(zip(schema[2::2],schema[3::2]))
            if set(fields)-{':parameters',':precondition',':effect',':observe'}:raise ValueError('unsupported action field')
            params=typed_list(fields.get(':parameters',[]))
            choices=[[o for o,t in objects.items() if ty=='object' or t==ty] for ty in params.values()]
            for values in grounder.bindings(fields):
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

        self.grounding_stats=dict(grounder.stats)
        self.action_index=ActionIndex(self.actions)
        self.applicable_cache={}
        self.index_stats=dict(candidate_checks=0,queries=0,cache_hits=0,pure_senses_skipped=0)
        self.pre_masks={n:conjunction_masks(a.pre) for n,a in self.actions.items()}

    def applicable(self,state):
        bits,valid=state.symbols
        if not valid:return ()
        self.index_stats['queries']+=1
        if bits in self.applicable_cache:
            self.index_stats['cache_hits']+=1;actions=self.applicable_cache[bits]
        else:
            actions=[]
            for name in self.action_index.candidates(bits):
                self.index_stats['candidate_checks']+=1;mask=self.pre_masks[name]
                if ((bits&mask[0])==mask[0] and not bits&mask[1]) if mask is not None else ev(self.actions[name].pre,bits):
                    actions.append(name)
            actions=tuple(actions)
            if len(self.applicable_cache)<32768:self.applicable_cache[bits]=actions
        return tuple(n for n in actions if all(r>=c for r,c in zip(state.resources,self.actions[n].consumption)))

    def metadata(self):
        return dict(super().metadata(),grounding=dict(self.grounding_stats))
