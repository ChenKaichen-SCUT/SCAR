"""Admit a query when giving it work, and preserve a selected root's opportunity.

Retired speculative frames do not consume the 64 actual-admission budget. Both
the root-only control and the ranked queue use the same sparse catalog engine.
"""
from time import perf_counter
from scar_public.frontier_scheduler import FrontierPlanner,Query,AncestorRejected
from scar_public.catalog_capacity import CatalogCapacity
from scar_public.certificate_refinement import projection_view


class FocusedPlanner(FrontierPlanner):
    def __init__(self,task,mode='focused_multistep'):
        if mode not in ('root_only','focused','focused_multistep'):raise ValueError(mode)
        super().__init__(task,'priority_multistep' if mode=='focused_multistep' else 'priority')
        self.focus_mode=mode;self.candidates={};self.job_sequence=0;self.focus_job=None
        self.focus_stats=dict(candidate_frames=0,unstarted_retired=0,focus_resumes=0,
            saturated_skips=0,reused_projection_upgrades=0)

    def engine(self,extra):
        if extra not in self.engines:self.engines[extra]=CatalogCapacity(projection_view(self.task,extra),self.pool)
        return self.engines[extra]

    def admit(self,frame):
        # This call now only registers an opportunity. No SAT, node or projection
        # is created, and the actual admission counter does not move.
        started=perf_counter()
        try:
            if self.focus_mode=='root_only' and frame.depth:return
            if len(frame.belief)<2:return
            self.candidates[id(frame)]=frame;self.focus_stats['candidate_frames']+=1
        finally:self.inference_seconds+=perf_counter()-started

    def start_query(self,frame):
        before=self.scheduler_stats['admitted'];before_seconds=self.inference_seconds
        FrontierPlanner.admit(self,frame)
        # The enclosing service includes this wall time exactly once.
        self.inference_seconds=before_seconds
        self.candidates.pop(id(frame),None)
        if self.scheduler_stats['admitted']==before:return None
        self.job_sequence+=1;frame.job.identifier=self.job_sequence
        return frame.job

    def refine(self,job,deadline):
        if self.mode=='priority_multistep':
            _,common=self.selector.known(job.live)
            extra=self.identities&common
            if extra&~job.extra:
                engine=self.engine(extra);key=engine.owner.project(job.live[0][1])
                mask=sum(engine.owner.model_bits[n] for n,_ in job.live)
                job.engine=engine;job.node=engine.node(key,mask,job.frame.budget);job.extra=extra
                self.focus_stats['reused_projection_upgrades']+=1
                return True
        return super().refine(job,deadline)

    def candidate_score(self,frame):
        # Before admission there is no recurrence evidence. A root's still-open
        # threshold can govern the whole current iteration. Child candidates
        # need actual remaining action fanout to outrank it.
        impact=max(1,frame.remaining_actions)
        initial_work=3*max(1,len(self.task.actions))*max(1,frame.budget)
        return impact/initial_work

    def service(self,current):
        if self.inference_seconds>=3:return
        if self.expanded-self.last_service<8 and self.last_service>=0:return
        self.last_service=self.expanded;started=perf_counter()
        active={id(f) for f in self.stack};pending=[]
        for j in self.jobs:
            if not j.resolved and (id(j.frame) not in active or not self.actionable(j)):
                j.resolved=True;j.status='STALE';self.scheduler_stats['retired']+=1
            if not j.resolved:pending.append(j)
        self.jobs=pending
        for identity,frame in list(self.candidates.items()):
            rec=self.record(frame.belief)
            if identity not in active or not rec.lower<=frame.budget<rec.upper:
                self.candidates.pop(identity);self.focus_stats['unstarted_retired']+=1
        exact_elapsed=max(0.,perf_counter()-self.scheduler_start-self.inference_seconds)
        credit=min(3.,.05+.5*exact_elapsed)-self.inference_seconds
        allowance=min(.025,max(0.,credit),3.-self.inference_seconds)
        if allowance<.001:
            self.scheduler_stats['budget_skips']+=1
            self.inference_seconds+=perf_counter()-started;return
        job=None
        if pending:
            # A partially evaluated ancestor with still-open alternatives is
            # resumed before opening another speculative descendant request.
            # This is commitment to usable work, not reward for sunk CPU cost.
            job=max(pending,key=lambda j:(self.score(j),j is self.focus_job,-j.frame.depth))
            if job is self.focus_job:self.focus_stats['focus_resumes']+=1
        elif self.scheduler_stats['admitted']<64 and self.candidates:
            frame=max(self.candidates.values(),key=lambda f:(self.candidate_score(f),-f.depth))
            job=self.start_query(frame)
        if job is None:
            self.inference_seconds+=perf_counter()-started;return
        self.focus_job=job
        # A certified completed pass is cheap to retire. Optional refinement may
        # still use its complete witness; no repeat recurrence is launched.
        if job.node.done and job.node.lower>=job.candidates:self.focus_stats['saturated_skips']+=1
        self.scheduler_stats['ranking_seconds']+=perf_counter()-started
        allowance=max(0.,allowance-(perf_counter()-started))
        if allowance<.0001:
            self.inference_seconds+=perf_counter()-started;return
        predicted=job.engine.frontier_cost(job.node);rate=job.engine.seconds_per_unit
        engine_before=job.engine;before=engine_before.work['units'];slice_start=perf_counter()
        if job.slices:self.scheduler_stats['resumed']+=1
        job.slices+=1;self.scheduler_stats['slices']+=1
        quota=max(128,min(8192,int(allowance/rate)))
        job.engine.advance(job.node,units=quota,seconds=allowance)
        status='PENDING'
        if job.node.upper<job.candidates:
            rec=self.record(job.frame.belief);rec.lower=max(rec.lower,job.frame.budget+1)
            assert rec.lower<=rec.upper
            job.resolved=True;status=job.status='REJECT';self.scheduler_stats['prunes']+=1
        elif job.node.lower>=job.candidates:
            if not self.refine(job,slice_start+allowance):
                job.resolved=True;status=job.status='BOUND_PASS';self.scheduler_stats['passes']+=1
            else:status='REFINED'
        elapsed=perf_counter()-slice_start;work=engine_before.work['units']-before
        job.seconds+=elapsed;job.units+=work
        if len(self.evidence)<384:
            self.evidence.append(dict(query=job.identifier,depth=job.frame.budget,stack_depth=job.frame.depth,
                prediction=predicted,predicted_seconds=predicted*rate,work=work,seconds=elapsed,status=status,
                quota=quota,lower=job.node.lower,upper=job.node.upper,candidates=job.candidates,
                remaining_exact_actions=job.frame.remaining_actions,slices=job.slices))
        self.inference_seconds+=perf_counter()-started
        if status=='REJECT' and job.frame is not current:
            self.scheduler_stats['ancestor_prunes']+=1;raise AncestorRejected(job.frame)

    def statistics(self):
        result=super().statistics()
        result['frontier']['mode']=self.focus_mode
        result['frontier']['focus']=dict(self.focus_stats)
        return result
