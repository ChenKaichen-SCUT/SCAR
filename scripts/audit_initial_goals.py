"""Check that frozen recovery goals are not satisfied before agents act."""
import argparse
import json
from pathlib import Path

from scar.environment import restore
from scar.diagnostics.build import goal_reached
from scar.diagnostics.scoring import score_candidate
from scar.io import atomic_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", required=True)
    parser.add_argument("--output", default="results/initial_goal_audit.json")
    args = parser.parse_args()
    checks = []
    for case in json.loads(Path(args.cases).read_text()):
        env = restore(case["initial_snapshot"])
        checks.append({"id": case["id"], "split": case["split"], "types": case["types"],
                       "initial_goal_already_reached": goal_reached(env, case["goal"]),
                       "target_semantic_rejection": score_candidate(env, case["target_action"])["semantic_rejection"]})
    result = {"checked": len(checks),
              "initial_goal_already_reached": sum(c["initial_goal_already_reached"] for c in checks),
              "checks": checks}
    atomic_json(args.output, result)
    print(json.dumps({k: v for k, v in result.items() if k != "checks"}))
    if result["initial_goal_already_reached"]:
        raise SystemExit("Invalid recovery starting states; inspect audit without changing frozen data silently")


if __name__ == "__main__":
    main()
