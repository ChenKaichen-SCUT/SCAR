"""Observed development suite: reusable continuations and hot-work scheduling."""
from scar_public import study_resource_validation as base

original_manifest=base.manifest


def manifest(cache):
    result=original_manifest(cache)
    result['modes']=['frontier_fifo','frontier_priority','frontier_multistep']
    result['scope']='Development only: all 50 cases already observed, 46 after prior duplicate audit. Run only three changed variants; reuse saved leaf, amortized_relation, final_work and persistent_multistep baselines. No LLM/API calls.'
    result['limits']='Same 15s/2GiB and H16 Rover/H60 other task caps;256 models/20000 actions. Optional wall time <=3s/run, slices <=.025s; atomic SAT can overrun. Slice units=clamp128..8192(allowance/measured seconds per unit), EWMA .8/.2, initial2us/unit. One unit per lookup/scan/assembly, 32 additional units per SAT call. At most64 query admissions, resume an admitted query without consuming an additional admission. Service every8 exact expansions. Credit=.05+.5*exact elapsed capped3s. Trace <=12 attempts/3 refinements/6 identities; .05s per attempt within slice deadline.'
    result['queries']='No stronger-control reruns. New resumable C1 equals unbounded completed old C1 on exact small-instance regression. All first-stage full-run outcomes retained. Frozen implementation before viewing these new outcomes.'
    return result


if __name__=='__main__':
    base.MODES=['frontier_fifo','frontier_priority','frontier_multistep']
    base.manifest=manifest
    base.main()
