"""Read-only post-run audits and application of a results-bound scientific review."""
import argparse
from collections import Counter
import json
from pathlib import Path

from scar.io import atomic_json, digest


def review(runtime, output, report):
    runtime, output, report = Path(runtime), Path(output), Path(report)
    reasons, triggers, violations, false_blocks = Counter(), Counter(), [], []
    for path in sorted((runtime / "runs").glob("*/steps/*/transition.json")):
        row = json.loads(path.read_text())
        reasons[row["reason"]] += 1
        triggers[str(row["repair_trigger"])] += 1
        if row["intercepted"] and row["candidate_syntax_valid"] and row["candidate_assessment"] != "block":
            violations.append(str(path.relative_to(runtime)))
        if row["intercepted"] and not row["proposed_truth"]["semantic_rejection"]:
            memory = json.loads((path.parent / "memory/scar.json").read_text())
            hits = [e["rule"] for e in row["events"] if e["event"] == "memory_hit" and e["action"] == row["proposed_action"]]
            rules = [r for r in memory["failure_memory"]["rules"] if r["id"] in hits]
            false_blocks.append({"task": path.parents[2].name, "index": row["index"],
                                 "proposed": row["proposed_action"], "executed": row["executed_action"],
                                 "reason": row["reason"], "rule_conditions": [r["conditions"] for r in rules],
                                 "candidate_truth": row["proposed_truth"], "executed_rejected": row["semantic_rejection"]})
    atomic_json(output / "gating_audit.json", {
        "decisions": sum(reasons.values()), "reasons": dict(reasons), "repair_triggers": dict(triggers),
        "unblocked_valid_candidate_override_violations": violations, "false_block_cases": false_blocks})
    current = json.loads((output / "all_summaries.json").read_text())
    archived = json.loads((output / "archived_comparators.json").read_text())
    prior = {r["id"]: r for r in archived if r.get("diagnostic") and r["algorithm"] == "SCARAgent"}
    discordant = []
    for row in current:
        if row.get("diagnostic") and row["recovery_at_20"] != prior[row["id"]]["recovery_at_20"]:
            discordant.append({**{k: row[k] for k in ["id", "game", "family", "types", "target_action", "recovery_at_20", "recovery_steps"]},
                               "v1_recovery_at_20": prior[row["id"]]["recovery_at_20"],
                               "v1_recovery_steps": prior[row["id"]]["recovery_steps"]})
    atomic_json(output / "recovery_discordant_pairs.json", discordant)
    # A reviewed conclusion must never be silently carried to a different result set.
    decision_path = output / "scientific_review.json"
    if decision_path.exists():
        decision = json.loads(decision_path.read_text())
        assert digest(current) == decision["results_sha256"]
        assert digest(archived) == decision["comparators_sha256"]
        assert not violations
        text = report.read_text()
        marker = "## 研究判断"
        assert marker in text
        report.write_text(text.split(marker)[0] + marker + "\n\n" + decision["review_markdown"].rstrip() + "\n")
    print(json.dumps({"decisions": sum(reasons.values()), "gating_violations": len(violations),
                      "false_blocks": len(false_blocks), "discordant_pairs": len(discordant)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--output", default="results/v2")
    parser.add_argument("--report", default="reports/修订版实验报告.md")
    args = parser.parse_args()
    review(args.runtime, args.output, args.report)
