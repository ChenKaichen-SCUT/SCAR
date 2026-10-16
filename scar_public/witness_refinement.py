"""Second-stage development: skip C1 only with a saturation witness W=N.

The first frozen study is preserved in resource_validation_upload.zip.
No new empirical pressure threshold is fitted. W is a lower bound on optimistic
C1, so W=N proves this capacity recurrence cannot reject at this query.
"""
from scar_public.incremental_channels import IncrementalCoverage
from scar_public.amortized_refinement import AmortizedCoverage
from scar_public.decision_coverage import DecisionPlanner


class WitnessCoverage(IncrementalCoverage):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.witness_gate_stats = dict(queries=0,saturated_skips=0,relation_attempts=0)

    def decide(self,belief,budget,mode):
        prune,e = super().decide(belief,budget,'count_threshold')
        if prune or mode=='count_threshold' or e['reason']!='count_pass':
            return prune,e
        live = [(n,s) for n,s in belief if not self.task.goal.holds(s)]
        key = self.project(live[0][1]); mask = sum(self.model_bits[n] for n,_ in live)
        self.witness_gate_stats['queries'] += 1
        value = self.witness_value(key,mask,budget)
        if value >= mask.bit_count():
            self.witness_gate_stats['saturated_skips'] += 1
            return False,dict(e,reason='witness_certified_no_threshold_effect',witness=value)
        self.witness_gate_stats['relation_attempts'] += 1
        prune,e = super().decide(belief,budget,'relation_threshold')
        return prune,dict(e,witness=value)


class WitnessAmortizedCoverage(AmortizedCoverage):
    coverage_type = WitnessCoverage

    @property
    def stats(self):
        result = super().stats
        result['witness_gate'] = {k:sum(b.witness_gate_stats[k] for b in self.refined.values())
            for k in ('queries','saturated_skips','relation_attempts')}
        return result


class WitnessPlanner(DecisionPlanner):
    def __init__(self,task):
        super().__init__(task,'relation_threshold')
        self.target_coverage = WitnessAmortizedCoverage(task)
