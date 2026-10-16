"""Three changed variants on all 50 observed configs; old baselines reused."""
from scar_public import study_resource_validation as base

original_manifest = base.manifest


def manifest(cache):
    result = original_manifest(cache)
    result['modes'] = ['multistep','work_scheduled','multistep_scheduled']
    result['evaluation_stage'] = 'Development only: every input has been observed in previous studies.'
    result['scope'] = ('No unchanged baseline reruns. Compare multi-step selection, actual cache-miss '
        'work scheduling, and their combination against saved leaf/amortized results. '
        'No heldout or statistical significance claim. No LLM calls.')
    result['new_limits'] = dict(selection_seconds=.10, trace_depth=8, refinement_rounds=3,
        added_atoms=6, core_minimization_checks=64, bootstrap_work=128,
        work_per_search_expansion=4, total_work_cap=16384, per_query_work=1024)
    return result


if __name__ == '__main__':
    base.MODES = ['multistep','work_scheduled','multistep_scheduled']
    base.manifest = manifest
    base.main()
