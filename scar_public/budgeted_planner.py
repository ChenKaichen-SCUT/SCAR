"""Checked inexpensive lower bounds and explicitly budgeted optional inference.

No learned performance claim: the scheduler is a fixed engineering control.
Its only correctness claim is that skipped/interrupted inference is safe.
"""
from collections import deque
from math import inf
from time import perf_counter
from scar_public.threshold_search import ThresholdPlanner,Record
from scar_public.bounded_resource_coverage import BoundedResourceCoverage
from scar_public.information_controls import InformationControls


class InferenceStop(Exception):pass


class MeteredCoverage(BoundedResourceCoverage):
    def __init__(self,task,mode):
        super().__init__(task,mode,100000)
        self.deadline=inf;self.stops=0
    def check(self):
        if perf_counter()>=self.deadline:self.stops+=1;raise InferenceStop()
    def pattern(self,*args):
        self.check();return super().pattern(*args)
    def get_channels(self,*args):
        self.check();return super().get_channels(*args)
    def capacity(self,*args):
        self.check();return super().capacity(*args)
    def relational_capacity(self,*args):
        self.check();return super().relational_capacity(*args)


def expression_level(expr,levels,neg=False):
    if type(expr) is bool:return 0 if expr!=neg else inf
    if type(expr) is int:
        lit=-expr if neg else expr
        return levels.get(lit,inf)
    op,args=expr
    if op=='not':return expression_level(args[0],levels,not neg)
    if op in ('and','or'):
        conjunction=(op=='and')!=neg
        values=[expression_level(x,levels,neg) for x in args]
        return max(values,default=0) if conjunction else min(values,default=inf)
    # oneof implies at least one; its negation is relaxed to True.
    if op=='oneof':return 0 if neg else min((expression_level(x,levels) for x in args),default=inf)
    raise ValueError(op)


class BudgetedPlanner(ThresholdPlanner):
    MODES=('cheap','leaf','pair','leaf_counts','leaf_lineage_fixed','leaf_lineage_scheduled')
    def __init__(self,task,mode='leaf_lineage_scheduled'):
        if mode not in self.MODES:raise ValueError(mode)
        # Parent validates against self.MODES, so initialize with a valid name
        # then explicitly install the optional bound, without changing parent.
        original=self.MODES;self.MODES=ThresholdPlanner.MODES
        super().__init__(task,'single');self.MODES=original
        self.variant_mode=mode;self.coverage=None
        self.control=InformationControls(task)
        if mode in ('leaf_counts','leaf_lineage_fixed','leaf_lineage_scheduled'):
            self.coverage=MeteredCoverage(task,'counts' if mode=='leaf_counts' else 'lineage')
        self.hmax_cache={};self.inference_start=perf_counter();self.bfs_used=0
        self.cost_stats=dict(hmax_calls=0,hmax_work=0,hmax_fallbacks=0,hmax_seconds=0.,
            bfs_fallbacks=0,coverage_seconds=0.,coverage_attempts=0,coverage_skipped=0,
            coverage_interrupted=0,coverage_helpful=0,coverage_pruning=0)
        self.current_root=None

    def hmax(self,state):
        bits=state.symbols[0]
        if bits in self.hmax_cache:return self.hmax_cache[bits]
        started=perf_counter();self.cost_stats['hmax_calls']+=1
        levels={i+1 if bits&(1<<i) else -(i+1):0 for i in range(len(self.task.atom_names))}
        try:
            work=0
            while True:
                changed=False
                for a in self.task.actions.values():
                    pre=expression_level(a.pre,levels)
                    for guard,lit in a.effects:
                        work+=1;self.cost_stats['hmax_work']+=1
                        if work>50000 or self.cost_stats['hmax_work']>2000000:
                            self.cost_stats['hmax_fallbacks']+=1;return 0
                        value=1+max(pre,expression_level(guard,levels))
                        if value<levels.get(lit,inf):levels[lit]=value;changed=True
                if not changed:break
            result=expression_level(self.task.goal_expr,levels)
            self.hmax_cache[bits]=result;return result
        finally:self.cost_stats['hmax_seconds']+=perf_counter()-started

    def known_world(self,world,budget):
        rec=self.world_records.setdefault(world,Record())
        if rec.upper<inf or rec.lower>budget:return rec
        if not self.allowed(world[1]):rec.lower=inf;return rec
        if self.goal.holds(world[1]):rec.lower=rec.upper=0;rec.policy={'stop':True};return rec
        rec.lower=max(rec.lower,self.hmax(world[1]))
        if rec.lower>budget:return rec
        # BFS is useful for short tails, but cannot monopolize the whole run.
        if self.bfs_used>=4096:self.cost_stats['bfs_fallbacks']+=1;return rec
        started=perf_counter();queue=deque([(world,0)]);parents={world:None};expanded=0;found=None
        try:
            while queue:
                current,depth=queue.popleft()
                if expanded>=64 or self.bfs_used>=4096:
                    # All shallower layers have been completely searched.
                    rec.lower=max(rec.lower,depth)
                    self.cost_stats['bfs_fallbacks']+=1;return rec
                self.bfs_used+=1;expanded+=1;self.bound_stats['single_nodes']+=1
                if depth>=budget:continue
                for action in self.costs:
                    child,obs=self._step(current,action)
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
        finally:self.search_stats['singleton_seconds']+=perf_counter()-started

    def optional_lower(self,belief,budget,cheap):
        if self.coverage is None:return cheap
        spent=self.cost_stats['coverage_seconds'];scheduled=self.variant_mode.endswith('scheduled')
        if scheduled:
            elapsed=perf_counter()-self.inference_start
            credit=min(3.,0.25+0.25*max(0.,elapsed-spent))
            allowance=min(0.25,max(0.,credit-spent))
            # Most singleton tails and clearly impossible cheap bounds do not
            # benefit from a model-relationship computation.
            if len(belief)<2 or cheap>budget:allowance=0
        else:allowance=min(1.,max(0.,3.-spent))
        if allowance<0.002:self.cost_stats['coverage_skipped']+=1;return cheap
        self.cost_stats['coverage_attempts']+=1;started=perf_counter()
        self.coverage.deadline=started+allowance
        try:
            value=self.coverage.lower(belief,budget)
            if value>cheap:self.cost_stats['coverage_helpful']+=1
            if value>budget:self.cost_stats['coverage_pruning']+=1
            return max(cheap,value)
        except InferenceStop:
            self.cost_stats['coverage_interrupted']+=1;return cheap
        finally:self.cost_stats['coverage_seconds']+=perf_counter()-started

    def estimate(self,belief,budget):
        rec=self.record(belief)
        if rec.lower>budget or rec.lower==rec.upper or rec.checked>=budget:return rec
        self.bound_stats['calls']+=1
        for world in sorted(belief,key=lambda w:w[0]):
            known=self.known_world(world,budget);rec.lower=max(rec.lower,known.lower)
            if len(belief)==1 and known.upper<inf:rec.upper,rec.policy=known.upper,known.policy
            if rec.lower>budget:break
        if rec.lower<=budget and rec.lower<rec.upper:
            if self.variant_mode.startswith('leaf'):
                bound=self.control.leaf_lower(belief,budget)
                rec.lower=max(rec.lower,budget+1 if bound==inf else bound)
            elif self.variant_mode=='pair':
                bound=self.control.pair_lower(belief,budget)
                rec.lower=max(rec.lower,budget+1 if bound==inf else bound)
            if rec.lower<=budget:
                value=self.optional_lower(belief,budget,rec.lower)
                rec.lower=max(rec.lower,budget+1 if value==inf else value)
        rec.checked=budget
        assert rec.lower<=rec.upper
        return rec

    def statistics(self):
        return dict(super().statistics(),cost_control=dict(self.cost_stats,bfs_nodes=self.bfs_used),
            information_control=dict(self.control.stats))
