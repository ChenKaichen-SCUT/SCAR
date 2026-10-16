"""Identity-preserving resource coverage, with optional sibling b-matching.

Counts, lineage and matching share the SAME symbolic witness channels and exact
search. Candidate masks are bitsets of initial model IDs, not concrete states.
The bounded extra DP falls back to the original count upper bound, never a
partial maximum. No observation is added to the real controller.
"""
from collections import defaultdict
from math import inf
from time import perf_counter
import z3

from scar_public.invariant_coverage import InvariantCoverage
from scar_public.symbolic_coverage import LazyCoveragePlanner,Unavailable
from scar_public.symbolic_task import ze


def bits(mask):
    while mask:
        bit=mask&-mask;yield bit;mask^=bit


def matching_size(buckets):
    """Exact integral bipartite b-matching; unit capacity per candidate model.

    A bucket is (eligible model bitset, maximum successful members). Augmenting
    paths reassign existing owners instead of greedily counting each bucket.
    """
    buckets=[(m,min(c,m.bit_count())) for m,c in buckets if m and c]
    members=0;overlap=False
    for m,_ in buckets:overlap|=bool(members&m);members|=m
    if not overlap:return sum(c for _,c in buckets)
    owners=[[] for _ in buckets]
    def assign(bit,seen):
        for j,(mask,capacity) in enumerate(buckets):
            if j in seen or not bit&mask:continue
            seen.add(j)
            if len(owners[j])<capacity:owners[j].append(bit);return True
            for previous in tuple(owners[j]):
                if assign(previous,seen):
                    owners[j].remove(previous);owners[j].append(bit);return True
        return False
    return sum(assign(bit,set()) for bit in bits(members))


class RelationalCoverage(InvariantCoverage):
    MODES=('counts','lineage','matching')
    def __init__(self,task,mode='matching',node_limit=5000):
        if mode not in self.MODES:raise ValueError(mode)
        if node_limit is not None and node_limit<0:raise ValueError('negative node limit')
        super().__init__(task,use_invariants=False)
        self.relation_mode,self.node_limit=mode,node_limit
        self.mask_channels={};self.relation_cache={}
        self.model_bits={m.name:1<<i for i,m in enumerate(task.models)}
        self.group_masks={static:sum(1<<i for i in names) for static,names in self.groups.items()}
        self.relation_stats=dict(nodes=0,fallbacks=0,matching_calls=0,matching_seconds=0,
            sibling_deduplications=0,capacity_reductions=0,lower_seconds=0,mask_cardinalities={})

    @property
    def stats(self):
        return dict(super().stats,relation=dict(self.relation_stats,mode=self.relation_mode,
            node_limit=self.node_limit,cache_entries=len(self.relation_cache)))

    def get_channels(self,key):
        if key in self.channels:return self.channels[key]
        self._stats['channel_queries']+=1;resources,projected=key;records=[]
        common=[z3.BoolVal(bool(projected&(1<<i))) if i in self.task.projection else v
                for i,v in enumerate(self.common_static)]
        for a in self.task.actions.values():
            if any(r<c for r,c in zip(resources,a.consumption)):continue
            if z3.is_false(z3.simplify(ze(a.pre,common))):continue
            nxt_resources=tuple(r-c for r,c in zip(resources,a.consumption))
            goal_mask=0;buckets=defaultdict(int)
            for static,names in self.group_masks.items():
                immediate,outcomes=self.pattern(static,projected,a)
                if immediate:goal_mask|=names
                for obs,nxt in outcomes:buckets[obs,nxt]|=names
            channels=tuple((names,(nxt_resources,nxt)) for (obs,nxt),names in sorted(buckets.items()))
            records.append((a.name,goal_mask,channels))
        self.mask_channels[key]=tuple(records)
        self.channels[key]=tuple((a,f.bit_count(),tuple((u.bit_count(),q) for u,q in children))
                                 for a,f,children in records)
        return self.channels[key]

    def relational_capacity(self,key,candidates,horizon):
        if not candidates or horizon==0:return 0
        memo=key,candidates,horizon
        if memo in self.relation_cache:return self.relation_cache[memo]
        ceiling=min(candidates.bit_count(),self.capacity(key,horizon))
        if ceiling==0:return 0
        if self.node_limit is not None and self.relation_stats['nodes']>=self.node_limit:
            self.relation_stats['fallbacks']+=1;return ceiling
        self.relation_stats['nodes']+=1
        size=candidates.bit_count();hist=self.relation_stats['mask_cardinalities'];hist[size]=hist.get(size,0)+1
        best=0
        for _,goals,channels in self.mask_channels[key]:
            immediate=candidates&goals;remaining=candidates&~goals;children=[]
            for eligible,nxt in channels:
                mask=remaining&eligible
                if mask:
                    count=self.relational_capacity(nxt,mask,horizon-1)
                    if count:children.append((mask,count))
            total=sum(c for _,c in children)
            if self.relation_mode=='matching' and len(children)>1:
                self.relation_stats['matching_calls']+=1;start=perf_counter()
                distinct=matching_size(children)
                self.relation_stats['matching_seconds']+=perf_counter()-start
                self.relation_stats['sibling_deduplications']+=distinct<total
                total=distinct
            best=max(best,min(ceiling,immediate.bit_count()+total))
            if best==ceiling:break
        self.relation_stats['capacity_reductions']+=best<ceiling
        self.relation_cache[memo]=best;return best

    def lower(self,belief,horizon):
        started=perf_counter()
        try:
            if self.relation_mode=='counts':return super().lower(belief,horizon)
            self._stats['lower_calls']+=1
            if any(not self.task.allowed(s) for _,s in belief):return inf
            live=[(n,s) for n,s in belief if not self.task.goal.holds(s)]
            if not live:return 0
            keys={self.project(s) for _,s in live}
            if self._stats['disabled_reason'] or len(keys)!=1:
                self._stats['inapplicable_queries']+=1;return 0
            key=next(iter(keys));mask=0
            for name,_ in live:mask|=self.model_bits[name]
            try:
                for h in range(1,horizon+1):
                    if self.relational_capacity(key,mask,h)>=mask.bit_count():return h
                return inf
            except Unavailable as error:
                self._stats['disabled_reason']=str(error);return 0
        finally:self.relation_stats['lower_seconds']+=perf_counter()-started


class RelationalPlanner(LazyCoveragePlanner):
    def __init__(self,task,mode='matching',node_limit=5000):
        super().__init__(task,'symbolic');self.coverage=RelationalCoverage(task,mode,node_limit)
