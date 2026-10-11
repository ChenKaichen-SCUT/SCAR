"""Freeze development-learned rules; evaluate on independent diagnostic states."""
import argparse
import json
from pathlib import Path

from scar.agents.scar.memory import FailureMemory
from scar.agents.scar.state import VisibleState
from scar.environment import AGENT_ID, restore
from scar.diagnostics.scoring import score_candidate
from scar.io import atomic_json, digest


def evaluate(runtime, cases_path, output):
    runtime = Path(runtime)
    cases = json.loads(Path(cases_path).read_text())
    memories = {}
    for run in sorted((runtime / "runs").glob("pilot-SCARAgent-*")):
        task_path = run / "task.json"
        if not task_path.exists():
            continue
        task = json.loads(task_path.read_text())["task"]
        paths = sorted(run.glob("steps/*/memory/scar.json"))
        if paths:
            memory_dict = json.loads(paths[-1].read_text())["failure_memory"]
            memories[task["game"]] = memory_dict
    predictions = []
    for case in cases:
        if case["split"] != "test" or case["game"] not in memories:
            continue
        env = restore(case["initial_snapshot"])
        memory = FailureMemory.from_dict(memories[case["game"]])
        state = None
        for event in case["history"]:
            state = VisibleState.observe(event["before"], state)
            state = VisibleState.observe(event["after"], state)
        state = VisibleState.observe(env.obs[AGENT_ID], state)
        for rule in memory.rules:
            if rule.status == "contradicted":
                continue
            predicted = memory.matches(rule, state) and rule.confidence >= memory.threshold
            truth = score_candidate(env, rule.action)["semantic_rejection"]
            predictions.append({"case": case["id"], "family": case["family"], "game": case["game"],
                                "rule": rule.id, "action": rule.action, "predict_invalid": predicted,
                                "actual_invalid": truth, "correct": predicted == truth})
    atomic_json(output, {"frozen_development_rule_hash": digest(memories), "test_cases_hash": digest(cases),
                "n": len(predictions), "cra": sum(p["correct"] for p in predictions) / len(predictions) if predictions else None,
                "blocking_predictions": sum(p["predict_invalid"] for p in predictions),
                "actual_invalid": sum(p["actual_invalid"] for p in predictions),
                "families": len({p["family"] for p in predictions}),
                "predictions": predictions,
                "scope": "Rules learned only in development-seed pilot. No updates on test states; no-match treated as allow. Correlated rules/states are not independent samples."})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--cases", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    evaluate(args.runtime, args.cases, args.output)
