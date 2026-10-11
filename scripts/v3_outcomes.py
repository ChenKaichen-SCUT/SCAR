"""Classify observed policy termination without rewriting frozen run records.

An exhausted action-format repair is an observed method failure, not missing
experimental data. Infrastructure errors remain incomplete. No retries, fictitious
steps, successful outcomes or changes to the frozen agent are introduced here.
"""
from pathlib import Path
import json

FORMAT_FAILURES = {
    "ModelResponseError: No public-signature-valid action after bounded V3 format repair",
    "ModelResponseError: No syntactically valid action after bounded repair; no game action executed",
    "ModelResponseError: Final action failed public signature validation",
}


def disposition(summary, directory):
    if summary["status"] == "completed":
        return "completed"
    if summary["status"] != "failed" or summary.get("error") not in FORMAT_FAILURES:
        return "incomplete"
    path = Path(directory)/"requests.jsonl"
    if not path.exists():
        return "incomplete"
    requests = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    # Both the base proposal and bounded repair reached the API successfully.
    # Timeouts, auth/rate errors, missing outputs and unknown crashes do not qualify.
    if len(requests) < 2 or any(r.get("status") != "ok" for r in requests[-2:]):
        return "incomplete"
    return "method_terminated_format_failure"


def stage_evaluation(runtime, stage):
    runtime = Path(runtime)
    plan = runtime/f"plan_{stage}.json"
    if not plan.exists():
        return {"fully_evaluated":False, "method_terminations":0, "normal_completions":0}
    tasks = json.loads(plan.read_text())["tasks"]
    outcomes = []
    for task in tasks:
        directory = runtime/"runs"/task["task_id"]
        path = directory/"summary.json"
        if not path.exists():
            outcomes.append("incomplete")
        else:
            outcomes.append(disposition(json.loads(path.read_text()),directory))
    return {"expected":len(tasks), "fully_evaluated":bool(tasks) and "incomplete" not in outcomes,
            "method_terminations":outcomes.count("method_terminated_format_failure"),
            "normal_completions":outcomes.count("completed"), "incomplete":outcomes.count("incomplete")}
