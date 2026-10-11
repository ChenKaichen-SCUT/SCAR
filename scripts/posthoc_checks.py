"""Explicitly supplementary checks of retry truth, FBR ratios and cache accounting."""
import argparse
from collections import defaultdict, Counter
import json
from pathlib import Path

import numpy as np

from scar.agents.scar.state import action_key
from scar.experiments.analyze import stage_of, SUCCESS, write_csv
from scar.io import atomic_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--output", default="results")
    args = parser.parse_args()
    runtime, output = Path(args.runtime), Path(args.output)
    retries, fbr_groups, accounting = [], defaultdict(list), defaultdict(Counter)
    for path in sorted((runtime / "runs").glob("*/summary.json")):
        s = json.loads(path.read_text())
        stage = stage_of(s)
        if stage not in {"long", "cost", "diagnostic"} or s["status"] not in SUCCESS:
            continue
        key = (stage, s["algorithm"])
        fbr_groups[key].append(s)
        with (path.parent / "requests.jsonl").open() as source:
            for line in source:
                request = json.loads(line)
                usage = request.get("usage") or {}
                for field in ["prompt_tokens", "completion_tokens", "prompt_cache_hit_tokens", "prompt_cache_miss_tokens"]:
                    accounting[key][field] += usage.get(field, 0)
                accounting[key]["requests"] += 1
                accounting[key]["cost_usd"] += request.get("cost_usd", 0)
        if stage == "diagnostic" and "B" in s["types"]:
            strict_step = None
            for p in sorted(path.parent.glob("steps/*/transition.json")):
                row = json.loads(p.read_text())
                if (action_key(row["executed_action"]) == action_key(s["target_action"])
                        and not row["semantic_rejection"] and row["diagnostic_goal_reached"]):
                    strict_step = row["index"] + 1
                    break
            retries.append({"id": s["id"], "family": s["family"], "algorithm": s["algorithm"],
                            "accepted_retry_step": s["successful_retry_steps"],
                            "goal_verified_retry_step": strict_step, "recovery_step": s["recovery_steps"]})
    ratios = []
    for (stage, method), summaries in sorted(fbr_groups.items()):
        groups = defaultdict(lambda: np.zeros(2))
        for s in summaries:
            group = s["family"] if stage == "diagnostic" else (s["game"], s["seed"])
            groups[group] += (s.get("false_blocks", 0), s.get("interceptions", 0))
        values = np.array(list(groups.values()))
        numerator, denominator = values.sum(axis=0)
        if not denominator:
            continue
        rng = np.random.default_rng(314159)
        draws = values[rng.integers(0, len(values), size=(10000, len(values)))].sum(axis=1)
        defined = draws[:, 1] > 0
        samples = draws[defined, 0] / draws[defined, 1]
        lo, hi = np.quantile(samples, [.025, .975])
        ratios.append({"stage": stage, "algorithm": method, "groups": len(groups),
                       "false_blocks": int(numerator), "interceptions": int(denominator),
                       "pooled_fbr": numerator / denominator, "ci95_low": lo, "ci95_high": hi,
                       "bootstrap_draws_without_interceptions": int((~defined).sum()),
                       "scope": "supplementary ratio bootstrap; diagnostic family / game-seed clusters"})
    atomic_json(output / "fbr_ratio_uncertainty.json", ratios)
    write_csv(output / "goal_verified_retries.csv", retries)
    grouped = defaultdict(list)
    for row in retries:
        grouped[row["algorithm"]].append(row)
    atomic_json(output / "goal_verified_retries.json", [
        {"algorithm": method, "n": len(rows),
         "accepted_retries": sum(r["accepted_retry_step"] is not None for r in rows),
         "goal_verified_retries": sum(r["goal_verified_retry_step"] is not None for r in rows)}
        for method, rows in sorted(grouped.items())])
    atomic_json(output / "cache_accounting_by_method.json", [
        {"stage": stage, "algorithm": method, **counts,
         "cache_hit_fraction": counts["prompt_cache_hit_tokens"] / counts["prompt_tokens"]}
        for (stage, method), counts in sorted(accounting.items())])
    print(json.dumps({"retry_cases": len(retries), "fbr_groups": len(ratios)}))


if __name__ == "__main__":
    main()
