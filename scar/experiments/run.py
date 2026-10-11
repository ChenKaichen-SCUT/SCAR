"""Resumable isolated episodes, process scheduling and resource/audit monitoring."""
import argparse
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
import contextlib
import copy
import json
import multiprocessing as mp
import os
from pathlib import Path
import random
import time
import traceback

for _key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "TOKENIZERS_PARALLELISM"):
    os.environ[_key] = "false" if _key == "TOKENIZERS_PARALLELISM" else "1"

import psutil

from scar.io import atomic_json, append_jsonl, read_jsonl, digest
from scar.providers.deepseek import DeepSeekProvider, BudgetLedger, BudgetExceeded, EpisodeBudgetExceeded
from scar.environment import AGENT_ID, create_environment, save_snapshot, restore, state_digest
from scar.agents.scar.state import VisibleState
from scar.diagnostics.scoring import outcome, score_candidate, aggregate_trajectory, recovery_score


def prepare_initials(config, root, seeds):
    root = Path(root)
    for game in config["games"]:
        for seed in seeds:
            path = root / "initials" / f"{game}-{seed}.pkl"
            if path.exists():
                continue
            env, obs = create_environment(game, seed, root / "initials" / f"{game}-{seed}")
            sha = save_snapshot(path, env)
            atomic_json(path.with_suffix(".json"), {"game": game, "seed": seed, "sha256": sha,
                                                  "state_digest": state_digest(env)})


def audit_totals(path):
    rows = read_jsonl(path)
    return {"input_tokens": sum((r.get("usage") or {}).get("prompt_tokens", 0) for r in rows),
            "output_tokens": sum((r.get("usage") or {}).get("completion_tokens", 0) for r in rows),
            "api_calls": len(rows), "failed_requests": sum(r["status"] != "ok" for r in rows),
            "cost_usd": sum(r.get("cost_usd", 0) for r in rows),
            "conservative_cost_usd": sum(r.get("charged_or_reserved_usd", 0) for r in rows),
            "api_latency_seconds": sum(r["latency_seconds"] for r in rows),
            "http_429": sum(r.get("http_status") == 429 for r in rows)}


def episode(task, config, runtime, key_path, workers):
    task_id = task["task_id"]
    run_dir = Path(runtime) / "runs" / task_id
    run_dir.mkdir(parents=True, exist_ok=True)
    status_path = run_dir / "status.json"
    if status_path.exists() and json.loads(status_path.read_text()).get("status") in {"completed", "completed_budget"}:
        return json.loads((run_dir / "summary.json").read_text())
    started = time.time()
    config = dict(config, seed=task["seed"])
    atomic_json(run_dir / "task.json", {"task": task, "config": config})
    atomic_json(status_path, {"status": "running", "started": started, "pid": os.getpid()})
    rows, env, agent, visible = [], None, None, None
    # Capture upstream verbose logs per task; no shared file handles between workers.
    with (run_dir / "engine.log").open("a") as engine_log, contextlib.redirect_stdout(engine_log), contextlib.redirect_stderr(engine_log):
        try:
            from scar.integration import make_agent
            provider = DeepSeekProvider(config, run_dir / "requests.jsonl", Path(runtime) / "budget.sqlite", key_path, workers)
            agent = make_agent(task["algorithm"], task["game"], provider, config, run_dir / "memory")
            checkpoints = sorted((run_dir / "steps").glob("*/checkpoint.json"))
            if checkpoints:
                last = checkpoints[-1].parent
                env = restore(last / "environment.pkl", run_dir, agent)
                agent.load_memory(last / "memory")
                meta = json.loads((last / "checkpoint.json").read_text())
                visible = VisibleState(**meta["visible_state"])
                rows = [json.loads(p.with_name("transition.json").read_text()) for p in checkpoints]
            else:
                initial = task.get("initial_snapshot") or str(Path(runtime) / "initials" / f"{task['game']}-{task['seed']}.pkl")
                env = restore(initial, run_dir, agent)
                # Every algorithm receives the identical observed history.
                for transition in task.get("history", []):
                    agent.memorize(f"{transition['before']['text']}\nAction: {transition['action']}\n{transition['after']['text']}")
                    if hasattr(agent, "observe_transition"):
                        agent.observe_transition(transition["before"], transition["action"], transition["after"])
                if task.get("diagnostic"):
                    agent.memorize(f"Recovery objective: resume the subgoal previously attempted by {task['target_action']}. "
                                   "Use observed evidence to remove blockers or achieve the same goal by another route.")
                visible = VisibleState.observe(env.obs[AGENT_ID])
                save_snapshot(run_dir / "initial.pkl", env)
            done = bool(rows and rows[-1]["done"])
            for index in range(len(rows), task["max_steps"]):
                if done:
                    break
                obs = copy.deepcopy(env.obs)
                before = VisibleState.observe(obs[AGENT_ID], visible)
                totals_before = audit_totals(run_dir / "requests.jsonl")
                tick = time.monotonic()
                action, _, _, response = agent.act({"step": obs[AGENT_ID]["step"], "text": obs[AGENT_ID]["text"]})
                decision = getattr(agent, "decision", {}) or {"proposed_action": action, "executed_action": action,
                                                              "intercepted": False, "all_proposals": [action], "rule_predictions": []}
                decision = copy.deepcopy(decision)
                # This truth is computed after policy selection and never returned to it.
                proposed_truth = score_candidate(env, decision["proposed_action"]) if decision["intercepted"] else None
                rule_tests = []
                # Predeclared sparse audit to bound CPU/storage overhead, not cherry-picking.
                if index % 10 == 0:
                    for prediction in decision.get("rule_predictions", [])[:10]:
                        truth = score_candidate(env, prediction["action"])
                        rule_tests.append(dict(prediction, semantic_rejection=truth["semantic_rejection"]))
                executed_truth = score_candidate(env, action)
                after, reward, done, info = env.step({AGENT_ID: action})
                env.update_scores(reward)
                evaluation = outcome(after, info)
                evaluation["semantic_rejection"] = executed_truth["semantic_rejection"]
                evaluation["action_rule_feedback"] = executed_truth["feedback"]
                evaluation["action_rule_events"] = executed_truth["events"]
                if hasattr(agent, "observe_transition"):
                    agent.observe_transition(obs[AGENT_ID], action, after[AGENT_ID])
                visible = VisibleState.observe(after[AGENT_ID], before)
                totals_after = audit_totals(run_dir / "requests.jsonl")
                row = {"index": index, "engine_step": env.steps, "observation": obs[AGENT_ID],
                       "next_observation": copy.deepcopy(after[AGENT_ID]), **decision, **evaluation,
                       "reward": copy.deepcopy(reward[AGENT_ID].__dict__), "done": bool(done),
                       "visible_state_hash": before.fingerprint, "visible_fields": before.fields,
                       "proposed_truth": proposed_truth, "rule_tests": rule_tests,
                       "response": response, "elapsed_seconds": time.monotonic() - tick,
                       "cost_cumulative": totals_after["cost_usd"],
                       "api_delta": {k: totals_after[k] - totals_before[k] for k in totals_after},
                       "events": list(getattr(agent, "events", []))}
                if task.get("diagnostic"):
                    from scar.diagnostics.build import goal_reached
                    row["diagnostic_goal_reached"] = goal_reached(env, task["goal"])
                if hasattr(agent, "events"):
                    agent.events.clear()
                append_jsonl(run_dir / "attempt_transitions.jsonl", row)
                checkpoint = run_dir / "steps" / f"{index + 1:04}"
                if (checkpoint / "checkpoint.json").exists():
                    raise RuntimeError("Refusing to overwrite committed transition")
                checkpoint.mkdir(parents=True, exist_ok=True)
                (checkpoint / "memory").mkdir(parents=True, exist_ok=True)
                agent.save_memory(checkpoint / "memory")
                save_snapshot(checkpoint / "environment.pkl", env)
                atomic_json(checkpoint / "transition.json", row)
                # Commit marker is last. Incomplete directories are safely rebuilt on resume.
                atomic_json(checkpoint / "checkpoint.json", {"visible_state": visible.__dict__, "index": index})
                rows.append(row)
                atomic_json(status_path, {"status": "running", "steps": len(rows), "updated": time.time(), **totals_after})
            status, error = "completed", None
        except EpisodeBudgetExceeded as exc:
            status, error = "completed_budget", str(exc)
        except BudgetExceeded as exc:
            status, error = "budget_stopped", str(exc)
        except Exception as exc:
            status, error = "failed", f"{type(exc).__name__}: {exc}"
            # Provider exceptions sanitize credentials. Game tracebacks contain no key.
            (run_dir / "error.txt").write_text(traceback.format_exc())
        summary = {**task, **aggregate_trajectory(rows), **audit_totals(run_dir / "requests.jsonl"),
                   "status": status, "error": error, "wall_seconds_this_attempt": time.time() - started,
                   "decision_wall_seconds": sum(r["elapsed_seconds"] for r in rows)}
        if task.get("diagnostic"):
            summary.update(recovery_score(rows, task["target_action"], task["recoverable"]))
        equal_budget = config["equal_cost_per_episode_usd"]
        prefix = [r for r in rows if r["cost_cumulative"] <= equal_budget]
        summary["fixed_cost_prefix"] = {"budget_usd": equal_budget, **aggregate_trajectory(prefix)}
        atomic_json(run_dir / "summary.json", summary)
        atomic_json(status_path, {"status": status, "error": error, "steps": len(rows), "updated": time.time()})
        return summary


def run_batch(config, runtime, key_path, tasks, workers):
    runtime = Path(runtime)
    runtime.mkdir(parents=True, exist_ok=True)
    atomic_json(runtime / "batch.json", {"config": config, "tasks": tasks, "workers": workers})
    ctx = mp.get_context("spawn")
    pending = list(tasks)
    completed = []
    # Ramp after successful completions: 4 -> 8 -> 12 -> configured maximum.
    previous_monitor = read_jsonl(runtime / "monitor.jsonl")
    validated_target = previous_monitor[-1].get("target", 4) if previous_monitor else 4
    target = min(workers, max(4, validated_target))
    with ProcessPoolExecutor(max_workers=workers, mp_context=ctx) as pool:
        active = {}
        while pending or active:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage(runtime)
            if memory.available < 2 * 1024 ** 3 or disk.free < 3 * 1024 ** 3:
                target = max(1, target // 2)
                if disk.free < 1 * 1024 ** 3:
                    pending.clear()
            while pending and len(active) < target:
                task = pending.pop(0)
                future = pool.submit(episode, task, config, str(runtime), key_path, workers)
                active[future] = task
            ready, _ = wait(active, timeout=15, return_when=FIRST_COMPLETED)
            for future in ready:
                task = active.pop(future)
                try:
                    result = future.result()
                except Exception as exc:
                    result = {**task, "status": "worker_failed", "error": type(exc).__name__}
                completed.append(result)
                append_jsonl(runtime / "task_results.jsonl", result)
                print(json.dumps({k: result.get(k) for k in ("task_id", "status", "steps", "main_quest_reward", "cost_usd", "error")}), flush=True)
                if result["status"] == "budget_stopped":
                    for remaining in pending:
                        append_jsonl(runtime / "not_started.jsonl", {**remaining, "reason": "global_budget"})
                    pending.clear()
                if result.get("http_429", 0) > 2 or result["status"] in {"failed", "worker_failed"}:
                    target = max(1, target // 2)
                elif len(completed) % 4 == 0:
                    target = min(workers, target + 4)
            ledger = BudgetLedger(runtime / "budget.sqlite", config["total_budget_usd"])
            append_jsonl(runtime / "monitor.jsonl", {"time": time.time(), "cpu_percent": psutil.cpu_percent(),
                "memory_available": memory.available, "disk_free": disk.free, "active": len(active), "target": target,
                "completed": len(completed), "pending": len(pending), "committed_cost_usd": ledger.total()})
    return completed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/protocol.json")
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--key-file", required=True)
    parser.add_argument("--stage", choices=["smoke", "pilot", "collect", "long", "diagnostic", "cost"], required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--cases")
    parser.add_argument("--algorithms", nargs="+")
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text())
    config["implementation_sha256"] = digest({str(p.relative_to(Path(__file__).parents[1])): p.read_text()
        for p in sorted(Path(__file__).parents[1].rglob("*.py"))})
    algorithms = args.algorithms or config["algorithms"]
    max_steps = {"smoke": 20, "pilot": 120, "collect": 120, "long": 200, "diagnostic": 20, "cost": 200}[args.stage]
    if args.stage == "cost":
        config["episode_budget_usd"] = config["equal_cost_per_episode_usd"]
    if args.stage in {"smoke", "pilot"}:
        config["total_budget_usd"] = config["pilot_budget_usd"]
    runtime = Path(args.runtime)
    tasks = []
    frozen_hash = digest(config)[:12]
    if args.stage == "diagnostic":
        cases = json.loads(Path(args.cases).read_text())
        for case in cases:
            if case["split"] != "test":
                continue
            for algorithm in algorithms:
                task = dict(case, diagnostic=True, algorithm=algorithm, max_steps=20,
                            task_id=f"diagnostic-{case['id']}-{algorithm}-{frozen_hash}")
                tasks.append(task)
    else:
        seeds = config["test_seeds"] if args.stage in {"long", "cost"} else config["dev_seeds"]
        if args.stage == "collect":
            seeds = config["diagnostic_seeds"]
            algorithms = ["ShortTermMemoryAgent"]
        prepare_initials(config, runtime, seeds)
        for seed in seeds:
            for game in config["games"]:
                for algorithm in algorithms:
                    tasks.append({"stage": args.stage, "algorithm": algorithm, "game": game, "seed": seed,
                                  "max_steps": max_steps,
                                  "task_id": f"{args.stage}-{algorithm}-{game}-{seed}-{frozen_hash}"})
    random.Random(20261011).shuffle(tasks)
    run_batch(config, runtime, args.key_file, tasks, args.workers)


if __name__ == "__main__":
    main()
