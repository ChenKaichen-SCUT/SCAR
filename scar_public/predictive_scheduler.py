"""Online cost and frame-survival prediction, with a non-pruning shadow control."""
from time import perf_counter
from scar_public.frontier_scheduler import AncestorRejected
from scar_public.focused_scheduler import FocusedPlanner
from scar_public.certificate_refinement import projection_view
from scar_public.online_cost_model import PredictiveCapacity,LifetimeModel,timely_forecast
from scar_public.threshold_search import ThresholdPlanner


class PredictivePlanner(FocusedPlanner):
    def __init__(self,task,mode='joint'):
        if mode not in ('shadow','observe','joint'):raise ValueError(mode)
        super().__init__(task,'focused')
        self.predict_mode=mode;self.life=LifetimeModel();self.context=[];self.frame_meta={}
        self.predictions=[];self.query_log=[];self.closed_queries=[]
        self.pred_stats=dict(forecasts=0,gate_skips=0,cold_probes=0,model_seconds=0.,
            completed_queries=0,retired_queries=0,prediction_log_dropped=0,
            shadow_rejects=0,delivered_units=0,delivered_expansions=0)
        self.delivery_rate=None;self.last_delivery=None;self.rejects=0;self.passes=0

    def engine(self,extra):
        if extra not in self.engines:
            self.engines[extra]=PredictiveCapacity(projection_view(self.task,extra),self.pool)
        return self.engines[extra]

    def admit(self,frame):
        start=perf_counter();before=self.inference_seconds
        if self.context:self.context[-1]=frame
        self.frame_meta[frame]=dict(start=self.expanded,predictions=[],queries=[])
        super().admit(frame)
        overhead=perf_counter()-start
        self.inference_seconds=before+overhead
        self.pred_stats['model_seconds']+=overhead

    def decision(self,belief,budget):
        if self.inference_seconds>=3 or (self.scheduler_stats['admitted']>=64
                                         and not any(not j.resolved for j in self.jobs)):
            # No future request can be served. Preserve exact search ordering
            # without creating lifetime records or running prediction callbacks.
            return ThresholdPlanner.decision(self,belief,budget)
        self.context.append(None);normal=False
        try:
            result=super().decision(belief,budget);normal=True;return result
        finally:
            frame=self.context.pop()
            if frame is not None:
                start=perf_counter();meta=self.frame_meta.pop(frame)
                duration=self.expanded-meta['start']
                censored=not normal or (frame.job is not None and frame.job.status=='REJECT'
                                         and self.predict_mode!='shadow')
                # First close logged outcomes, then learn. No prediction is
                # revised using this frame's later duration or bound result.
                for entry,job,spent in meta['predictions']:
                    entry['frame_exit_expansions']=duration
                    entry['residual_expansions']=self.expanded-entry['at_expanded']
                    entry['frame_censored']=censored
                    entry['timely_completed']=job.node.done if not censored else None
                    entry['timely_rejected']=(job.node.done and job.node.upper<job.candidates) if not censored else None
                    if job.node.done:entry['actual_remaining_units']=max(0,job.units-spent)
                    else:entry['work_observed_lower']=max(0,job.units-spent)
                for job in meta['queries']:
                    if not job.resolved:
                        job.resolved=True;job.status='RETIRED';self.pred_stats['retired_queries']+=1
                        self.scheduler_stats['retired']+=1
                    job.log.update(status=job.status,completed=job.node.done,units=job.units,
                        slices=job.slices,frame_censored=censored,frame_duration=duration)
                self.life.observe(frame,duration,not censored)
                elapsed=perf_counter()-start;self.inference_seconds+=elapsed
                self.pred_stats['model_seconds']+=elapsed

    def start_query(self,frame):
        job=super().start_query(frame)
        if job is not None:
            job.log=dict(query=job.identifier,depth=frame.budget,stack_depth=frame.depth,
                status='OPEN',completed=False,candidates=job.candidates,started_at=self.expanded)
            self.query_log.append(job.log);self.frame_meta[frame]['queries'].append(job)
        return job

    def forecast(self,job,quota):
        start=perf_counter();cost=job.engine.predict(job.node)
        meta=self.frame_meta[job.frame];age=self.expanded-meta['start']
        exact=max(1e-6,perf_counter()-self.scheduler_start-self.inference_seconds)
        per_expansion=exact/max(1,self.expanded)
        rate=job.engine.seconds_per_unit
        # Future delivery is limited by both cadence and earned inference credit.
        theoretical=min(8192/8,.5*per_expansion/max(1e-9,rate))
        delivery=theoretical if self.delivery_rate is None else min(theoretical,self.delivery_rate)
        table=self.life.table(job.frame)
        timely=timely_forecast(cost,table,age,quota,delivery,rate,max(0,3-self.inference_seconds))
        reject_probability=(1+self.rejects)/(2+self.rejects+self.passes)
        result=dict(query=job.identifier,depth=job.frame.budget,stack_depth=job.frame.depth,
            at_expanded=self.expanded,age=age,work_spent=job.units,quota=quota,
            delivery_units_per_expansion=delivery,rate_seconds=rate,cost=cost,**timely,
            rejection_probability=reject_probability,
            timely_rejection_probability=timely['probability']*reject_probability,
            lifetime_version=table.version,outcome_samples=self.rejects+self.passes,
            frame_censored=None,timely_completed=None,timely_rejected=None)
        self.pred_stats['forecasts']+=1;self.pred_stats['model_seconds']+=perf_counter()-start
        return result

    def service(self,current):
        if self.inference_seconds>=3:return
        if self.expanded-self.last_service<8 and self.last_service>=0:return
        self.last_service=self.expanded;started=perf_counter()
        active={id(f) for f in self.stack}
        self.jobs=[j for j in self.jobs if not j.resolved and id(j.frame) in active and self.actionable(j)]
        for identity,frame in list(self.candidates.items()):
            rec=self.record(frame.belief)
            if identity not in active or not rec.lower<=frame.budget<rec.upper:
                self.candidates.pop(identity);self.focus_stats['unstarted_retired']+=1
        exact=max(0.,perf_counter()-self.scheduler_start-self.inference_seconds)
        allowance=min(.025,max(0.,min(3.,.05+.5*exact)-self.inference_seconds),3-self.inference_seconds)
        if allowance<.001:
            self.scheduler_stats['budget_skips']+=1
            self.inference_seconds+=perf_counter()-started;return
        job=None
        if self.jobs:job=self.jobs[0]  # One active continuation; isolate prediction/gating.
        elif self.scheduler_stats['admitted']<64 and self.candidates:
            frame=max(self.candidates.values(),key=lambda f:(self.candidate_score(f),-f.depth))
            job=self.start_query(frame)
        if job is None:
            self.inference_seconds+=perf_counter()-started;return
        quota=max(128,min(8192,int(allowance/job.engine.seconds_per_unit)))
        prediction=self.forecast(job,quota)
        if len(self.predictions)<1024:
            self.predictions.append(prediction)
            self.frame_meta[job.frame]['predictions'].append((prediction,job,job.units))
        else:self.pred_stats['prediction_log_dropped']+=1
        # Cold probes expose the local recurrence before gating a continuation.
        # A low-probability request is deferred, never converted into infeasibility.
        gate=(self.predict_mode=='joint' and job.slices>0 and prediction['lifetime_samples']>=16
              and prediction['upper']<.5)
        prediction['gated']=gate
        if gate:
            self.pred_stats['gate_skips']+=1;self.inference_seconds+=perf_counter()-started;return
        if not job.slices:self.pred_stats['cold_probes']+=1
        allowance=max(0.,allowance-(perf_counter()-started))
        if allowance<.0001:
            prediction['no_slice_budget']=True;self.inference_seconds+=perf_counter()-started;return
        before=job.engine.work['units'];slice_start=perf_counter()
        job.engine.advance(job.node,units=quota,seconds=allowance)
        used=job.engine.work['units']-before;elapsed=perf_counter()-slice_start
        self.scheduler_stats['resumed']+=bool(job.slices);self.scheduler_stats['slices']+=1
        job.slices+=1;job.units+=used;job.seconds+=elapsed
        if self.last_delivery is not None and self.expanded>self.last_delivery:
            gap=self.expanded-self.last_delivery
            measured=used/gap
            self.delivery_rate=measured if self.delivery_rate is None else .8*self.delivery_rate+.2*measured
            self.pred_stats['delivered_expansions']+=gap
        self.last_delivery=self.expanded;self.pred_stats['delivered_units']+=used
        prediction['slice_work']=used;prediction['slice_seconds']=elapsed
        if job.node.done:
            rejected=job.node.upper<job.candidates
            job.status='REJECT' if rejected else 'BOUND_PASS';job.resolved=True
            self.pred_stats['completed_queries']+=1
            self.rejects+=rejected;self.passes+=not rejected
            self.scheduler_stats['passes']+=not rejected
            if rejected:
                if self.predict_mode=='shadow':self.pred_stats['shadow_rejects']+=1
                else:
                    rec=self.record(job.frame.belief);rec.lower=max(rec.lower,job.frame.budget+1)
                    assert rec.lower<=rec.upper
                    self.scheduler_stats['prunes']+=1
        job.log.update(status=job.status,completed=job.node.done,units=job.units,slices=job.slices)
        self.inference_seconds+=perf_counter()-started
        if job.status=='REJECT' and self.predict_mode!='shadow' and job.frame is not current:
            self.scheduler_stats['ancestor_prunes']+=1;raise AncestorRejected(job.frame)

    def statistics(self):
        result=super().statistics()
        result['prediction']=dict(self.pred_stats,mode=self.predict_mode,
            lifetime_events=self.life.observed,lifetime_censored=self.life.censored,
            queries=self.query_log,forecasts=self.predictions,
            engines=[dict(e.model_stats) for e in self.engines.values()])
        return result
