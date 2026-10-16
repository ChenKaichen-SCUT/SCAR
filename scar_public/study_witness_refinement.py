"""Only rerun the changed method; reuse the five frozen baseline result sets."""
from scar_public import study_resource_validation as base

original_manifest = base.manifest


def manifest(cache):
    result = original_manifest(cache)
    result['modes'] = ['witness_amortized']
    result['evaluation_stage'] = 'Development after all first-study outcomes were inspected; not independent validation.'
    result['scope'] = ('Reuse the same 50 configurations and all five frozen baselines. '
        'Only the witness-gated amortized variant is new. A scalar-tree witness W=N '
        'certifies C1=N and skips the identity recurrence. Otherwise complete C1 is required. '
        'All parsing/selection/witness/inference costs included; same15s/2GiB budget.')
    return result


if __name__=='__main__':
    base.MODES=['witness_amortized']
    base.manifest=manifest
    base.main()
