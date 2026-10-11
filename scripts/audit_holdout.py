"""Exclude any test action/state family already encountered in development.

Run before any diagnostic policies; saves the pre-audit manifest and exclusions.
"""
import argparse
import json
from pathlib import Path

from scar.io import atomic_json, digest
from scar.environment import AGENT_ID, restore
from scar.diagnostics.build import natural_statistics, physical_goal, all_actions, transition
from scar.agents.scar.state import action_key


def family(game, target, last_observation, goal):
    return digest([game, action_key(target), last_observation["text"].split("I am holding")[-1], goal])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--cases-dir", required=True)
    args = parser.parse_args()
    runtime, directory = Path(args.runtime), Path(args.cases_dir)
    manifest = directory / "cases.json"
    cases = json.loads(manifest.read_text())
    _, failures = natural_statistics(runtime)
    development = set()
    for failure in failures:
        if failure["task"].get("stage") != "pilot":
            continue
        env = restore(Path(failure["run"]) / "steps" / f"{failure['index'] + 1:04}" / "environment.pkl")
        action = failure["row"]["executed_action"]
        goal = physical_goal(env, action)
        if goal:
            development.add(family(failure["task"]["game"], action, failure["row"]["next_observation"], goal))
    for path in sorted((runtime / "initials").glob("*-7.pkl")):
        game = path.stem.rsplit("-", 1)[0]
        initial = restore(path)
        picks = [a for a in all_actions(initial) if a.startswith("pick up ")]
        for shift in range(min(len(picks), 6)):
            env = restore(path)
            for action in (picks[shift:] + picks[:shift])[:4]:
                event = transition(env, action)
                if event["semantic_rejection"]:
                    goal = physical_goal(env, action)
                    if goal:
                        development.add(family(game, action, event["after"], goal))
                    break
    excluded = [c for c in cases if c["split"] == "test" and c["family"] in development]
    kept = [c for c in cases if c not in excluded]
    original = directory / "cases_before_holdout_audit.json"
    if not original.exists():
        atomic_json(original, cases)
    atomic_json(manifest, kept)
    validation = json.loads((directory / "validation.json").read_text())
    validation.update(count=len(kept), frozen_sha256=digest(kept),
        type_counts={t: sum(t in c["types"] for c in kept) for t in "ABCD"},
        split_counts={s: sum(c["split"] == s for c in kept) for s in ("dev", "test")},
        holdout_audit={"development_families_checked": len(development),
                       "excluded_previously_seen_cases": [c["id"] for c in excluded],
                       "test_development_overlap_after_audit": 0})
    atomic_json(directory / "validation.json", validation)
    print(json.dumps(validation))


if __name__ == "__main__":
    main()
