"""Cache harvesting and admission batching; followup development, no new baselines."""
from scar_public import study_multistep_refinement as previous
from scar_public import study_resource_validation as base


def manifest(cache):
    result=previous.manifest(cache)
    result['modes']=['cached_multistep','batched_work','batched_multistep']
    result['evaluation_stage']='Second development stage after inspecting first-stage starvation; same observed cases.'
    result['new_limits'].update(trace_depth='Shortest already cached saturated root depth, at most current H',
        refinement_rounds='At most 3 per run',trace_attempts=12,initial_batch=128,max_batch=1024,
        admission='Defer before consuming an attempt if available work is below batch; double spent slice after exhaustion.')
    return result


if __name__=='__main__':
    base.MODES=['cached_multistep','batched_work','batched_multistep']
    base.manifest=manifest
    base.main()
