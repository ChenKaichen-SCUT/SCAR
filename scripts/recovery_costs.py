"""Exact token/request cost until the first scored recovery, or the 20-step cap."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import statistics

from scar.experiments.analyze import stage_of, write_csv, paired_bootstrap
from scar.io import atomic_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--output", default="results")
    args = parser.parse_args()
    rows = []
    for path in sorted((Path(args.runtime) / "runs").glob("*/summary.json")):
        summary = json.loads(path.read_text())
        if stage_of(summary) != "diagnostic" or summary["status"] != "completed":
            continue
        trace = [json.loads(p.read_text()) for p in sorted(path.parent.glob("steps/*/transition.json"))]
        steps = summary["recovery_steps"] or len(trace)
        prefix = trace[:steps]
        row = {"task_id": summary["task_id"], "id": summary["id"], "family": summary["family"],
               "algorithm": summary["algorithm"], "game": summary["game"], "seed": summary["seed"],
               "recovered": summary["recovery_steps"] is not None, "steps_until_recovery_or_cap": steps}
        for key in ["input_tokens", "output_tokens", "api_calls", "cost_usd", "conservative_cost_usd"]:
            row[key] = sum(r["api_delta"][key] for r in prefix)
        rows.append(row)
    write_csv(Path(args.output) / "recovery_cost_per_case.csv", rows)
    groups = defaultdict(list)
    for row in rows:
        groups[row["algorithm"]].append(row)
    aggregate = []
    for method, values in sorted(groups.items()):
        entry = {"algorithm": method, "cases": len(values), "recovered": sum(r["recovered"] for r in values)}
        for key in ["steps_until_recovery_or_cap", "input_tokens", "output_tokens", "api_calls", "cost_usd"]:
            entry[key + "_mean"] = statistics.mean(v[key] for v in values)
            entry[key + "_median"] = statistics.median(v[key] for v in values)
        successful = [v["steps_until_recovery_or_cap"] for v in values if v["recovered"]]
        entry["recovery_steps_success_only_mean"] = statistics.mean(successful) if successful else None
        entry["recovery_steps_success_only_median"] = statistics.median(successful) if successful else None
        aggregate.append(entry)
    write_csv(Path(args.output) / "recovery_cost_by_algorithm.csv", aggregate)
    atomic_json(Path(args.output) / "recovery_cost_by_algorithm.json", aggregate)


if __name__ == "__main__":
    main()
