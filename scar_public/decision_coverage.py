"""Threshold-only capacity and a certified skip based on a scalar witness.

The witness is a lower bound on OUR optimistic identity-capacity recurrence,
not a real policy certificate. Saturation certifies no pruning at this threshold.
Resource/time pressure only schedules work; it is never an infeasibility proof.
"""
from math import inf
from time import perf_counter
from scar_public.budgeted_planner import MeteredCoverage,InferenceStop
from scar_public.symbolic_coverage import Unavailable
from scar_public.indexed_planner import IndexedPlanner


class DecisionCoverage(MeteredCoverage):
    def __init__(self,task):
        super().__init__(task,'lineage');self.scalar_witness={};self.witness_cache={}
        self.decision_stats=dict(scalar_queries=0,witness_nodes=0,witness_saturated=0,
            scalar_prunes=0,relation_queries=0,relation_prunes=0,pressure_skips=0)

    def capacity(self,key,horizon):
        self.check()
        if horizon==0:return 0
        key=self.canonical(key,horizon);memo=key,horizon
        if memo in self.cache:return self.cache[memo]
        self._stats['dp_nodes']+=1;best=0;chosen=None
        for index,(_,immediate,channels) in enumerate(self.get_channels(key)):
            value=min(self.model_count,immediate+sum(min(n,self.capacity(q,horizon-1)) for n,q in channels))
            if value>best:best,chosen=value,index
            if best==self.model_count:break
        self.cache[memo]=best;self.scalar_witness[memo]=chosen;return best

    def witness_value(self,key,mask,horizon):
        self.check()
        if not mask or not horizon:return 0
        key=self.canonical(key,horizon);memo=key,mask,horizon
        if memo in self.witness_cache:return self.witness_cache[memo]
        self.decision_stats['witness_nodes']+=1
        ceiling=min(mask.bit_count(),self.capacity(key,horizon))
        chosen=self.scalar_witness.get((key,horizon))
        if chosen is None:return 0
        _,goals,channels=self.mask_channels[key][chosen]
        immediate=mask&goals;remaining=mask&~goals
        total=immediate.bit_count()
        for eligible,nxt in channels:
            total+=self.witness_value(nxt,remaining&eligible,horizon-1)
        value=min(ceiling,total);self.witness_cache[memo]=value;return value

    def decide(self,belief,budget,mode):
        live=[(n,s) for n,s in belief if not self.task.goal.holds(s)]
        if len(live)<2:return False,dict(reason='fewer_than_two_live')
        keys={self.project(s) for _,s in live}
        if len(keys)!=1:return False,dict(reason='projection_mismatch')
        key=next(iter(keys));mask=0
        for name,_ in live:mask|=self.model_bits[name]
        n=mask.bit_count();self.decision_stats['scalar_queries']+=1
        count=self.capacity(key,budget);e=dict(candidates=n,budget=budget,scalar=count)
        if count<n:
            self.decision_stats['scalar_prunes']+=1;return True,dict(e,reason='scalar_prune')
        if mode=='count_threshold':return False,dict(e,reason='count_pass')
        if mode=='relation_gate':
            witness=self.witness_value(key,mask,budget);deficit=n-witness
            pressure=max((1-min(1,r/(budget*c)) for r,c in zip(key[0],self.max_consumption) if c and budget),default=0)
            e.update(witness=witness,identity_deficit=deficit,resource_pressure=pressure)
            if witness>=n:
                self.decision_stats['witness_saturated']+=1
                return False,dict(e,reason='certified_no_threshold_effect')
            time_critical=self.capacity(key,max(0,budget-1))<n
            e['time_critical']=time_critical
            if pressure<=0 and not time_critical:
                self.decision_stats['pressure_skips']+=1
                return False,dict(e,reason='pressure_schedule_skip')
        self.decision_stats['relation_queries']+=1
        value=self.relational_capacity(key,mask,budget);prune=value<n
        self.decision_stats['relation_prunes']+=prune
        return prune,dict(e,identity_capacity=value,reason='relation_prune' if prune else 'relation_pass')


class DecisionPlanner(IndexedPlanner):
    MODES=('leaf','count_threshold','relation_threshold','relation_gate')
    def __init__(self,task,mode='relation_gate'):
        if mode not in self.MODES:raise ValueError(mode)
        super().__init__(task);self.decision_mode=mode
        self.target_coverage=None if mode=='leaf' else DecisionCoverage(task)
        self.target_seen=set();self.target_seconds=0.;self.target_attempts=0
        self.target_stats=dict(skipped_budget=0,interrupted=0,prunes=0)
        self.evidence=[]

    def decision(self,belief,budget):
        rec=self.estimate(belief,budget)
        if rec.lower<=budget<rec.upper and self.target_coverage is not None:
            query=belief,budget
            if query not in self.target_seen:
                self.target_seen.add(query)
                # Skip before SAT allocation when no cross-candidate issue exists.
                if len(belief)>1:
                    allowance=min(.25,max(0.,3.-self.target_seconds))
                    if allowance<.025 or self.target_attempts>=64:self.target_stats['skipped_budget']+=1
                    else:
                        start=perf_counter();self.target_attempts+=1
                        self.target_coverage.deadline=start+allowance
                        try:
                            prune,e=self.target_coverage.decide(belief,budget,self.decision_mode)
                            if len(self.evidence)<128:self.evidence.append(dict(e,seconds=perf_counter()-start))
                            if prune:
                                rec.lower=budget+1;self.target_stats['prunes']+=1
                        except (InferenceStop,Unavailable):self.target_stats['interrupted']+=1
                        finally:self.target_seconds+=perf_counter()-start
        return super().decision(belief,budget)

    def statistics(self):
        result=super().statistics()
        result['target_capacity']=dict(self.target_stats,seconds=self.target_seconds,attempts=self.target_attempts,
            evidence=self.evidence,coverage=self.target_coverage.stats if self.target_coverage else None,
            decisions=self.target_coverage.decision_stats if self.target_coverage else None)
        return result
