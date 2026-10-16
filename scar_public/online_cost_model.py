"""Prequential estimates. None of these estimates is a planning certificate."""
from collections import defaultdict,deque
from math import ceil,inf,log2
from scar_public.catalog_capacity import CatalogCapacity


def bucket(n):return max(0,int(log2(max(1,n))))


def quantiles(values,levels=(.1,.3,.5,.7,.9)):
    values=sorted(values)
    return [values[min(len(values)-1,int(q*len(values)))] for q in levels]


class Survival:
    """Bounded history, event=natural frame exit; interruptions are censored.

    The unresolved tail yields identification bounds, not confidence intervals.
    All observations must be supplied AFTER the associated prediction/outcome.
    """
    def __init__(self,limit=256):self.rows=deque(maxlen=limit);self.version=0

    def add(self,duration,event=True):
        self.rows.append((max(0,duration),bool(event)));self.version+=1

    def curve(self):
        counts=defaultdict(lambda:[0,0])
        for t,event in self.rows:counts[t][0 if event else 1]+=1
        risk=len(self.rows);survival=1.;curve=[]
        for t,(events,censored) in sorted(counts.items()):
            survival*=1-events/risk
            curve.append((t,survival));risk-=events+censored
        return curve

    def residual(self,age,required):
        if required<=0:return 1.,1.
        curve=self.curve()
        if not curve:return 0.,1.
        at_age=1.;at_target=1.
        for t,s in curve:
            if t<=age:at_age=s
            if t<=age+required:at_target=s
        if at_age<=0 or age>=curve[-1][0]:return 0.,1.
        upper=min(1.,at_target/at_age)
        return (0.,upper) if age+required>curve[-1][0] else (upper,upper)

    def median_remaining(self,age):
        curve=self.curve();at_age=1.
        for t,s in curve:
            if t<=age:at_age=s
        if at_age<=0:return None
        return next((t-age for t,s in curve if t>age and s/at_age<=.5),None)


class LifetimeModel:
    def __init__(self):self.tables=defaultdict(Survival);self.observed=0;self.censored=0

    def keys(self,frame):
        root=frame.depth==0
        return [(root,bucket(frame.budget),bucket(len(frame.belief))),
                (root,bucket(frame.budget)),(root,)]

    def observe(self,frame,duration,event):
        for key in self.keys(frame):self.tables[key].add(duration,event)
        self.observed+=bool(event);self.censored+=not event

    def table(self,frame):
        tables=[self.tables[k] for k in self.keys(frame)]
        return next((t for t in tables if len(t.rows)>=16),tables[-1])


class PredictiveCapacity(CatalogCapacity):
    """Learn inclusive action work: it contains newly exposed descendant work.

    Observations are taken only when an action closes, and retained across
    slices. They include memo hits and resource/child assembly from CatalogCapacity.
    Unknown-depth work is extrapolated from the nearest observed lower depth;
    the fallback is explicitly reported and has no admissibility claim.
    """
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.action_samples=defaultdict(lambda:deque(maxlen=256))
        self.catalog_samples=deque(maxlen=128);self.catalog_spent={};self.meta={}
        self.model_stats=dict(action_samples=0,catalog_samples=0,predictions=0,extrapolations=0)

    def profile(self,node):
        pressure=any(r<node.depth*c for r,c in zip(node.key[0],self.owner.max_consumption))
        return node.depth,bucket(node.mask.bit_count()),pressure

    def evaluate(self,node):
        if node.done:return node.lower
        if node not in self.meta:
            self.meta[node]=dict(units=0,closed=node.closed,at_close=0,catalog_ready=False)
        meta=self.meta[node]
        if node.runner is None:node.runner=self.compute(node)
        while not node.done:
            before=self.work['units']
            try:event=next(node.runner)
            except StopIteration:
                assert node.done;event=None
            # Each active ancestor gets only work driven through this call.
            # Other parents can advance a shared child without being charged here.
            meta['units']+=self.work['units']-before
            if not meta['catalog_ready'] and node.key[1] in self.catalogs:
                meta['catalog_ready']=True;meta['at_close']=meta['units']
            closed=node.closed-meta['closed']
            if closed>0:
                amount=max(1,(meta['units']-meta['at_close'])/closed)
                key=self.profile(node)
                self.action_samples[key].append(amount)
                self.action_samples[(node.depth,)].append(amount)
                self.model_stats['action_samples']+=1
                meta['at_close']=meta['units'];meta['closed']=node.closed
            if event is not None:yield event
        return node.lower

    def build_catalog(self,projected):
        source=super().build_catalog(projected)
        self.catalog_spent.setdefault(projected,0)
        while True:
            before=self.work['units']
            try:event=next(source)
            except StopIteration:
                self.catalog_spent[projected]+=self.work['units']-before
                self.catalog_samples.append(self.catalog_spent[projected])
                self.model_stats['catalog_samples']+=1
                return
            self.catalog_spent[projected]+=self.work['units']-before
            yield event

    def action_distribution(self,node):
        key=self.profile(node);samples=self.action_samples[key]
        if len(samples)>=8:return quantiles(samples),len(samples),False
        samples=self.action_samples[(node.depth,)]
        if len(samples)>=8:return quantiles(samples),len(samples),False
        for d in range(node.depth-1,0,-1):
            samples=self.action_samples[(d,)]
            if len(samples)<8:continue
            previous=self.action_samples[(d-1,)]
            growth=2.
            if len(previous)>=8:
                growth=min(8.,max(1.,quantiles(samples)[2]/max(1.,quantiles(previous)[2])))
            multiplier=min(1e6,growth**(node.depth-d))
            return [x*multiplier for x in quantiles(samples)],len(samples),True
        base=3+2*len(node.key[0])
        return [base*min(1e6,g**max(0,node.depth-1)) for g in (1.,1.4,2.,3.,4.)],0,True

    def predict(self,node):
        if node.done:return dict(units=[0.]*5,median=0.,old_spine=0,samples=0,fallback=False)
        current=node;seen=set();totals=[0.]*5;support=[];fallback=False
        while current is not None and not current.done and current not in seen:
            seen.add(current);projected=current.key[1];catalog=self.catalogs.get(projected)
            if catalog is None:
                spent=self.catalog_spent.get(projected,0)
                samples=[x for x in self.catalog_samples if x>spent]
                if len(samples)>=8:cold=[max(1,x-spent) for x in quantiles(samples)]
                else:
                    base=max(1,len(self.actions)*max(1,len(self.owner.group_masks))*32)
                    cold=[max(base*q,spent*q) for q in (.25,.5,1.,2.,4.)];fallback=True
                totals=[a+b for a,b in zip(totals,cold)]
            size=len(catalog) if catalog is not None else len(self.actions)
            distribution,n,extra=self.action_distribution(current);support.append(n);fallback|=extra
            waiting=current.waiting if current.waiting is not None and not current.waiting.done else None
            remaining=max(0,size-current.closed-(1 if waiting is not None else 0))
            meta=self.meta.get(current,{})
            partial=max(0,meta.get('units',0)-meta.get('at_close',0))
            # Do not subtract work spent inside the active child from unrelated
            # future actions. That child is predicted separately on the spine.
            for i,per_action in enumerate(distribution):
                unseen=remaining*per_action
                if waiting is None and remaining:
                    unseen=max(1.,unseen-min(partial,per_action))
                totals[i]+=unseen
            current=waiting
        totals=sorted(max(1.,x) for x in totals)
        self.model_stats['predictions']+=1;self.model_stats['extrapolations']+=fallback
        return dict(units=totals,median=totals[2],old_spine=self.frontier_cost(node),
                    samples=min(support,default=0),fallback=fallback)


def timely_forecast(cost,life,age,current_quota,delivery_rate,rate_seconds,remaining_seconds):
    """Conditional forecast for current slice plus stationary future delivery.

    Cost points are heuristic uncertainty scenarios, not calibrated quantiles.
    Independence of work and frame lifetime conditional on features is assumed.
    """
    bounds=[]
    for work in cost['units']:
        if work*rate_seconds>remaining_seconds:bounds.append((0.,0.));continue
        needed=max(0.,work-current_quota)/max(1e-9,delivery_rate)
        bounds.append(life.residual(age,ceil(needed)))
    low=sum(b[0] for b in bounds)/len(bounds);high=sum(b[1] for b in bounds)/len(bounds)
    return dict(probability=(low+high)/2,lower=low,upper=high,
                lifetime_samples=len(life.rows),remaining_expansions_median=life.median_remaining(age))
