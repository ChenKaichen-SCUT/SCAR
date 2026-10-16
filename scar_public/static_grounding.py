"""Sound lifted static joins before grounding; no sampled/truncated action set."""
from collections import defaultdict,Counter
from math import prod
from scar_public.symbolic_task import typed_list,flatten_and


def changed_predicates(domain):
    result=set()
    def visit(x):
        if not x:return
        if x[0]=='and':
            for y in x[1:]:visit(y)
        elif x[0]=='when':visit(x[2])
        elif x[0]=='not':visit(x[1])
        elif x[0] in ('oneof','probabilistic','forall','increase','decrease'):
            raise ValueError('unsupported effect '+x[0])
        else:result.add(x[0])
    for schema in domain:
        if isinstance(schema,list) and schema and schema[0]==':action':
            fields=dict(zip(schema[2::2],schema[3::2]));visit(fields.get(':effect',[]))
    return result


class StaticGrounder:
    def __init__(self,domain,objects,names,positive,uncertain,work_limit=2000000):
        self.dynamic=changed_predicates(domain);self.objects=objects
        self.possible={names[i] for i in positive|uncertain if names[i][0] not in self.dynamic}
        self.certain={names[i] for i in positive if names[i][0] not in self.dynamic}
        self.relations=defaultdict(list)
        for fact in sorted(self.possible):self.relations[fact[0]].append(fact[1:])
        self.stats=dict(cartesian_bindings=0,join_checks=0,emitted_bindings=0,static_rejections=0)
        self.work_limit=work_limit

    def charge(self):
        self.stats['join_checks']+=1
        if self.stats['join_checks']>self.work_limit:raise ValueError('static join work limit; no truncation')

    def truth(self,x,env):
        if not x:return True
        op=x[0]
        if op=='not':
            v=self.truth(x[1],env);return None if v is None else not v
        if op in ('and','or'):
            vs=[self.truth(y,env) for y in x[1:]]
            if op=='and':return False if False in vs else (True if all(v is True for v in vs) else None)
            return True if True in vs else (False if all(v is False for v in vs) else None)
        if op=='oneof':return None
        args=tuple(env.get(v,v) for v in x[1:])
        if any(v.startswith('?') for v in args):return None
        if op=='=':return args[0]==args[1]
        if op in self.dynamic:return None
        fact=(op,)+args
        return True if fact in self.certain else (None if fact in self.possible else False)

    def bindings(self,fields):
        params=typed_list(fields.get(':parameters',[]))
        choices={p:tuple(o for o,t in self.objects.items() if ty=='object' or t==ty)
                 for p,ty in params.items()}
        domains={p:set(values) for p,values in choices.items()}
        self.stats['cartesian_bindings']+=prod(len(v) for v in choices.values())
        pre=fields.get(':precondition',[])
        joins=[x for x in flatten_and(pre) if x and x[0] not in
            self.dynamic|{'and','or','not','oneof','='}]
        joins.sort(key=lambda x:len(self.relations[x[0]]))
        def joined(index,env):
            if self.truth(pre,env) is False:
                self.stats['static_rejections']+=1;return
            if index<len(joins):
                atom=joins[index]
                for values in self.relations[atom[0]]:
                    self.charge()
                    if len(values)!=len(atom)-1:continue
                    nxt=dict(env)
                    for term,value in zip(atom[1:],values):
                        if term.startswith('?'):
                            if term not in domains or value not in domains[term] or (term in nxt and nxt[term]!=value):break
                            nxt[term]=value
                        elif term!=value:break
                    else:yield from joined(index+1,nxt)
                return
            remaining=[p for p in params if p not in env]
            def assign(i):
                if self.truth(pre,env) is False:
                    self.stats['static_rejections']+=1;return
                if i==len(remaining):
                    self.stats['emitted_bindings']+=1;yield tuple(env[p] for p in params);return
                p=remaining[i]
                for value in choices[p]:
                    self.charge();env[p]=value;yield from assign(i+1)
                env.pop(p,None)
            yield from assign(0)
        yield from joined(0,{})


def required_literals(expr):
    if type(expr) is int:return {expr}
    if type(expr) is bool:return set()
    op,args=expr
    if op=='not' and type(args[0]) is int:return {-args[0]}
    if op=='and':return set().union(*(required_literals(x) for x in args))
    return set()


def conjunction_masks(expr):
    if expr is True:return 0,0
    if type(expr) is int:return ((1<<(expr-1),0) if expr>0 else (0,1<<(-expr-1)))
    if type(expr) is bool:return None
    op,args=expr
    if op=='not' and type(args[0]) is int:return conjunction_masks(-args[0])
    if op!='and':return None
    masks=[conjunction_masks(x) for x in args]
    if any(x is None for x in masks):return None
    pos=neg=0
    for p,n in masks:pos|=p;neg|=n
    return pos,neg


class ActionIndex:
    def __init__(self,actions):
        self.actions=tuple(actions);self.cache={};self.anchors=defaultdict(int);self.unanchored=0
        requirements={name:required_literals(a.pre) for name,a in actions.items()}
        frequency=Counter(x for r in requirements.values() for x in r)
        for i,name in enumerate(self.actions):
            r=requirements[name]
            if r:self.anchors[min(r,key=lambda x:(frequency[x],x))]|=1<<i
            else:self.unanchored|=1<<i

    def candidates(self,bits):
        if bits not in self.cache:
            mask=self.unanchored
            for lit,actions in self.anchors.items():
                if bool(bits&(1<<(abs(lit)-1)))==(lit>0):mask|=actions
            if len(self.cache)<32768:self.cache[bits]=mask
        else:mask=self.cache[bits]
        while mask:
            bit=mask&-mask;yield self.actions[bit.bit_length()-1];mask^=bit
