"""Second development stage after first-stage premature retirement diagnosis."""
from scar_public import study_frontier_scheduler as previous
from scar_public import study_resource_validation as base


def manifest(cache):
    result=previous.manifest(cache)
    result['modes']=['focus_root','focus_priority','focus_multistep']
    result['scope']='Second development stage on same observed 50 configs. New sparse action catalogs and depth-one shortcut. Admit only when work is assigned; do not consume admissions on unstarted frames. Compare root-only continuation and focused scheduling with/without multi-step refinement. Reuse all unchanged baselines and first-stage results.'
    result['limits']+=' Candidate frame registration does not allocate an inference node; pending actionable work takes precedence over opening another request. Same64 actual admissions and3s total inference cap.'
    return result


if __name__=='__main__':
    base.MODES=['focus_root','focus_priority','focus_multistep'];base.manifest=manifest;base.main()
