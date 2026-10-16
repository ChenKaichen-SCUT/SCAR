"""Second development stage: harvest paths after C0, batch work before admission.

The first-stage snapshot/results remain authoritative. This avoids computing a
separate scalar tree solely to select predicates, and avoids spending all 64
optional attempts on tiny work slices. No timing or dominance theorem is claimed.
"""
from time import perf_counter
from scar_public.amortized_refinement import AmortizedCoverage
from scar_public.multistep_refinement import scalar_path, path_core
from scar_public.certificate_refinement import indices, projection_view
from scar_public.decision_coverage import DecisionPlanner
from scar_public.budgeted_planner import InferenceStop
from scar_public.symbolic_coverage import Unavailable
from scar_public.work_scheduled_refinement import WorkMixin


class CachedMultistepCoverage(AmortizedCoverage):
    def __init__(self, task):
        super().__init__(task)
        self.trace_seen = set()
        self.trace_attempts = 0
        self.multistep_stats = dict(paths=0,multi_step_paths=0,spurious_paths=0,
            linked_satisfiable=0,sat_checks=0,core_minimizations=0,refinements=0,
            capped_cores=0,interrupted=0,seconds=0.,traces=[])

    def harvest(self, bound, live, budget):
        extra=self.active_extra
        if self.trace_attempts>=12 or self.multistep_stats['refinements']>=3:
            return extra
        key=bound.project(live[0][1]);n=len(live)
        # Read only cached scalar entries. Their construction was necessary for
        # the actual threshold query, not an extra selection-only depth sweep.
        depths=[d for d in range(1,budget+1)
            if bound.cache.get((bound.canonical(key,d),d),-1)>=n]
        if not depths:return extra
        depth=min(depths);memo_key=(extra,frozenset(live),depth)
        if memo_key in self.trace_seen:return extra
        self.trace_attempts+=1;first,common=self.known(live)
        started=perf_counter();old_deadline=bound.deadline
        bound.deadline=min(old_deadline,started+.10)
        try:
            memo={}
            for name,state in sorted(live,key=lambda w:w[0]):
                path=scalar_path(bound,key,bound.model_bits[name],depth,memo)
                if path is None:continue
                self.multistep_stats['paths']+=1
                self.multistep_stats['multi_step_paths']+=len(path)>1
                core=path_core(bound,path,state.symbols[0],common&~extra,self.multistep_stats)
                if not core:continue
                if (extra|core|getattr(self,'retained_identities',0)).bit_count()>6:
                    self.multistep_stats['capped_cores']+=1;continue
                self.multistep_stats['refinements']+=1
                self.multistep_stats['traces'].append(dict(model=name,depth=depth,
                    actions=[p[1] for p in path],added_atoms=[self.task.atom_names[i] for i in indices(core)]))
                extra|=core
                break
            self.trace_seen.add(memo_key)
        except (InferenceStop,Unavailable):
            self.multistep_stats['interrupted']+=1
        finally:
            self.multistep_stats['seconds']+=perf_counter()-started
            bound.deadline=old_deadline
        return extra

    def decide(self,belief,budget,mode='relation_threshold'):
        self.counts_only=True
        try:prune,e=super().decide(belief,budget,'count_threshold')
        finally:self.counts_only=False
        if prune or e.get('reason')!='count_pass':return prune,e
        live=[(n,s) for n,s in belief if not self.task.goal.holds(s)]
        bound=self.refined[self.active_extra]
        extra=self.harvest(bound,live,budget)
        if extra!=self.active_extra:
            self.active_extra=extra
            if extra not in self.refined:
                self.refined[extra]=self.coverage_type(projection_view(self.task,extra),pool=self.channel_pool)
            bound=self.refined[extra];bound.deadline=self.deadline
        started=perf_counter()
        try:
            prune,e=bound.decide(belief,budget,'count_threshold' if len(self.group_masks)==1 else 'relation_threshold')
        finally:self.amortized_stats['inference_seconds']+=perf_counter()-started
        if prune:
            self.amortized_stats['scalar_prunes' if e['reason']=='scalar_prune' else 'relation_prunes']+=1
        return prune,dict(e,selected_atoms=[self.task.atom_names[i] for i in indices(extra)])

    @property
    def stats(self):
        return dict(super().stats,multistep=dict(self.multistep_stats,attempts=self.trace_attempts))


class BatchedCoverage(WorkMixin,AmortizedCoverage):
    pass


class BatchedMultistepCoverage(WorkMixin,CachedMultistepCoverage):
    pass


class CachedMultistepPlanner(DecisionPlanner):
    def __init__(self,task):
        super().__init__(task,'relation_threshold')
        self.target_coverage=CachedMultistepCoverage(task)


class BatchedWorkPlanner(DecisionPlanner):
    def __init__(self,task,multistep=True):
        super().__init__(task,'relation_threshold')
        self.target_coverage=(BatchedMultistepCoverage if multistep else BatchedCoverage)(task)
        self.next_batch=128
        self.batch_stats=dict(admission_skips=0,admitted=0,completed=0)

    def decision(self,belief,budget):
        coverage=self.target_coverage;ledger=coverage.channel_pool.work_ledger
        coverage.search_expansions=self.expanded
        ledger.earned=min(16384,128+4*self.expanded)
        available=ledger.earned-ledger.used
        cached=False
        if coverage.active_extra in coverage.refined:
            bound=coverage.refined[coverage.active_extra]
            live=[(n,s) for n,s in belief if not self.task.goal.holds(s)]
            keys={bound.project(s) for _,s in live}
            if len(keys)==1:
                key=bound.canonical(next(iter(keys)),budget)
                mask=sum(bound.model_bits[n] for n,_ in live)
                cached=(key,mask,budget) in bound.relation_cache or bound.cache.get((key,budget),float('inf'))<len(live)
        if available<self.next_batch and not cached:
            # Do not mark this query as seen or consume an optional attempt.
            # Exact search and its inexpensive bounds still run normally.
            self.batch_stats['admission_skips']+=1
            return super(DecisionPlanner,self).decision(belief,budget)
        before_attempts=self.target_attempts;before_used=ledger.used
        before_deferrals=ledger.stats['deferred']
        try:return super().decision(belief,budget)
        finally:
            if self.target_attempts>before_attempts:
                self.batch_stats['admitted']+=1
                if ledger.stats['deferred']>before_deferrals:
                    self.next_batch=min(1024,max(128,2*(ledger.used-before_used)))
                else:
                    self.next_batch=128;self.batch_stats['completed']+=1

    def statistics(self):
        return dict(super().statistics(),batch_schedule=dict(self.batch_stats,next_batch=self.next_batch))
