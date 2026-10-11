"""All-run tables and paired uncertainty; incomplete runs remain visible."""
import argparse
from collections import defaultdict
import csv
import json
from pathlib import Path
import statistics

import numpy as np

from scar.io import atomic_json


SUCCESS = {"completed", "completed_budget"}
METRICS = ["main_quest_reward", "completion", "iar", "semantic_failure_rate", "riar", "semantic_riar",
           "fbr", "cra", "recovery_at_10", "recovery_at_20", "recovery_steps", "alternative_recovery",
           "successful_retry_steps", "input_tokens", "output_tokens", "api_calls", "cost_usd",
           "decision_wall_seconds", "steps"]


def stage_of(row):
    if row.get("diagnostic"):
        return "diagnostic" if row.get("protocol_cohort") == "formal_hash0" else "diagnostic_provisional"
    return row.get("stage", "unknown")


def write_csv(path, rows):
    if not rows:
        Path(path).write_text("")
        return
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with Path(path).open("w") as out:
        writer = csv.DictWriter(out, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def paired_bootstrap(values, groups=None, seed=314159, n=10000):
    values = np.asarray(values, dtype=float)
    if not len(values):
        return None
    rng = np.random.default_rng(seed)
    if groups is None:
        groups = list(range(len(values)))
    indices = defaultdict(list)
    for i, group in enumerate(groups):
        indices[group].append(i)
    clusters = list(indices.values())
    # Equal family weight prevents paired state-release variants inflating evidence.
    cluster_means = np.asarray([values[index].mean() for index in clusters])
    draws = rng.choice(cluster_means, size=(n, len(clusters)), replace=True).mean(axis=1)
    return {"pairs": len(values), "independent_groups": len(clusters), "mean_difference": float(cluster_means.mean()),
            "median_difference": float(np.median(values)), "ci95_low": float(np.quantile(draws, .025)),
            "ci95_high": float(np.quantile(draws, .975)), "small_sample": len(clusters) < 20}


def analyze(runtime, output):
    runtime, output = Path(runtime), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    summaries = [json.loads(p.read_text()) for p in sorted((runtime / "runs").glob("*/summary.json"))]
    simple = [{k: v for k, v in row.items() if not isinstance(v, (dict, list))} for row in summaries]
    write_csv(output / "all_runs.csv", simple)
    atomic_json(output / "all_summaries.json", [{k: v for k, v in row.items()
                 if k not in {"history", "witness", "initial_snapshot", "goal"}} for row in summaries])
    groups = defaultdict(list)
    for row in summaries:
        stage = stage_of(row)
        for game in [row["game"], "ALL"]:
            groups[(stage, game, row["algorithm"])].append(row)
    aggregate = []
    for (stage, game, algorithm), rows in sorted(groups.items()):
        valid = [r for r in rows if r["status"] in SUCCESS]
        out = {"stage": stage, "game": game, "algorithm": algorithm,
               "runs_total": len(rows), "runs_complete": len(valid), "runs_incomplete": len(rows) - len(valid)}
        for metric in METRICS:
            values = [float(r[metric]) for r in valid if r.get(metric) is not None]
            out[metric + "_n"] = len(values)
            out[metric + "_mean"] = statistics.mean(values) if values else None
            out[metric + "_median"] = statistics.median(values) if values else None
        aggregate.append(out)
    write_csv(output / "aggregate.csv", aggregate)
    atomic_json(output / "aggregate.json", aggregate)
    pairs = []
    for stage in ["long", "cost", "diagnostic"]:
        valid = [r for r in summaries if r["status"] in SUCCESS and
                 stage_of(r) == stage]
        by_key = defaultdict(dict)
        for row in valid:
            key = row.get("id") if stage == "diagnostic" else (row["game"], row["seed"])
            by_key[key][row["algorithm"]] = row
        baselines = sorted({r["algorithm"] for r in valid} - {"SCARAgent"})
        for baseline in baselines:
            for game in ["ALL", "remnant", "mark", "metropolis"]:
                matches = [(rows["SCARAgent"], rows[baseline]) for rows in by_key.values()
                           if "SCARAgent" in rows and baseline in rows and
                           (game == "ALL" or rows["SCARAgent"]["game"] == game)]
                for metric in METRICS:
                    measured = [(a, b) for a, b in matches if a.get(metric) is not None and b.get(metric) is not None]
                    differences = [float(a[metric]) - float(b[metric]) for a, b in measured]
                    labels = [a.get("family", (a["game"], a["seed"])) for a, b in measured]
                    result = paired_bootstrap(differences, labels)
                    if result:
                        pairs.append({"stage": stage, "game": game, "comparison": "SCARAgent - " + baseline,
                                      "metric": metric, **result})
    write_csv(output / "paired_comparisons.csv", pairs)
    atomic_json(output / "paired_comparisons.json", pairs)
    failures = [r for r in simple if r["status"] not in SUCCESS]
    write_csv(output / "incomplete_runs.csv", failures)
    # Cost includes pilot failures, API probe, retries and attempts without committed actions.
    from scar.providers.deepseek import BudgetLedger
    ledger = BudgetLedger(runtime / "budget.sqlite", 20)
    atomic_json(output / "audit_overview.json", {
        "total_runs": len(summaries), "completed_runs": sum(r["status"] in SUCCESS for r in summaries),
        "incomplete_runs": len(failures), "global_conservative_cost_usd": ledger.total(),
        "recorded_request_cost_usd": sum(r.get("cost_usd", 0) for r in summaries),
        "api_calls": sum(r.get("api_calls", 0) for r in summaries),
        "failed_requests": sum(r.get("failed_requests", 0) for r in summaries),
        "notes": ["Peak pricing gives a reproducible conservative comparison, not account debit.",
                  "Online CRA audit is exploratory; frozen independent-rule accuracy is not substituted.",
                  "All unfinished runs are listed; complete-case paired comparisons may be biased if missingness is unequal."]})
    print(json.dumps({"runs": len(summaries), "paired_comparisons": len(pairs), "cost": ledger.total()}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--output", default="results")
    args = parser.parse_args()
    analyze(args.runtime, args.output)
