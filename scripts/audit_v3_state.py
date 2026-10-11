"""Stage 1: tri-valued matching on real archived states, without API calls."""
import argparse
import json
from pathlib import Path

from scar.environment import restore, AGENT_ID
from scar.diagnostics.scoring import score_candidate
from scar.io import atomic_json
from scar_v3.state import PublicState, Truth, Evidence


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--historical-runtime", required=True)
    parser.add_argument("--v2-runtime", required=True)
    parser.add_argument("--output", default="results/v3/state_audit.json")
    args = parser.parse_args()
    cases = json.loads((Path(args.historical_runtime) / "ao_fr_frozen/cases.json").read_text())
    checks = []
    for case in cases:
        if case["split"] != "test":
            continue
        env = restore(case["initial_snapshot"])
        state = None
        for event in case["history"]:
            state = PublicState.observe(event["before"], state)
            state = PublicState.observe(event["after"], state, event["action"])
        state = PublicState.observe(env.obs[AGENT_ID], state)
        # This is a controlled state-feature audit, not the learned V3 predictor.
        fact = state.features(case["target_action"]).get("hands.space", Evidence())
        predicted = True if fact.truth == Truth.FALSE else None
        truth = score_candidate(env, case["target_action"])["semantic_rejection"]
        checks.append({"case": case["id"], "family": case["family"], "hand_space": fact.to_dict(),
                       "predict_rejected": predicted, "actual_rejected": truth})
    regression = []
    for path in sorted((Path(args.v2_runtime) / "runs").glob("*/steps/*/transition.json")):
        row = json.loads(path.read_text())
        if row.get("intercepted") and not row["proposed_truth"]["semantic_rejection"]:
            state = PublicState.observe(row["observation"])
            hand = state.features(row["proposed_action"]).get("hands.space", Evidence())
            regression.append({"task": path.parents[2].name, "index": row["index"], "action": row["proposed_action"],
                               "missing_hands": state.hands is None, "hand_space": hand.truth,
                               "spurious_same_missing_rejected": hand.truth != Truth.FALSE})
    tp = sum(c["predict_rejected"] is True and c["actual_rejected"] for c in checks)
    fp = sum(c["predict_rejected"] is True and not c["actual_rejected"] for c in checks)
    positives = sum(c["actual_rejected"] for c in checks)
    negatives = len(checks) - positives
    result = {"scope": "Historical regression audit of the hand-space feature only; not V3 generalization performance or a whole-model validity classifier.",
              "n": len(checks), "rejection_prediction_coverage": (tp + fp) / len(checks),
              "rejection_precision": tp / (tp + fp) if tp + fp else None,
              "rejection_recall_all_targets": tp / positives if positives else None,
              "false_block_rate_among_predictions": fp / (tp + fp) if tp + fp else None,
              "false_positive_rate_among_valid": fp / negatives if negatives else None,
              "unknown_predictions": sum(c["predict_rejected"] is None for c in checks),
              "old_false_blocks_checked": len(regression),
              "missing_field_regressions_passed": sum(c["spurious_same_missing_rejected"] for c in regression),
              "checks": checks, "regression_cases": regression}
    atomic_json(args.output, result)
    print(json.dumps({k: v for k, v in result.items() if k not in {"checks", "regression_cases"}}))


if __name__ == "__main__":
    main()
