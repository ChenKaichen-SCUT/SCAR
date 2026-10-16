"""Resume still-actionable queries on the active exact-search stack.

Priority uses remaining exact action alternatives, completed abstract action
checks and a hot-work-inclusive dependency-spine estimate. It is an explicit
heuristic, not an optimal value-of-computation theorem. Only a certified upper
endpoint below the query's candidate count changes a search lower bound.
"""
from dataclasses import dataclass
from time import perf_counter
from math import inf
from scar_public.indexed_planner import IndexedPlanner
from scar_public.threshold_search import InterruptedSearch
from scar_public.certificate_refinement import RefinementCoverage,projection_view,indices
from scar_public.incremental_channels import ChannelPool
from scar_public.resumable_capacity import ResumableCapacity
from scar_public.multistep_refinement import path_core
from scar_public.budgeted_planner import InferenceStop
from scar_public.symbolic_coverage import Unavailable


@dataclass(eq=False)
class Frame:
    belief: frozenset
    budget: int
    depth: int
    remaining_actions: int = 1
    job: object = None


@dataclass(eq=False)
class Query:
    frame: Frame
    engine: object
    node: object
    extra: int
    candidates: int
    live: list
    slices: int = 0
    seconds: float = 0.
    units: int = 0
    resolved: bool = False
    status: str = 'PENDING'


class AncestorRejected(Exception):
    def __init__(self,frame):self.frame=frame


class FrontierPlanner(IndexedPlanner):
    def __init__(self,task,mode='priority_multistep'):
        super().__init__(task)
        if mode not in ('fifo','priority','priority_multistep'):raise ValueError(mode)
        self.mode=mode;self.stack=[];self.jobs=[];self.engines={};self.pool=ChannelPool(task)
        self.selector=RefinementCoverage(task);self.identities=0;self.selected=False
        self.inference_seconds=0.;self.scheduler_start=perf_counter();self.last_service=-8
        self.last_job=None;self.service_count=0;self.evidence=[]
        self.scheduler_stats=dict(admitted=0,resumed=0,retired=0,prunes=0,ancestor_prunes=0,
            passes=0,slices=0,admission_skips=0,selection_seconds=0.,ranking_seconds=0.,
            assembly_seconds=0.,refinement_seconds=0.,budget_skips=0)
        self.trace_stats=dict(paths=0,multi_step_paths=0,spurious_paths=0,linked_satisfiable=0,
            sat_checks=0,core_minimizations=0,refinements=0,interrupted=0,attempts=0,traces=[])

    def engine(self,extra):
        if extra not in self.engines:
            self.engines[extra]=ResumableCapacity(projection_view(self.task,extra),self.pool)
        return self.engines[extra]

    def admit(self,frame):
        if self.scheduler_stats['admitted']>=64:return
        live=[(n,s) for n,s in frame.belief if not self.task.goal.holds(s)]
        if len(live)<2 or len({self.selector.project(s) for _,s in live})!=1:return
        started=perf_counter()
        if not self.selected:
            self.selector.deadline=started+.01
            try:self.identities|=self.selector.select(live)[0]
            except (InferenceStop,Unavailable):pass
            self.selected=True
            self.scheduler_stats['selection_seconds']+=perf_counter()-started
        _,common=self.selector.known(live)
        extra=self.identities&common;engine=self.engine(extra)
        key=engine.owner.project(live[0][1]);mask=sum(engine.owner.model_bits[n] for n,_ in live)
        node=engine.node(key,mask,frame.budget)
        frame.job=Query(frame,engine,node,extra,len(live),live)
        self.jobs.append(frame.job);self.scheduler_stats['admitted']+=1
        self.inference_seconds+=perf_counter()-started

    def actionable(self,job):
        rec=self.record(job.frame.belief)
        return not job.resolved and rec.lower<=job.frame.budget<rec.upper

    def score(self,job):
        n=job.node;engine=job.engine
        # Rejection can still remove these active exact alternatives. This is
        # available work, not the already spent search effort (a sunk cost).
        impact=max(1,job.frame.remaining_actions)
        progress=1+n.closed/max(1,len(engine.actions))
        # Exposure of a near-threshold lower bound makes this query more likely
        # to prove saturation rather than rejection; retain, but discount it.
        gap=max(1,job.candidates-n.lower)
        estimated=max(1e-6,engine.frontier_cost(n)*engine.seconds_per_unit)
        return impact*progress*(gap/job.candidates)/estimated

    def refine(self,job,deadline):
        if self.mode!='priority_multistep' or self.trace_stats['refinements']>=3 or self.trace_stats['attempts']>=12:
            return False
        self.trace_stats['attempts']+=1
        owner=job.engine.owner;owner.deadline=min(deadline,perf_counter()+.05)
        _,common=self.selector.known(job.live)
        started=perf_counter()
        try:
            for name,state in sorted(job.live,key=lambda x:x[0]):
                path=job.engine.path(job.node,owner.model_bits[name])
                if not path:continue
                self.trace_stats['paths']+=1;self.trace_stats['multi_step_paths']+=len(path)>1
                core=path_core(owner,path,state.symbols[0],common&~job.extra,self.trace_stats)
                if not core or (self.identities|core).bit_count()>6:continue
                self.identities|=core;extra=(job.extra|core)&common
                engine=self.engine(extra);key=engine.owner.project(job.live[0][1])
                mask=sum(engine.owner.model_bits[n] for n,_ in job.live)
                job.engine=engine;job.node=engine.node(key,mask,job.frame.budget);job.extra=extra
                self.trace_stats['refinements']+=1
                self.trace_stats['traces'].append(dict(depth=job.frame.budget,model=name,
                    actions=[p[1] for p in path],added_atoms=[self.task.atom_names[i] for i in indices(core)]))
                return True
        except (InferenceStop,Unavailable):self.trace_stats['interrupted']+=1
        finally:self.scheduler_stats['refinement_seconds']+=perf_counter()-started
        return False

    def service(self,current):
        if self.inference_seconds>=3 or not self.jobs:return
        # Queue inspection itself is throttled and its wall time is included.
        if self.expanded-self.last_service<8 and self.last_service>=0:return
        self.last_service=self.expanded
        started=perf_counter()
        pending=[]
        active={id(f) for f in self.stack}
        for j in self.jobs:
            if not j.resolved and (id(j.frame) not in active or not self.actionable(j)):
                j.resolved=True;j.status='STALE';self.scheduler_stats['retired']+=1
            if not j.resolved:pending.append(j)
        self.jobs=pending
        if not pending:
            self.inference_seconds+=perf_counter()-started;return
        exact_elapsed=max(0.,perf_counter()-self.scheduler_start-self.inference_seconds)
        credit=min(3.,.05+.5*exact_elapsed)-self.inference_seconds
        allowance=min(.025,max(0.,credit),3.-self.inference_seconds)
        if allowance<.001:
            self.scheduler_stats['budget_skips']+=1
            self.inference_seconds+=perf_counter()-started;return
        if self.mode=='fifo':
            job=min(pending,key=lambda j:(j.slices,j.frame.depth))
        else:
            # At a tie, resume existing work and prefer an ancestor. Completed
            # checks are evidence; total elapsed work is not added to benefit.
            job=max(pending,key=lambda j:(self.score(j),j is self.last_job,-j.frame.depth))
        self.scheduler_stats['ranking_seconds']+=perf_counter()-started
        predicted=job.engine.frontier_cost(job.node)
        before=job.engine.work['units'];slice_start=perf_counter()
        if job.slices:self.scheduler_stats['resumed']+=1
        job.slices+=1;self.scheduler_stats['slices']+=1;self.last_job=job
        quota=max(128,min(8192,int(allowance/job.engine.seconds_per_unit)))
        job.engine.advance(job.node,units=quota,seconds=allowance)
        status='PENDING'
        if job.node.upper<job.candidates:
            rec=self.record(job.frame.belief);rec.lower=max(rec.lower,job.frame.budget+1)
            assert rec.lower<=rec.upper
            job.resolved=True;status=job.status='REJECT'
            self.scheduler_stats['prunes']+=1
        elif job.node.lower>=job.candidates:
            if not self.refine(job,slice_start+allowance):
                job.resolved=True;status=job.status='BOUND_PASS';self.scheduler_stats['passes']+=1
            else:status='REFINED'
        elapsed=perf_counter()-slice_start;job.seconds+=elapsed
        work=job.engine.work['units']-before if status!='REFINED' else None
        if work is not None:job.units+=work
        if len(self.evidence)<192:
            self.evidence.append(dict(depth=job.frame.budget,stack_depth=job.frame.depth,
                prediction=predicted,work=work,seconds=elapsed,status=status,
                quota=quota,
                lower=job.node.lower,upper=job.node.upper,candidates=job.candidates,
                remaining_exact_actions=job.frame.remaining_actions,slices=job.slices))
        self.inference_seconds+=perf_counter()-started
        if status=='REJECT' and job.frame is not current:
            self.scheduler_stats['ancestor_prunes']+=1
            raise AncestorRejected(job.frame)

    def decision(self,belief,budget):
        """Same ordering/semantics as ThresholdPlanner plus safe ancestor exits."""
        self.search_stats['decisions']+=1;rec=self.record(belief)
        if rec.upper<=budget:
            self.search_stats['decision_hits']+=1;return True
        if rec.lower>budget:
            self.search_stats['bound_prunes']+=1;return False
        rec=self.estimate(belief,budget)
        if rec.upper<=budget:return True
        if rec.lower>budget:
            self.search_stats['bound_prunes']+=1;return False
        frame=Frame(belief,budget,len(self.stack));self.stack.append(frame)
        try:
            if self.inference_seconds<3:self.admit(frame)
            self.service(frame)
            if rec.lower>budget:return False
            if self.remaining is not None:
                if self.remaining<=0:raise InterruptedSearch()
                self.remaining-=1
            self.expanded+=1;edges=self.edges(belief)
            order=sorted(edges,key=lambda e:(max(self.record(b).lower for b in e[1].values()),e[0]))
            frame.remaining_actions=len(order)
            for action,branches in order:
                children=sorted(branches.values(),key=lambda b:(self.record(b).lower,len(b)),reverse=True)
                if all(self.decision(child,budget-1) for child in children):
                    value=1+max(self.record(b).upper for b in branches.values())
                    if value<rec.upper:
                        rec.upper=value;rec.policy=dict(action=action,branches={o:self.record(b).policy for o,b in branches.items()})
                    self.search_stats['successful_decisions']+=1
                    assert rec.lower<=rec.upper<=budget;return True
                frame.remaining_actions-=1
            rec.lower=max(rec.lower,budget+1)
            if not edges:rec.lower=inf
            self.search_stats['failed_decisions']+=1;assert rec.lower<=rec.upper
            return False
        except AncestorRejected as interrupted:
            if interrupted.frame is not frame:raise
            return False
        finally:
            assert self.stack[-1] is frame;self.stack.pop()

    def statistics(self):
        return dict(super().statistics(),frontier=dict(self.scheduler_stats,seconds=self.inference_seconds,
            mode=self.mode,trace=self.trace_stats,evidence=self.evidence,
            engines=[dict(projection=[self.task.atom_names[i] for i in indices(extra)],
                work=e.work,nodes=len(e.nodes),templates=len(e.templates)) for extra,e in self.engines.items()]))
