"""Post-holdout engineering diagnostic, not the frozen evaluation method.

Bounds interrupted during a transition loop retain only completed old evidence.
Separate file preserves the preregistered implementation and its source hashes.
"""
from time import perf_counter
from scar_public.budgeted_planner import BudgetedPlanner


class TailStop(Exception):pass


class TransitionBudgetedPlanner(BudgetedPlanner):
    def __init__(self,task,mode='leaf_lineage_scheduled'):
        super().__init__(task,mode)
        self.tail_active=False;self.tail_steps=0;self.tail_query_steps=0
        self.tail_limit=65536;self.tail_query_limit=4096;self.tail_deadline=float('inf')
        self.tail_seconds=0.;self.tail_stops=0;self.scheduler_skips=0

    def hmax(self,state):
        bits=state.symbols[0]
        if bits in self.hmax_cache:return self.hmax_cache[bits]
        if self.cost_stats['hmax_work']>=2000000:
            self.cost_stats['hmax_fallbacks']+=1;return 0
        return super().hmax(state)

    def _step(self,world,action):
        if self.tail_active:
            if (self.tail_steps>=self.tail_limit or self.tail_query_steps>=self.tail_query_limit
                    or perf_counter()>=self.tail_deadline):raise TailStop()
            self.tail_steps+=1;self.tail_query_steps+=1
        return super()._step(world,action)

    def known_world(self,world,budget):
        self.tail_active=True;self.tail_query_steps=0
        # The allowance covers hmax too, conservatively reducing BFS time.
        started=perf_counter();self.tail_deadline=started+min(.05,max(0.,1.-self.tail_seconds))
        try:return super().known_world(world,budget)
        except TailStop:
            self.tail_stops+=1;self.cost_stats['bfs_fallbacks']+=1
            # Parent has not installed a partial BFS layer/policy on this path.
            return self.world_records[world]
        finally:
            self.tail_active=False;self.tail_seconds+=perf_counter()-started

    def optional_lower(self,belief,budget,cheap):
        if self.variant_mode.endswith('scheduled'):
            spent=self.cost_stats['coverage_seconds']
            elapsed=perf_counter()-self.inference_start
            credit=min(3.,.25+.25*max(0.,elapsed-spent))
            if self.cost_stats['coverage_attempts']>=32 or credit-spent<.025:
                self.scheduler_skips+=1;self.cost_stats['coverage_skipped']+=1;return cheap
        return super().optional_lower(belief,budget,cheap)

    def statistics(self):
        return dict(super().statistics(),transition_budget=dict(steps=self.tail_steps,
            seconds=self.tail_seconds,stops=self.tail_stops,scheduler_skips=self.scheduler_skips))
