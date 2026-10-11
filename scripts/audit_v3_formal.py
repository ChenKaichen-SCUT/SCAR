"""Audit real V3-cohort trajectories and export generated action records only."""
import argparse
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path

from scar.environment import restore, state_digest, AGENT_ID
from scar.io import atomic_json, read_jsonl
from scripts.v3_outcomes import disposition


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--runtime", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    runtime, output = Path(args.runtime), Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    costs, events, examples = Counter(), defaultdict(Counter), defaultdict(list)
    replay_checks, initial_checks, method_terminations = [], [], []
    pairing = defaultdict(dict)
    streams = {}
    try:
        for directory in sorted((runtime/"runs").iterdir()):
            if not (directory/"summary.json").exists():
                continue
            summary = json.loads((directory/"summary.json").read_text())
            if summary.get("stage") not in {"dev", "hard", "long"}:
                continue
            for request in read_jsonl(directory/"requests.jsonl"):
                costs["api_calls"] += 1
                costs["failed_requests"] += request["status"] != "ok"
                costs["cost_usd"] += request.get("cost_usd", 0)
                costs["conservative_cost_usd"] += request.get("charged_or_reserved_usd", 0)
                usage = request.get("usage") or {}
                for name in ["prompt_tokens", "completion_tokens", "prompt_cache_hit_tokens"]:
                    costs[name] += usage.get(name, 0)
            outcome = disposition(summary,directory)
            if outcome == "incomplete":
                continue
            if outcome != "completed":
                method_terminations.append({"task":directory.name,"steps":summary["steps"],"error":summary["error"],"disposition":outcome})
            initial = directory/"initial.pkl"
            source = summary.get("initial_snapshot") or runtime/"initials"/f"{summary['game']}-{summary['seed']}.pkl"
            initial_hash = state_digest(restore(initial))
            initial_checks.append({"task": directory.name, "matches_frozen_source": initial_hash == state_digest(restore(source))})
            cluster = summary["family"] if summary.get("diagnostic") else f"{summary['game']}-{summary['seed']}"
            pairing[(summary["stage"], cluster)][summary["algorithm"]] = initial_hash
            paths = sorted(directory.glob("steps/*/transition.json"))
            rows = [json.loads(path.read_text()) for path in paths]
            for index in sorted({0, len(rows)//2, len(rows)-1}) if rows else []:
                before = initial if index == 0 else paths[index-1].with_name("environment.pkl")
                trial = restore(before)
                obs, reward, done, _ = trial.step({AGENT_ID:rows[index]["executed_action"]})
                trial.update_scores(reward)
                exact = state_digest(trial) == state_digest(restore(paths[index].with_name("environment.pkl")))
                exact &= obs[AGENT_ID] == rows[index]["next_observation"] and reward[AGENT_ID].__dict__ == rows[index]["reward"] and bool(done) == rows[index]["done"]
                replay_checks.append({"task":directory.name, "index":index, "exact":exact})
            method = summary["algorithm"]
            if method not in streams:
                streams[method] = gzip.open(output/f"trajectories_{method}.jsonl.gz", "wt", encoding="utf-8")
            for row in rows:
                # Actual public observations/outputs and evaluator evidence, with
                # no HTTP headers, credentials, downloaded engine files or pickle.
                streams[method].write(json.dumps({"task": {k:v for k,v in summary.items() if k in {"task_id","stage","algorithm","game","seed","family"}}, "transition":row},ensure_ascii=False)+"\n")
                events[method].update(e["event"] for e in row.get("events", []))
                if row.get("proposed_truth") is not None:
                    legal = not row["proposed_truth"]["semantic_rejection"]
                    kind = "legal_to_rejected" if legal and row["semantic_rejection"] else "rejected_to_legal" if not legal and not row["semantic_rejection"] else "other"
                    key = method+":"+kind
                    if len(examples[key]) < 3:
                        examples[key].append({"task":directory.name, **row})
    finally:
        for stream in streams.values():
            stream.close()
    pair_checks = [{"stage":stage, "family_or_game":cluster, "algorithms":len(hashes), "equal_initial_states":len(set(hashes.values())) == 1} for (stage, cluster),hashes in pairing.items()]
    result = {"checked":len(replay_checks), "exact":sum(r["exact"] for r in replay_checks), "checks":replay_checks,
              "method_terminations":method_terminations,
              "initial_checks":initial_checks, "pair_checks":pair_checks,
              "failures":sum(not r["exact"] for r in replay_checks)+sum(not r["matches_frozen_source"] for r in initial_checks)+sum(not r["equal_initial_states"] for r in pair_checks)}
    atomic_json(output/"replay_audit.json",result)
    atomic_json(output/"request_accounting.json",dict(costs))
    atomic_json(output/"events_by_method.json",dict(events))
    atomic_json(output/"intervention_examples.json",dict(examples))
    print(json.dumps({"checked":result["checked"],"failures":result["failures"],"costs":dict(costs)}))
    if result["failures"]:
        raise SystemExit("Replay/initial-state audit failed; keep results and investigate")


if __name__ == "__main__":
    main()
