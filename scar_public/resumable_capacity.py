"""Persistent C1 continuations with explicit hot-path work accounting.

Dropping the C0 ceiling does not change the completed lineage recurrence: by
induction C1 <= C0 already. Partial intervals enclose the optimistic recurrence,
not the number of candidates executable by one real policy. A saturated lower
endpoint only certifies that THIS bound cannot prune.
"""
from dataclasses import dataclass, field
from math import inf
from time import perf_counter
from scar_public.incremental_channels import IncrementalCoverage, ChannelPool
from scar_public.budgeted_planner import InferenceStop
from scar_public.symbolic_coverage import Unavailable


@dataclass(eq=False)
class CapacityNode:
    key: tuple
    mask: int
    depth: int
    lower: int = 0
    upper: int = 0
    done: bool = False
    cursor: int = 0
    closed: int = 0
    edge_cursor: int = 0
    edge_count: int = 0
    waiting: object = None
    witness: object = None
    runner: object = None


class ResumableCapacity:
    def __init__(self, task, pool=None):
        self.owner=IncrementalCoverage(task,pool=pool)
        self.task=task;self.pool=self.owner.channel_pool
        self.actions=tuple(task.actions.values())
        self.nodes={};self.templates={};self.builders={}
        self.seconds_per_unit=2e-6
        self.work=dict(node_lookups=0,new_nodes=0,action_visits=0,template_lookups=0,
            template_hits=0,core_lookups=0,core_hits=0,pattern_lookups=0,pattern_hits=0,
            pattern_misses=0,sat_calls=0,outcome_assemblies=0,edge_visits=0,
            reductions=0,completed_nodes=0,dominated_actions=0,slices=0,
            units=0,seconds=0.,pattern_seconds=0.,atomic_interruptions=0)

    def event(self,kind,amount=1):
        self.work[kind]+=amount;self.work['units']+=amount
        return amount

    def node(self,key,mask,depth):
        key=self.owner.canonical(key,depth);memo=key,mask,depth
        self.event('node_lookups')
        if memo not in self.nodes:
            self.event('new_nodes')
            self.nodes[memo]=CapacityNode(key,mask,depth,upper=mask.bit_count(),done=not mask or not depth)
            if not mask or not depth:self.nodes[memo].upper=0
        return self.nodes[memo]

    def template(self,projected,index):
        """Resource-independent template; group and outcome assembly can pause.

        Core hits still incur lookup and copying work. Persistent builders avoid
        redoing the earlier static groups after an interrupted SAT call.
        """
        key=projected,index
        yield self.event('template_lookups')
        if key in self.templates:
            self.work['template_hits']+=1
            return self.templates[key]
        # A builder is shared by all suspended node computations asking for it.
        if key not in self.builders:
            self.builders[key]=self.build_template(projected,index)
        builder=self.builders[key]
        while key not in self.templates:
            try:yield next(builder)
            except StopIteration:break
        return self.templates[key]

    def build_template(self,projected,index):
        a=self.actions[index];spec=self.pool.spec(self.task.projection,a)
        outputs,static,retained,copied=spec
        core_key=a.name,outputs,retained,projected&retained
        yield self.event('core_lookups')
        if core_key in self.pool.channels:
            self.work['core_hits']+=1
            goals,core=self.pool.channels[core_key]
        else:
            goals=0;buckets={}
            for fixed,members in self.owner.group_masks.items():
                while True:
                    yield self.event('pattern_lookups')
                    known=static|retained
                    pat=(a.name,outputs,known,(fixed|projected)&known)
                    self.work['pattern_hits' if pat in self.pool.patterns else 'pattern_misses']+=1
                    before=self.pool.stats['sat_calls'];start=perf_counter()
                    interrupted=False
                    try:
                        immediate,outcomes=self.pool.pattern(self.owner,fixed,projected,a,spec)
                    except (InferenceStop,Unavailable):
                        self.work['atomic_interruptions']+=1
                        # The generator remains live. Only the unfinished atomic
                        # pattern is retried; already aggregated groups survive.
                        interrupted=True
                    finally:
                        self.work['pattern_seconds']+=perf_counter()-start
                        calls=self.pool.stats['sat_calls']-before
                        self.work['sat_calls']+=calls;self.work['units']+=32*calls
                    if interrupted:yield 0
                    else:break
                if immediate:goals|=members
                for obs,nxt in outcomes:
                    yield self.event('outcome_assemblies')
                    buckets[obs,nxt]=buckets.get((obs,nxt),0)|members
            if buckets:yield self.event('outcome_assemblies',len(buckets))
            core=tuple((obs,nxt,m) for (obs,nxt),m in sorted(buckets.items()))
            if len(self.pool.channels)<100000:self.pool.channels[core_key]=goals,core
        carry=projected&copied;rows=[]
        for obs,nxt,m in core:
            yield self.event('outcome_assemblies')
            rows.append((obs,nxt|carry,m))
        self.templates[projected,index]=goals,tuple(rows)

    def evaluate(self,node):
        if node.runner is None and not node.done:node.runner=self.compute(node)
        while not node.done:
            try:yield next(node.runner)
            except StopIteration:
                assert node.done,'unfinished recurrence closed'
        return node.lower

    def compute(self,node):
        cap=node.mask.bit_count();best=0;resources,projected=node.key
        for index,a in enumerate(self.actions):
            node.cursor=index
            yield self.event('action_visits')
            if any(r<c for r,c in zip(resources,a.consumption)):
                node.closed=index+1;continue
            goals,channels=yield from self.template(projected,index)
            immediate=node.mask&goals;remaining=node.mask&~goals
            total=immediate.bit_count();prepared=[]
            after_resources=tuple(r-c for r,c in zip(resources,a.consumption))
            node.edge_count=len(channels);node.edge_cursor=0
            # Computing this action's cheap ceiling also costs edge traversals.
            ceiling=total
            for obs,projected_next,eligible in channels:
                yield self.event('edge_visits')
                mask=remaining&eligible
                if mask:
                    nxt=(after_resources,projected_next)
                    child=self.node(nxt,mask,node.depth-1)
                    prepared.append((obs,nxt,mask,child))
                    ceiling+=child.upper
            if min(cap,ceiling)<=best:
                self.work['dominated_actions']+=1
                node.closed=index+1;continue
            if prepared:yield self.event('edge_visits',len(prepared))
            uncomputed=sum(child.upper for _,_,_,child in prepared)
            for j,(_,_,_,child) in enumerate(prepared):
                node.edge_cursor=j
                yield self.event('edge_visits')
                uncomputed-=child.upper
                node.waiting=child
                value=yield from self.evaluate(child)
                node.waiting=None;total+=value
                # All remaining children contribute at most their saved ceilings.
                # They may tighten elsewhere, but a stale ceiling is still safe.
                if min(cap,total+uncomputed)<=best:
                    self.work['dominated_actions']+=1;break
            else:
                value=min(cap,total)
                if value>best:
                    best=value
                    node.witness=(a.name,goals,tuple(prepared))
                    node.lower=best
            node.closed=index+1;node.edge_cursor=node.edge_count
            if best==cap:break
        node.lower=node.upper=best;node.done=True;node.waiting=None
        self.work['completed_nodes']+=1
        self.work['reductions']+=best<cap

    def advance(self,node,units=512,seconds=.025):
        """Continue exactly where paused; one atomic SAT operation may overrun."""
        started=perf_counter();before=self.work['units'];self.work['slices']+=1
        self.owner.deadline=started+seconds
        run=self.evaluate(node)
        try:
            while not node.done and self.work['units']-before<units and perf_counter()<self.owner.deadline:
                event=next(run,None)
                if event==0:break
        finally:
            elapsed=perf_counter()-started;spent=self.work['units']-before
            self.work['seconds']+=elapsed
            if spent:self.seconds_per_unit=.8*self.seconds_per_unit+.2*elapsed/spent
        return node.lower,node.upper

    def frontier_cost(self,node):
        """Cheap scheduling estimate, not a lower/upper bound on future CPU cost.

        Counts the unvisited action spine and remaining child scans, including
        hot template reads and resource-key assembly. Descendant branching not
        yet exposed is unknown; no SAT or speculative channel build is done here.
        """
        work=0;seen=set();current=node
        while current is not None and not current.done and id(current) not in seen:
            seen.add(id(current))
            work+=3*max(0,len(self.actions)-current.closed)
            work+=2*max(0,current.edge_count-current.edge_cursor)
            current=current.waiting
        return max(1,work)

    def path(self,node,bit):
        if not node.witness:return None
        name,goals,children=node.witness
        if goals&bit:return [(node.key,name,None,None)]
        for obs,nxt,mask,child in children:
            if mask&bit:
                tail=self.path(child,bit)
                if tail is not None:return [(node.key,name,nxt,obs)]+tail
        return None
