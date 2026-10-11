"""Post-run accounting, diagnostic strata and exact committed-step replay audit."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import statistics

from scar.io import atomic_json, read_jsonl
from scar.environment import AGENT_ID, restore, state_digest
from scar.experiments.analyze import write_csv


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--output", default="results")
    args = parser.parse_args()
    runtime, output = Path(args.runtime), Path(args.output)
    output.mkdir(exist_ok=True, parents=True)
    requests = Counter()
    event_counts = defaultdict(Counter)
    diagnostic_groups = defaultdict(list)
    replays = []
    initial_checks = []
    runs = sorted((runtime / "runs").iterdir())
    for run in runs:
        summary_path = run / "summary.json"
        if not summary_path.exists():
            continue
        summary = json.loads(summary_path.read_text())
        stage = "diagnostic" if summary.get("diagnostic") else summary.get("stage")
        for request in read_jsonl(run / "requests.jsonl"):
            requests["calls"] += 1
            requests["failures"] += request["status"] != "ok"
            requests["http_429"] += request.get("http_status") == 429
            usage = request.get("usage") or {}
            requests["input_tokens"] += usage.get("prompt_tokens", 0)
            requests["output_tokens"] += usage.get("completion_tokens", 0)
            requests["cache_hit_tokens"] += usage.get("prompt_cache_hit_tokens", 0)
            requests["cost_usd"] += request.get("cost_usd", 0)
            requests["conservative_cost_usd"] += request.get("charged_or_reserved_usd", 0)
        paths = sorted(run.glob("steps/*/checkpoint.json"))
        rows = [json.loads(path.with_name("transition.json").read_text()) for path in paths]
        for row in rows:
            for event in row.get("events", []):
                event_counts[(stage, summary["game"], summary["algorithm"])][event["event"]] += 1
        if stage == "diagnostic" and summary["status"] == "completed":
            for label in ["ALL"] + summary["types"]:
                diagnostic_groups[(label, summary["algorithm"])].append(summary)
        if stage in {"long", "diagnostic", "cost", "collect"} and rows:
            source = (Path(summary["initial_snapshot"]) if stage == "diagnostic" else
                      runtime / "initials" / f"{summary['game']}-{summary['seed']}.pkl")
            initial_checks.append({"task": run.name,
                "equal_to_frozen_source": state_digest(restore(run / "initial.pkl")) == state_digest(restore(source))})
            for index in sorted({0, len(rows) // 2, len(rows) - 1}):
                before_path = run / "initial.pkl" if index == 0 else paths[index - 1].with_name("environment.pkl")
                try:
                    trial = restore(before_path)
                    action = rows[index]["executed_action"]
                    observed, reward, done, info = trial.step({AGENT_ID: action})
                    trial.update_scores(reward)
                    actual = restore(paths[index].with_name("environment.pkl"))
                    same = state_digest(trial) == state_digest(actual)
                    same = same and observed[AGENT_ID] == rows[index]["next_observation"]
                    same = same and reward[AGENT_ID].__dict__ == rows[index]["reward"]
                    replays.append({"task": run.name, "index": index, "exact": same})
                except Exception as exc:
                    replays.append({"task": run.name, "index": index, "exact": False,
                                    "error": type(exc).__name__})
    probe = read_jsonl(runtime / "api_probe.jsonl")
    atomic_json(output / "request_accounting.json", {**requests,
                "probe_calls": len(probe), "probe_cost_usd": sum(p.get("cost_usd", 0) for p in probe)})
    atomic_json(output / "replay_audit.json", {"checked": len(replays), "exact": sum(x["exact"] for x in replays),
                "failed": sum(not x["exact"] for x in replays), "checks": replays,
                "initial_states_checked": len(initial_checks),
                "initial_state_mismatches": sum(not c["equal_to_frozen_source"] for c in initial_checks),
                "initial_checks": initial_checks})
    write_csv(output / "scar_module_events.csv", [dict(stage=stage, game=game, algorithm=algorithm, **count)
               for (stage, game, algorithm), count in event_counts.items()])
    strata = []
    for (label, algorithm), values in sorted(diagnostic_groups.items()):
        row = {"type": label, "algorithm": algorithm, "n": len(values),
               "families": len({v["family"] for v in values})}
        for metric in ["recovery_at_10", "recovery_at_20", "recovery_steps", "alternative_recovery",
                       "semantic_riar", "fbr", "cost_usd", "api_calls", "successful_retry_steps"]:
            numbers = [v[metric] for v in values if v.get(metric) is not None]
            row[metric] = statistics.mean(numbers) if numbers else None
        row["correct_retry_rate"] = sum(v.get("successful_retry_steps") is not None for v in values) / len(values)
        strata.append(row)
    write_csv(output / "diagnostic_by_type.csv", strata)
    print(json.dumps({"requests": dict(requests), "replays_checked": len(replays),
                      "replay_failures": sum(not r["exact"] for r in replays)}))


if __name__ == "__main__":
    main()
