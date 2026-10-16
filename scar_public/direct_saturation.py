"""Cheap sufficient certificate that lineage cannot prune, BEFORE channel SAT.

For one action, construct a legal abstract pre-state for every live static model
group that finishes the goal in one step. These witnesses may be unreachable.
They certify saturation of the optimistic bound, never feasibility of the task.
"""
from collections import defaultdict
from scar_public.decision_coverage import DecisionCoverage,DecisionPlanner
from scar_public.static_grounding import conjunction_masks
from scar_public.finite_planner import State


class SaturationCoverage(DecisionCoverage):
    def __init__(self,task):
        super().__init__(task);self.achievers=defaultdict(list);self.direct_cache=set()
        self.direct_stats=dict(queries=0,certificates=0,model_tests=0,cache_hits=0,work_skips=0)
        goal=conjunction_masks(task.goal_expr)
        if goal is not None:
            gp,gn=goal
            for name,a in task.actions.items():
                pre=conjunction_masks(a.pre)
                if pre is None:continue
                for guard,lit in a.effects:
                    bit=1<<(abs(lit)-1)
                    if not bit&(gp if lit>0 else gn):continue
                    condition=conjunction_masks(guard)
                    if condition is None:continue
                    # One target literal starts false; other goal literals true.
                    pos=pre[0]|condition[0]|(gp&~bit)|(bit if lit<0 else 0)
                    neg=pre[1]|condition[1]|(gn&~bit)|(bit if lit>0 else 0)
                    if not pos&neg:self.achievers[name].append((pos,neg))
        self.fixed_mask=(((1<<len(task.atom_names))-1)^task.dynamic_mask)|task.projection_mask

    def direct_saturation(self,belief,budget):
        self.direct_stats['queries']+=1
        live=[(n,s) for n,s in belief if not self.task.goal.holds(s)]
        keys={self.project(s) for _,s in live}
        if budget<1 or len(live)<2 or len(keys)!=1:return False
        key=next(iter(keys));mask=0
        for n,_ in live:mask|=self.model_bits[n]
        memo=key,mask
        if memo in self.direct_cache:self.direct_stats['cache_hits']+=1;return True
        statics=[s for s,group in self.group_masks.items() if group&mask]
        local=0
        for name,assignments in self.achievers.items():
            self.check();a=self.task.actions[name]
            if any(r<c for r,c in zip(key[0],a.consumption)):continue
            for static in statics:
                fixed=static|key[1];supported=False
                for pos,neg in assignments:
                    if pos&self.fixed_mask&~fixed or neg&self.fixed_mask&fixed:continue
                    if local>=2048 or self.direct_stats['model_tests']>=50000:
                        self.direct_stats['work_skips']+=1;return False
                    local+=1;self.direct_stats['model_tests']+=1
                    bits=fixed|(pos&~self.fixed_mask)
                    state=State((bits,True),key[0]);child,_=self.task.step(state,name)
                    if (self.task.allowed(child) and not self.task.goal.holds(state)
                            and self.task.goal.holds(child)):
                        supported=True;break
                if not supported:break
            else:
                self.direct_cache.add(memo);self.direct_stats['certificates']+=1;return True
        return False

    def decide(self,belief,budget,mode):
        if self.direct_saturation(belief,budget):
            return False,dict(reason='direct_abstract_saturation',budget=budget)
        return super().decide(belief,budget,mode)

    @property
    def stats(self):return dict(super().stats,direct=dict(self.direct_stats))


class DirectPlanner(DecisionPlanner):
    def __init__(self,task,mode='direct_gate'):
        if mode!='direct_gate':raise ValueError(mode)
        super().__init__(task,'relation_gate');self.target_coverage=SaturationCoverage(task)
