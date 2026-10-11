"""Descriptive supplementary tables; does not change policy or scored outcomes."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import statistics

import numpy as np

from scar.experiments.analyze import SUCCESS, stage_of, write_csv
from scar.io import atomic_json, read_jsonl


def mean(values):
    return statistics.mean(values) if values else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--output", default="results")
    args = parser.parse_args()
    runtime, output = Path(args.runtime), Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    groups, stages = defaultdict(list), defaultdict(list)
    requests = defaultdict(list)
    interventions = defaultdict(Counter)
    examples = []
    for path in sorted((runtime / "runs").glob("*/summary.json")):
        row = json.loads(path.read_text())
        stage = stage_of(row)
        stages[stage].append(row)
        requests[stage].extend(read_jsonl(path.parent / "requests.jsonl"))
        if row["status"] not in SUCCESS:
            continue
        for game in ["ALL", row["game"]]:
            groups[(stage, game, row["algorithm"])].append(row)
        if stage not in {"long", "cost", "diagnostic"} or row["algorithm"] not in {"SCARAgent", "SimpleFailureRecovery"}:
            continue
        for p in sorted(path.parent.glob("steps/*/transition.json")):
            step = json.loads(p.read_text())
            if not step["intercepted"]:
                continue
            counts = interventions[(stage, row["algorithm"], step.get("reason", "unspecified"))]
            counts["changed_candidates"] += 1
            truth = step.get("proposed_truth")
            if truth is None:
                continue
            valid = not truth["semantic_rejection"]
            counts["valid_original_candidates"] += valid
            counts["valid_candidate_replaced_by_rejected_action"] += valid and step["semantic_rejection"]
            counts["invalid_candidate_replaced_by_accepted_action"] += not valid and not step["semantic_rejection"]
            # One deterministic illustration per stage/algorithm/category; not a frequency estimate.
            category = "valid_to_rejected" if valid and step["semantic_rejection"] else "other_interception"
            key = (stage, row["algorithm"], category)
            if not any((e["stage"], e["algorithm"], e["category"]) == key for e in examples):
                examples.append({"stage": stage, "algorithm": row["algorithm"], "category": category,
                                 "task_id": row["task_id"], "step": step["index"] + 1,
                                 "proposed_action": step["proposed_action"], "executed_action": step["executed_action"],
                                 "candidate_feedback": truth["feedback"],
                                 "executed_feedback": step["action_rule_feedback"],
                                 "reason": step.get("reason")})
    aggregates = []
    for (stage, game, algorithm), values in sorted(groups.items()):
        row = {"stage": stage, "game": game, "algorithm": algorithm, "n": len(values)}
        for metric in ["steps", "main_quest_reward", "input_tokens", "output_tokens", "api_calls", "cost_usd",
                       "wall_seconds_this_attempt", "decision_wall_seconds", "steps_to_first_milestone"]:
            numbers = [v[metric] for v in values if v.get(metric) is not None]
            row[metric + "_n"] = len(numbers)
            row[metric + "_mean"] = mean(numbers)
            row[metric + "_median"] = statistics.median(numbers) if numbers else None
        row["interceptions"] = sum(v.get("interceptions", 0) for v in values)
        row["false_blocks"] = sum(v.get("false_blocks", 0) for v in values)
        row["pooled_fbr"] = row["false_blocks"] / row["interceptions"] if row["interceptions"] else None
        row["completed_budget"] = sum(v["status"] == "completed_budget" for v in values)
        row["game_completions"] = sum(v["completion"] for v in values)
        aggregates.append(row)
    write_csv(output / "supplementary_aggregate.csv", aggregates)
    atomic_json(output / "supplementary_aggregate.json", aggregates)
    accounting = []
    for stage, values in sorted(stages.items()):
        req = requests[stage]
        latency = [r["latency_seconds"] for r in req]
        accounting.append({"stage": stage, "runs": len(values), "statuses": dict(Counter(v["status"] for v in values)),
            "actions": sum(v["steps"] for v in values), "calls": len(req),
            "failed_requests": sum(r["status"] != "ok" for r in req),
            "http_429": sum(r.get("http_status") == 429 for r in req),
            "cost_usd": sum(r.get("cost_usd", 0) for r in req),
            "conservative_cost_usd": sum(r.get("charged_or_reserved_usd", 0) for r in req),
            "request_latency_median": statistics.median(latency) if latency else None,
            "request_latency_p95": float(np.quantile(latency, .95)) if latency else None,
            "first_request": min((r["start"] for r in req), default=None),
            "last_response": max((r["end"] for r in req), default=None)})
    atomic_json(output / "stage_accounting.json", accounting)
    write_csv(output / "intervention_outcomes.csv", [dict(stage=k[0], algorithm=k[1], reason=k[2], **v)
                                                    for k, v in sorted(interventions.items())])
    atomic_json(output / "intervention_examples.json", examples)
    monitors = read_jsonl(runtime / "monitor.jsonl")
    if monitors:
        atomic_json(output / "resource_monitor_summary.json", {
            "samples": len(monitors), "max_target_workers": max(m["target"] for m in monitors),
            "min_available_memory_bytes": min(m["memory_available"] for m in monitors),
            "min_free_disk_bytes": min(m["disk_free"] for m in monitors),
            "median_sampled_cpu_percent": statistics.median(m["cpu_percent"] for m in monitors),
            "max_sampled_cpu_percent": max(m["cpu_percent"] for m in monitors),
            "scope": "All stages; irregular completion/15-second samples, not a time-weighted CPU mean."})
    cases_path = runtime / "ao_fr_frozen" / "cases.json"
    if cases_path.exists():
        cases = json.loads(cases_path.read_text())
        provenance = [{**{k: c.get(k) for k in ["id", "family", "split", "game", "seed", "types", "parent_case_id",
                                                  "target_action", "state_hash", "search_nodes", "validated"]},
                       "origin": "engine_condition_release_variant" if c.get("parent_case_id") else "natural_failure_snapshot"}
                      for c in cases]
        atomic_json(output / "dataset_provenance.json", provenance)
        paired = defaultdict(dict)
        for row in stages.get("diagnostic", []):
            if row["status"] == "completed":
                paired[row["id"]][row["algorithm"]] = row
        selected = {}
        for case in sorted(cases, key=lambda c: c["id"]):
            pair = paired.get(case["id"], {})
            if "SCARAgent" not in pair or "SimpleFailureRecovery" not in pair:
                continue
            scar_ok = pair["SCARAgent"]["recovery_at_20"]
            simple_ok = pair["SimpleFailureRecovery"]["recovery_at_20"]
            label = ("scar_only" if scar_ok else "simple_only") if scar_ok != simple_ok else ("both_recover" if scar_ok else "neither_recovers")
            if label in selected:
                continue
            example = {"case": case["id"], "game": case["game"], "types": case["types"],
                       "target_action": case["target_action"], "goal": case["goal"],
                       "verified_witness": case["witness"], "selection": "lexicographically first case in this outcome category",
                       "methods": {}}
            for method in ["SCARAgent", "SimpleFailureRecovery"]:
                summary = pair[method]
                trace = []
                for p in sorted((runtime / "runs" / summary["task_id"]).glob("steps/*/transition.json")):
                    step = json.loads(p.read_text())
                    trace.append({k: step.get(k) for k in ["index", "proposed_action", "executed_action", "reason",
                                  "semantic_rejection", "action_rule_feedback", "diagnostic_goal_reached"]})
                example["methods"][method] = {"task_id": summary["task_id"], "recovery_steps": summary["recovery_steps"], "trace": trace}
            selected[label] = example
        atomic_json(output / "paired_case_examples.json", selected)
    print(json.dumps({"groups": len(aggregates), "stages": len(accounting), "illustrations": len(examples)}))


if __name__ == "__main__":
    main()
