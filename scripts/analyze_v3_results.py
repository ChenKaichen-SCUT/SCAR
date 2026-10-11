"""Formal result analysis including observed bounded-format method terminations.

Post-hoc handling is disclosed; original raw statuses and frozen code stay intact.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path

import numpy as np

from scar.io import atomic_json, digest
from scripts.v3_outcomes import disposition


def paired_interval(pairs, cluster, seed=314159, repetitions=10000):
    groups = defaultdict(list)
    for case, difference in pairs:
        groups[case[cluster]].append(difference)
    values = list(groups.values())
    rng = np.random.default_rng(seed)
    n = len(values)
    if not n:
        return None
    sums = np.array([sum(v) for v in values]); counts = np.array([len(v) for v in values])
    indices = rng.integers(n, size=(repetitions, n))
    draws = sums[indices].sum(axis=1)/counts[indices].sum(axis=1)
    return {"difference": float(sums.sum()/counts.sum()), "ci95": np.quantile(draws, [.025, .975]).tolist(),
            "cluster": cluster, "clusters": n, "families": len(pairs),
            "scope": "Percentile paired cluster bootstrap, descriptive and not multiple-comparison adjusted; small source-cluster counts limit inference."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--cases", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root, output = Path(args.runtime), Path(args.output)
    cases = json.loads(Path(args.cases).read_text())
    cfg = json.loads(Path("configs/protocol_v3.json").read_text())
    rows = [json.loads(p.read_text()) for p in sorted((root/"runs").glob("*/summary.json"))]
    # A modified implementation creates another cohort; require explicit review,
    # never pool multiple outcomes from the same method/family or game/seed.
    evaluated = [dict(r, outcome_disposition=disposition(r,root/"runs"/r["task_id"])) for r in rows]
    hard = [r for r in evaluated if r.get("stage") == "hard" and r["outcome_disposition"] != "incomplete"]
    long = [r for r in evaluated if r.get("stage") == "long" and r["outcome_disposition"] != "incomplete"]
    for r in hard:
        if r["outcome_disposition"] == "method_terminated_format_failure":
            if r.get("recovery_steps") is not None:
                raise ValueError("Successful goal followed by policy termination violates early-stop protocol")
            assert not any(r[f"recovery_at_{h}"] for h in [10,20,40])

    index = {(r["family"], r["algorithm"]): r for r in hard}
    if len(index) != len(hard) or len({(r["game"], r["algorithm"]) for r in long}) != len(long):
        raise ValueError("Duplicate cohort results require explicit separation")
    test = [c for c in cases if c["split"] == "test"]
    expected = {(c["family"], a) for c in test for a in cfg["algorithms"]}
    complete = set(index) == expected
    totals = {}
    for method in cfg["algorithms"]:
        subset = [r for r in hard if r["algorithm"] == method]
        totals[method] = {"evaluated":len(subset), "completed":sum(r["status"] == "completed" for r in subset), "method_terminations":sum(r["outcome_disposition"] == "method_terminated_format_failure" for r in subset)}
        if subset:
            totals[method].update({f"recovery_at_{k}": sum(r[f"recovery_at_{k}"] for r in subset)/len(subset) for k in [10, 20, 40]})
            totals[method].update({k: sum(r.get(k, 0) for r in subset) for k in ["api_calls", "input_tokens", "output_tokens", "conservative_cost_usd", "decision_wall_seconds", "steps", "interceptions", "false_blocks", "legal_to_rejected", "rejected_to_legal", "interventions_with_physical_goal", "interventions_with_condition_release", "release_opportunities", "successful_released_retries", "repeated_semantic_count"]})
    paired = []
    if complete:
        for method in cfg["algorithms"][:-1]:
            for horizon in [10, 20, 40]:
                pairs = [(c, int(index[c["family"], "SCARV3Agent"][f"recovery_at_{horizon}"])-int(index[c["family"], method][f"recovery_at_{horizon}"])) for c in test]
                paired.append({"comparator": method, "horizon": horizon,
                               "uncertainty": [paired_interval(pairs, group) for group in ["family", "source_cluster", "mechanism_cluster"]]})
    by_type = []
    for kind in sorted({t for c in test for t in c["types"]}):
        families = {c["family"] for c in test if kind in c["types"]}
        for method in cfg["algorithms"]:
            rs = [r for r in hard if r["algorithm"] == method and r["family"] in families]
            by_type.append({"type": kind, "algorithm": method, "eligible_families": len(families), "evaluated": len(rs), "completed":sum(r["status"] == "completed" for r in rs), "method_terminations":sum(r["status"] != "completed" for r in rs),
                            "recovery_at_40": sum(r["recovery_at_40"] for r in rs)/len(rs) if rs else None})
    online = []
    for r in hard+long:
        for path in sorted((root/"runs"/r["task_id"]/"steps").glob("*/transition.json")):
            step = json.loads(path.read_text())
            for check in step.get("rule_tests", []):
                if "failure_probability" in check:
                    online.append({"task_id": r["task_id"], "index": step["index"], "truth": check["semantic_rejection"],
                                   "prediction": {"status": check["prediction_status"], "failure_probability": check["failure_probability"]}})
    from scripts.audit_v3_learning import metrics
    result = {"dataset_sha256": digest(cases), "hard_expected": len(expected), "hard_completed": sum(r["status"] == "completed" for r in hard), "hard_evaluated":len(hard), "hard_method_terminations":sum(r["status"] != "completed" for r in hard), "hard_complete": complete,
              "long_expected": 15, "long_completed": sum(r["status"] == "completed" for r in long), "long_evaluated":len(long), "long_method_terminations":sum(r["status"] != "completed" for r in long), "long_complete": len(long) == 15,
              "status": "complete_needs_scientific_review" if complete and len(long) == 15 else "INCOMPLETE",
              "hard_by_method": totals, "paired": paired, "by_type": by_type,
              "long": [{k: v for k, v in r.items() if k not in {"history", "goal"}} for r in long],
              "online_prequential_metrics": metrics(online),
              "limitations": ["Missing/infrastructure failures are not replaced by archived scores or assumed failures. Observed bounded-format policy aborts remain in the denominator as unsuccessful method outcomes, with original status/error/cost/steps preserved. This handling was clarified after two such aborts, before long experiments; no policy or frozen data was modified and no selective reruns were performed.",
                              "Long results are one seed per game; descriptive only.",
                              "Target action release is a progress proxy, separate from actual physical goal achievement.",
                              "Prediction coverage includes explicit rejection/support, with UNKNOWN abstention. Precision/recall alone are not causal evidence."]}
    atomic_json(output/"formal_status.json", result)
    atomic_json(output/"online_prequential_predictions.json", online)
    atomic_json(output/"all_summaries.json", rows)
    print(json.dumps({k: result[k] for k in ["status", "hard_completed", "hard_evaluated", "hard_expected", "long_completed", "long_evaluated", "long_expected"]}))


if __name__ == "__main__":
    main()
