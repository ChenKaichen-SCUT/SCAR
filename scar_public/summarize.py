"""Use upstream official score extraction; retain partial-run status explicitly."""
import argparse
import collections
import json
from pathlib import Path

from challenge_eval import extract_run_metrics
from scar_public.provider import usage_summary
from scar.io import atomic_json


def summarize(root):
    root = Path(root)
    groups = {}
    for current in sorted(root.glob("round*/*/*/current.json")):
        run = current.parent
        state = json.loads(current.read_text())
        manifest = json.loads((run / "manifest.json").read_text())
        official = extract_run_metrics(manifest["game"], str(run), None)
        traces = [json.loads(p.read_text()) for p in sorted((run/"trace").glob("*.json"))]
        actions = collections.Counter(r["action"] for r in traces)
        transitions = []
        previous = 0
        longest, ongoing = 0, 0
        for r in traces:
            score = r["scores"].get("quest", 0)
            if score > previous:
                transitions.append({"step": r["step"], "from": previous, "to": score, "action": r["action"]})
                longest = max(longest, ongoing)
                ongoing = 0
            else:
                ongoing += 1
            previous = score
        longest = max(longest, ongoing)
        group = groups.setdefault(manifest["method"], {"stage": manifest["stage"], "games": {}})
        group["games"][manifest["game"]] = {**official, "complete": state["complete"],
            "termination": state["termination"], "manifest": manifest, "usage": usage_summary(run/"api"),
            "quest_transitions": transitions, "longest_main_reward_plateau": longest,
            "top_actions": actions.most_common(10),
            "syntax_invalid_steps": sum(bool(r.get("info",{}).get("step_invalid_action",{}).get("agent_adam_davis"))
                                        for r in traces)}
    for method, group in groups.items():
        games = list(group["games"].values())
        complete = len(games) == 3 and all(g["complete"] for g in games)
        group["complete"] = complete
        group["main_mean"] = sum(g["main_quest"] for g in games)/3 if complete else None
        group["supplementary_mean"] = sum(g["supplementary_total"] for g in games)/3 if complete else None
        group["usage"] = usage_summary(root/group["stage"]/method)
    return {"groups": groups, "all_usage_including_probe": usage_summary(root),
            "initial_manifests": {p.parent.name:json.loads(p.read_text()) for p in (root/"initial").glob("*/manifest.json")}}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--root", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    result = summarize(args.root)
    atomic_json(args.out, result)
    for method, group in result["groups"].items():
        print(method, {g:(r["steps"],r["main_quest"],r["complete"]) for g,r in group["games"].items()},
              "mean",group["main_mean"],"peakUSD",round(group["usage"]["peak_usd_estimate"],4))
    print("TOTAL", result["all_usage_including_probe"])
