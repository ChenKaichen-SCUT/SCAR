"""Prediction-first development audit. No saved solver outcome enters learning."""
from scar_public import study_frontier_scheduler as previous
from scar_public import study_resource_validation as base


def manifest(cache):
    result=previous.manifest(cache)
    result['modes']=['forecast_shadow','forecast_observe','forecast_gate']
    result['scope']='All50 configurations are observed development data,46 distinct. 150 changed-variant runs. Reuse all baselines. No between-instance training; reset all predictors for each run. No old outcomes loaded by planner. No LLM/API calls.'
    result['limits']+=' Same sparse-catalog C1. No multistep refinement in this audit. At most1024 forecast records/run. Model overhead included in inference time and full elapsed time.'
    result['prediction']='Inclusive closed-action work includes new descendants. Per-engine last256 work samples by exact depth/candidate-size/resource-pressure; back off to depth with8 samples, otherwise lower-depth extrapolation growth1..8 or declared cold fallback. Five uncertainty scenarios, not calibrated confidence quantiles. Frame lifetimes use exact-expansion age, last256 natural/censored exits, root/depth/size strata with16 observations then backoff. Right-censored unresolved tail gives identification range. Future delivery limited by service cadence/earned credit and previous delivered-work rate. Shadow does not apply C1 rejections and must match leaf expansion count. Observe records predictions and applies certified rejections. Gate additionally defers a resumed query only when16 lifetime observations and optimistic timely-completion estimate<.5. Completion and rejection forecasts evaluated separately; censored labels never converted into negatives. Every query gets an initial probe; completed-node samples available only after closure.'
    return result


if __name__=='__main__':
    base.MODES=['forecast_shadow','forecast_observe','forecast_gate'];base.manifest=manifest;base.main()
