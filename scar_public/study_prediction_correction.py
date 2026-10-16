"""Correct current-action debit and stop maintenance when no request can start."""
from scar_public import study_online_prediction as previous
from scar_public import study_resource_validation as base


def manifest(cache):
    result=previous.manifest(cache)
    result['modes']=['forecast_shadow','forecast_gate']
    result['scope']='Second development stage:100 changed-variant runs on the same50 observed configs. Preserve all first-stage outcomes; no old baseline reruns. Fix current-action debit so it cannot erase future actions, and bypass prediction/lifetime maintenance after no further requests can be admitted. No fitted coefficient or threshold changes.'
    return result


if __name__=='__main__':
    base.MODES=['forecast_shadow','forecast_gate'];base.manifest=manifest;base.main()
