"""Run only revised SCAR with the original snapshots, provider and step accounting."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import random
import shutil

from scar.experiments import run as original
from scar.experiments.analyze import stage_of, SUCCESS
from scar.io import atomic_json, digest
from scar.providers.deepseek import BudgetLedger

PROJECT = Path(__file__).resolve().parents[1]
ORIGINAL_EPISODE = original.episode


def policy_hash():
    return digest({p.name: p.read_text() for p in [Path(__file__).with_name("agent.py"), Path(__file__).with_name("__init__.py")]})


def core_hash():
    return digest({str(p.relative_to(PROJECT / "scar")): p.read_text() for p in sorted((PROJECT / "scar").rglob("*.py"))})


def episode(task, config, runtime, key_path, workers):
    from scar_v2.agent import make_agent
    import scar.integration
    saved = scar.integration.make_agent
    scar.integration.make_agent = make_agent
    try:
        return ORIGINAL_EPISODE(task, config, runtime, key_path, workers)
    finally:
        scar.integration.make_agent = saved


def freeze(config, runtime, historical):
    runtime, historical = Path(runtime).resolve(), Path(historical).resolve()
    if runtime == historical:
        raise ValueError("The revised study needs its own runtime")
    assert config["algorithms"] == ["SCARV2Agent"]
    assert config["max_steps"] == 200 and config["test_seeds"] == [101]
    old = json.loads((PROJECT / "results/formal_freeze.json").read_text())
    assert core_hash() == old["implementation_sha256"], "First-round implementation changed"
    shared = ["upstream_commit", "python_hash_seed", "model", "base_url", "thinking", "temperature", "max_tokens",
              "games", "max_steps", "short_term_memory_size", "embedding_model", "embedding_revision",
              "scar", "pricing_usd_per_million", "equal_cost_per_episode_usd", "total_budget_usd"]
    assert all(config[k] == old["config"][k] for k in shared)
    runtime.mkdir(parents=True, exist_ok=True)
    # One project-wide budget and semaphore: no fresh $20 allowance for the revision.
    for name in ["budget.sqlite", "api_slots"]:
        src, dst = historical / name, runtime / name
        assert src.exists()
        if dst.is_symlink():
            assert dst.resolve() == src.resolve()
        elif dst.exists():
            raise ValueError(f"Refusing to replace {dst}")
        else:
            dst.symlink_to(src, target_is_directory=src.is_dir())
    snapshots = []
    (runtime / "initials").mkdir(exist_ok=True)
    for game in config["games"]:
        for seed in config["test_seeds"] + config["dev_seeds"]:
            src = historical / "initials" / f"{game}-{seed}.pkl"
            dst = runtime / "initials" / src.name
            if not dst.exists():
                shutil.copy2(src, dst)
            assert dst.read_bytes() == src.read_bytes()
            snapshots.append({"game": game, "seed": seed, "sha256": hashlib.sha256(src.read_bytes()).hexdigest()})
    cases = json.loads((historical / "ao_fr_frozen/cases.json").read_text())
    test_cases = {c["id"]: c for c in cases if c["split"] == "test"}
    assert len(test_cases) == 72
    archived = []
    for path in sorted((historical / "runs").glob("*/summary.json")):
        row = json.loads(path.read_text())
        stage = stage_of(row)
        if row.get("protocol_cohort") != "formal_hash0":
            continue
        if stage == "diagnostic" and row.get("id") in test_cases:
            case = test_cases[row["id"]]
            for key in ["initial_snapshot", "history", "goal", "target_action", "seed", "game"]:
                assert row[key] == case[key], (row["task_id"], key)
        elif not (stage in {"long", "cost"} and row["seed"] == 101):
            continue
        assert row["status"] in SUCCESS
        task_cfg = json.loads(path.with_name("task.json").read_text())["config"]
        assert all(config[k] == task_cfg[k] for k in shared)
        archived.append({k: v for k, v in row.items() if k not in {"history", "witness", "initial_snapshot", "goal"}})
    assert len(archived) == 318
    frozen = {
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(), "study": "v2_regression",
        "parent_commit": "6e483bb66c1d7d13d9b2d28b4fa052d3c84d74cf", "config": config,
        "v1_implementation_sha256": core_hash(), "v2_policy_sha256": policy_hash(),
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "cases_sha256": digest(cases), "archived_comparators_sha256": digest(archived),
        "initial_snapshots": snapshots, "baseline_tasks_reused": len(archived),
        "new_tasks": {"smoke": 3, "diagnostic": 72, "long": 3, "cost": 3},
        "cost_before_revision_usd": BudgetLedger(runtime / "budget.sqlite", config["total_budget_usd"]).total(),
        "scope": "Regression comparison after inspecting v1 outcomes; reused cases are not an unseen test. Historical baselines are not rerun; model service drift and API nondeterminism remain possible.",
    }
    output = PROJECT / "results/v2"
    output.mkdir(exist_ok=True)
    dest = output / "freeze.json"
    if dest.exists():
        prior = json.loads(dest.read_text())
        for field in ["config", "v1_implementation_sha256", "v2_policy_sha256", "runner_sha256", "cases_sha256", "archived_comparators_sha256", "initial_snapshots"]:
            assert prior[field] == frozen[field], f"Freeze conflict: {field}"
    else:
        atomic_json(dest, frozen)
    atomic_json(output / "archived_comparators.json", archived)
    return json.loads(dest.read_text())


def run_stage(stage, config, runtime, historical, key_file, workers):
    frozen = json.loads((PROJECT / "results/v2/freeze.json").read_text())
    assert config == frozen["config"]
    assert core_hash() == frozen["v1_implementation_sha256"] and policy_hash() == frozen["v2_policy_sha256"]
    assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest() == frozen["runner_sha256"]
    config = dict(config, implementation_sha256=policy_hash())
    if stage == "cost":
        config["episode_budget_usd"] = config["equal_cost_per_episode_usd"]
    config_hash = digest(config)[:12]
    tasks = []
    if stage == "diagnostic":
        cases = json.loads((Path(historical) / "ao_fr_frozen/cases.json").read_text())
        assert digest(cases) == frozen["cases_sha256"]
        for case in cases:
            if case["split"] == "test":
                tasks.append(dict(case, diagnostic=True, algorithm="SCARV2Agent", max_steps=20,
                                  protocol_cohort="formal_hash0", study="v2_regression",
                                  task_id=f"diagnostic-{case['id']}-SCARV2Agent-{config_hash}"))
    else:
        for game in config["games"]:
            for seed in config["dev_seeds"] if stage == "smoke" else config["test_seeds"]:
                tasks.append(dict(stage=stage, algorithm="SCARV2Agent", game=game, seed=seed,
                                  max_steps=20 if stage == "smoke" else config["max_steps"],
                                  protocol_cohort="formal_hash0", study="v2_regression",
                                  task_id=f"{stage}-SCARV2Agent-{game}-{seed}-{config_hash}"))
    random.Random(20261011).shuffle(tasks)
    atomic_json(Path(runtime) / f"tasks_{stage}.json", tasks)
    original.episode = episode
    results = original.run_batch(config, runtime, key_file, tasks, workers)
    if len(results) != len(tasks) or any(r["status"] not in SUCCESS for r in results):
        raise RuntimeError("Stage has unfinished runs; inspect status and resume only those tasks")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["freeze", "smoke", "diagnostic", "long", "cost"], required=True)
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--historical-runtime", required=True)
    parser.add_argument("--config", default="configs/protocol_v2.json")
    parser.add_argument("--key-file")
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()
    assert os.environ.get("PYTHONHASHSEED") == "0", "Use PYTHONHASHSEED=0"
    config = json.loads(Path(args.config).read_text())
    if args.stage == "freeze":
        frozen = freeze(config, args.runtime, args.historical_runtime)
        print(json.dumps({"new_tasks": frozen["new_tasks"], "reused_tasks": frozen["baseline_tasks_reused"],
                          "cost_before_revision_usd": frozen["cost_before_revision_usd"]}))
    else:
        run_stage(args.stage, config, args.runtime, args.historical_runtime, args.key_file, args.workers)


if __name__ == "__main__":
    main()
