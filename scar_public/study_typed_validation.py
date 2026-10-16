"""Audit six Woodworking configurations after adding general subtype support.

Post-run compiled-task hashes established that these particular tasks use only
leaf-type action parameters: their original grounding was already identical.
The earlier invalid-translation suspicion in the frozen audit manifest was
incorrect; type_audit.json records the correction. Original timings stay primary.
"""
from scar_public import study_resource_validation as base
from scar_public import fresh_resource_suite as suite

original_manifest = base.manifest
original_configurations = suite.configurations


def configurations():
    return [c for c in original_configurations() if c['family']=='woodworking']


def manifest(cache):
    result=original_manifest(cache)
    result['evaluation_stage']='Supplementary type-semantics audit; six hierarchical-type inputs only.'
    result['scope']=('General transitive type membership is now supported. Complete compiled-task hashes '
        'proved that these particular Woodworking tasks were already identical because their action '
        'parameters use leaf types. Original timings remain primary. The archived initial audit manifest '
        'contains a superseded invalid-translation suspicion, corrected in type_audit.json. '
        'All extra runs are audit evidence, not independent performance observations.')
    return result


if __name__=='__main__':
    suite.configurations=configurations
    base.MODES=base.MODES+['witness_amortized']
    base.manifest=manifest
    base.main()
