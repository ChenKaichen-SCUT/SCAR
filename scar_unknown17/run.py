"""Independent Stage 6 runner; Stage 5 source and artifacts remain unchanged.
Policy/data manifests are checked before a new paid batch.
"""
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
import sys

for _key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "TOKENIZERS_PARALLELISM"):
    os.environ[_key] = "false" if _key == "TOKENIZERS_PARALLELISM" else "1"

import psutil

from scar.io import atomic_json, append_jsonl, read_jsonl, digest
from scar.providers.deepseek import DeepSeekProvider, BudgetLedger, BudgetExceeded, EpisodeBudgetExceeded
from scar.environment import AGENT_ID, create_environment, save_snapshot, restore, state_digest, isolated_copy
from scar_sequence.supplement import goal_reached
from scar_sequence.evaluate import physical, metrics
from scar_v3.provider import CohortProvider, ledger_for
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


def episode(task, config, runtime, key_path, workers, provider_factory=None):
    task_id = task["task_id"]
    run_dir = Path(runtime) / "runs" / task_id
    run_dir.mkdir(parents=True, exist_ok=True)
    status_path = run_dir / "status.json"
    if status_path.exists() and json.loads(status_path.read_text()).get("status") in {"completed", "completed_budget", "method_abort"}:
        return json.loads((run_dir / "summary.json").read_text())
    started = time.time()
    config = dict(config, seed=task["seed"])
    atomic_json(run_dir / "task.json", {"task": task, "config": config})
    atomic_json(status_path, {"status": "running", "started": started, "pid": os.getpid()})
    rows, env, agent, visible = [], None, None, None
    # Capture upstream verbose logs per task; no shared file handles between workers.
    with (run_dir / "engine.log").open("a") as engine_log, contextlib.redirect_stdout(engine_log), contextlib.redirect_stderr(engine_log):
        try:
            from scar_unknown17.agent import make_agent
            provider = (provider_factory or CohortProvider)(config, run_dir / "requests.jsonl", Path(runtime) / "budget.sqlite", key_path, workers)
            agent = make_agent(task["algorithm"], task["game"], provider, config, run_dir / "memory")
            if task.get("diagnostic"):
                agent.cfg.system_prompt += "\nExperiment recovery objective (priority for this episode): " + task["public_goal"]
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
                initial_hash = state_digest(env)
                if task.get("state_hash") and initial_hash != task["state_hash"]:
                    raise ValueError("Restored physical state differs from frozen case")
                atomic_json(run_dir/"initial_state.json", {"state_hash": initial_hash})
                # Every algorithm receives the identical observed history.
                for transition in task.get("history", []):
                    agent.memorize(f"{transition['before']['text']}\nAction: {transition['action']}\n{transition['after']['text']}")
                    if hasattr(agent, "observe_transition"):
                        agent.observe_transition(transition["before"], transition["action"], transition["after"])
                if task.get("diagnostic"):
                    agent.memorize("Recovery objective: " + task["public_goal"])
                    if hasattr(agent, "set_recovery_objective"):
                        agent.set_recovery_objective(task["target_action"], task["public_goal"])
                visible = VisibleState.observe(env.obs[AGENT_ID])
                save_snapshot(run_dir / "initial.pkl", env)
            done = bool(rows and rows[-1]["done"])
            recovered = bool(rows and rows[-1].get("diagnostic_goal_reached"))
            for index in range(len(rows), task["max_steps"]):
                if done or recovered:
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
                if task["algorithm"] == "SCARV3Agent" or index % 10 == 0:
                    for prediction in decision.get("rule_predictions", [])[:10]:
                        truth = score_candidate(env, prediction["action"])
                        rule_tests.append(dict(prediction, semantic_rejection=truth["semantic_rejection"]))
                target_before = (score_candidate(env, task["target_action"])["semantic_rejection"]
                                 if task.get("diagnostic") else None)
                proposed_effect = None
                if decision["intercepted"]:
                    with isolated_copy(env) as counterfactual:
                        _, cf_reward, cf_done, _ = counterfactual.step({AGENT_ID: decision["proposed_action"]})
                        proposed_effect = {"quest_reward": cf_reward[AGENT_ID].quest,
                                           "game_done": bool(cf_done)}
                        if task.get("diagnostic"):
                            proposed_effect["physical_goal"] = goal_reached(counterfactual, task["goal"])
                            proposed_effect["target_rejected_after"] = score_candidate(counterfactual, task["target_action"])["semantic_rejection"]
                physical_before = physical(env, task)
                if decision["intercepted"]:
                    with isolated_copy(env) as cf:
                        cf.step({AGENT_ID: decision["proposed_action"]})
                        proposed_effect["physical_state"] = physical(cf, task)
                executed_truth = score_candidate(env, action)
                after, reward, done, info = env.step({AGENT_ID: action})
                env.update_scores(reward)
                physical_after = physical(env, task)
                objective_metrics = metrics(physical_before, physical_after, action, task, decision)
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
                       "proposed_effect": proposed_effect, "initial_state_hash": task.get("state_hash"),
                       "response": response, "elapsed_seconds": time.monotonic() - tick,
                       "cost_cumulative": totals_after["cost_usd"],
                       "api_delta": {k: totals_after[k] - totals_before[k] for k in totals_after},
                       "events": list(getattr(agent, "events", [])),
                       "physical_before": physical_before, "physical_after": physical_after,
                       "objective_metrics": objective_metrics}
                if task.get("diagnostic"):
                    recovered = goal_reached(env, task["goal"])
                    row["diagnostic_goal_reached"] = recovered
                    row["target_rejected_before"] = target_before
                    row["target_rejected_after"] = score_candidate(env, task["target_action"])["semantic_rejection"]
                    row["target_condition_release"] = bool(target_before and not row["target_rejected_after"])
                    row["recovery_progress_proxy"] = recovered or row["target_condition_release"]
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
            from scar.providers.deepseek import ModelResponseError
            status = "method_abort" if isinstance(exc, ModelResponseError) else "failed"
            error = f"{type(exc).__name__}: {exc}"
            # Provider exceptions sanitize credentials. Game tracebacks contain no key.
            (run_dir / "error.txt").write_text(traceback.format_exc())
        summary = {**task, **aggregate_trajectory(rows), **audit_totals(run_dir / "requests.jsonl"),
                   "status": status, "error": error, "wall_seconds_this_attempt": time.time() - started,
                   "decision_wall_seconds": sum(r["elapsed_seconds"] for r in rows)}
        if task.get("diagnostic"):
            summary.update(recovery_score(rows, task["target_action"], task["recoverable"]))
            summary["recovery_at_40"] = summary["recovery_steps"] is not None and summary["recovery_steps"] <= 40
            opportunities = [r for r in rows if not r["target_rejected_before"]]
            summary["release_opportunities"] = len(opportunities)
            from scar.agents.scar.state import action_key
            summary["successful_released_retries"] = sum(
                action_key(r["executed_action"]) == action_key(task["target_action"]) and not r["semantic_rejection"] for r in opportunities)
        labelled = [r for r in rows if r.get("proposed_truth") is not None]
        summary["legal_to_rejected"] = sum(not r["proposed_truth"]["semantic_rejection"] and r["semantic_rejection"] for r in labelled)
        summary["rejected_to_legal"] = sum(r["proposed_truth"]["semantic_rejection"] and not r["semantic_rejection"] for r in labelled)
        summary["interventions_with_physical_goal"] = sum(r.get("diagnostic_goal_reached", False) for r in labelled)
        summary["interventions_with_condition_release"] = sum(r.get("target_condition_release", False) for r in labelled)
        summary["interventions_with_quest_reward"] = sum(r["reward"].get("quest", 0) > 0 for r in labelled)
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
    consecutive_failures = 0
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
                consecutive_failures = consecutive_failures + 1 if result["status"] in {"failed", "worker_failed"} else 0
                append_jsonl(runtime / "task_results.jsonl", result)
                print(json.dumps({k: result.get(k) for k in ("task_id", "status", "steps", "main_quest_reward", "cost_usd", "error")}), flush=True)
                if result["status"] == "budget_stopped":
                    for remaining in pending:
                        append_jsonl(runtime / "not_started.jsonl", {**remaining, "reason": "global_budget"})
                    pending.clear()
                if consecutive_failures >= 3:
                    for remaining in pending:
                        append_jsonl(runtime / "not_started.jsonl", {**remaining, "reason": "three_consecutive_execution_failures"})
                    pending.clear()
                if result.get("http_429", 0) > 2 or result["status"] in {"failed", "worker_failed"}:
                    target = max(1, target // 2)
                elif len(completed) % 4 == 0:
                    target = min(workers, target + 4)
            ledger = ledger_for(runtime / "budget.sqlite", config)
            append_jsonl(runtime / "monitor.jsonl", {"time": time.time(), "cpu_percent": psutil.cpu_percent(),
                "memory_available": memory.available, "disk_free": disk.free, "active": len(active), "target": target,
                "completed": len(completed), "pending": len(pending), "committed_cost_usd": ledger.total()})
    return completed


def make_tasks(config,cases):
    tasks=[]
    for case in cases:
        for method in config['algorithms']:
            task={k:v for k,v in case.items() if k not in {'witness','witness_replay','initialization','snapshot_sha256','selection'}}
            task.update(stage='unknown17',diagnostic=True,algorithm=method,
                protocol_cohort=config['protocol_cohort'],task_id=f'{case["id"]}-{method}-{digest(config)[:12]}')
            tasks.append(task)
    random.Random(20261012).shuffle(tasks)
    return tasks


def main():
    p=argparse.ArgumentParser();p.add_argument('--runtime',required=True);p.add_argument('--key',default='/root/.scar-deepseek-key');p.add_argument('--workers',type=int,default=12)
    args=p.parse_args();root=Path(args.runtime)
    config=json.loads(Path('configs/protocol_unknown17.json').read_text())
    freeze=json.loads(Path('results/unknown17/freeze.json').read_text())
    import hashlib
    for name,sha in freeze['code_hashes'].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==sha,name
    cases=json.loads(Path('results/unknown17/cases.json').read_text())
    assert digest(cases)==freeze['dataset_digest']
    tasks=make_tasks(config,cases)
    for task in tasks:
        task['initial_snapshot']=str(root/'initials'/f"{task['id']}.pkl")
    atomic_json(root/'tasks.json',tasks)
    pending=[]
    for task in tasks:
        path=root/'runs'/task['task_id']/'status.json'
        if not path.exists() or json.loads(path.read_text())['status'] not in {'completed','method_abort','completed_budget'}:
            pending.append(task)
    atomic_json(root/'progress.json',{'phase':'closed_loop_running','total':len(tasks),'pending':len(pending),'new_budget_cap_usd':config['total_budget_usd']})
    run_batch(config,root,args.key,pending,args.workers)
    atomic_json(root/'progress.json',{'phase':'batch_returned','total':len(tasks),'note':'Requires independent verification and publication.'})

if __name__=='__main__':main()
