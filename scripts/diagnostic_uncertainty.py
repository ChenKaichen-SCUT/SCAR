"""Exploratory sensitivity to correlation within each source collection episode."""
import argparse
from collections import defaultdict
import json
from pathlib import Path

from scar.experiments.analyze import paired_bootstrap, write_csv, stage_of
from scar.io import atomic_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--output", default="results")
    args = parser.parse_args()
    by_case = defaultdict(dict)
    for p in (Path(args.runtime) / "runs").glob("*/summary.json"):
        row = json.loads(p.read_text())
        if stage_of(row) == "diagnostic" and row["status"] == "completed":
            by_case[row["id"]][row["algorithm"]] = row
    rows = []
    for baseline in ["ShortTermMemoryAgent", "VanillaRAGAgent", "SimpleFailureRecovery"]:
        for metric in ["recovery_at_10", "recovery_at_20", "semantic_riar", "cost_usd", "api_calls"]:
            differences, clusters = [], []
            for case in by_case.values():
                if "SCARAgent" in case and baseline in case:
                    a, b = case["SCARAgent"], case[baseline]
                    if a.get(metric) is not None and b.get(metric) is not None:
                        differences.append(float(a[metric]) - float(b[metric]))
                        clusters.append((a["game"], a["seed"]))
            result = paired_bootstrap(differences, clusters)
            if result:
                rows.append({"baseline": baseline, "metric": metric, **result,
                             "analysis": "exploratory equal-weight source-trajectory clusters; not independent per-state inference"})
    write_csv(Path(args.output) / "diagnostic_trajectory_cluster_sensitivity.csv", rows)
    atomic_json(Path(args.output) / "diagnostic_trajectory_cluster_sensitivity.json", rows)


if __name__ == "__main__":
    main()
