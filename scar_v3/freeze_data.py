"""Independent replay, source checks and immutable AO-FR-Hard freeze, no policies."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
import json
import multiprocessing as mp
from pathlib import Path

from scar.environment import restore, state_digest, AGENT_ID
from scar.io import atomic_json, digest
from scar.diagnostics.scoring import score_candidate
from scar.agents.scar.state import action_key
from scar_v3.state import PublicState
from scar_v3.hard import replay, goal_reached


def validate(case):
    env = restore(case["initial_snapshot"])
    ok, history = replay(case["initial_snapshot"], case["witness"], case["goal"])
    return {"id": case["id"], "exact_twice": ok, "initial_goal_false": not goal_reached(env, case["goal"]),
            "initial_target_rejected": score_candidate(env, case["target_action"])["semantic_rejection"],
            "state_hash_matches": state_digest(env) == case["state_hash"],
            "history_matches_initial_observation": case["history"][-1]["after"] == env.obs[AGENT_ID],
            "witness_length": len(case["witness"])}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--synthetic", required=True)
    parser.add_argument("--natural", required=True)
    parser.add_argument("--historical-runtime", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--limit", type=int, default=120)
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    dest = output / "cases.json"
    if dest.exists():
        raise SystemExit("Dataset already frozen; refusing overwrite")
    synthetic = json.loads((Path(args.synthetic) / "candidate_cases.json").read_text())
    natural = json.loads((Path(args.natural) / "candidate_cases.json").read_text())
    rows = natural + synthetic
    selected = sorted(rows, key=lambda r: (r["source"].startswith("synthetic"), digest([271828, r["family"]])))[:args.limit]
    old = json.loads((Path(args.historical_runtime) / "ao_fr_frozen/cases.json").read_text())
    assert not {r["state_hash"] for r in selected} & {r["state_hash"] for r in old}
    assert len({r["family"] for r in selected}) == len(selected)
    by_split = {s: [r for r in selected if r["split"] == s] for s in ["dev", "test"]}
    for field in ["family", "source_cluster"]:
        assert not {r[field] for r in by_split["dev"]} & {r[field] for r in by_split["test"]}, field
    # Source seed groups are disjoint too; new procedural worlds have separate
    # seed ranges and natural mothers use distinct archived trajectory seeds.
    assert not {(r["game"], r["seed"]) for r in by_split["dev"]} & {(r["game"], r["seed"]) for r in by_split["test"]}
    with ProcessPoolExecutor(max_workers=args.workers, mp_context=mp.get_context("spawn")) as pool:
        validation = list(pool.map(validate, selected))
    failures = [r for r in validation if not all(r[k] for k in ["exact_twice", "initial_goal_false", "initial_target_rejected", "state_hash_matches", "history_matches_initial_observation"])]
    atomic_json(output / "validation.json", {"checks": validation, "failed": failures})
    if failures:
        raise SystemExit("Dataset validation failed; no frozen cases written")
    types = Counter(t for r in selected for t in r["types"])
    required = {"multiple_preconditions", "ambiguous_feedback", "irrelevant_change", "state_release", "alternative_path", "long_recovery_chain", "task_goal_switch"}
    manifest = {
        "name": "AO-FR-Hard", "frozen_at_utc": datetime.now(timezone.utc).isoformat(), "sha256": digest(selected),
        "families": len(selected), "cases": len(selected), "sources": dict(Counter(r["source"] for r in selected)),
        "source_clusters": len({r["source_cluster"] for r in selected}),
        "mechanism_clusters": len({r["mechanism_cluster"] for r in selected}),
        "split_counts": {s: len(rs) for s, rs in by_split.items()}, "types": dict(types),
        "by_game": dict(Counter(r["game"] for r in selected)),
        "missing_types": sorted(required-set(types)),
        "family_target_80_to_120_met": 80 <= len(selected) <= 120,
        "all_witnesses_replayed_twice": True, "old_state_overlap": 0,
        "split_source_overlap": 0, "split_seed_source_overlap": 0,
        "selection": "Natural validated mothers first; remaining candidates in fixed hash order. No V3 evaluation or baseline scores used. One mother per family, release checkpoints auxiliary only.",
        "difficulty": {"witness_lengths": dict(Counter(r["witness_length"] for r in selected)),
                       "prerequisite_steps": dict(Counter(str(r["prerequisite_steps"]) for r in selected)),
                       "bounded_search": "Depth up to 10 and 1500 nodes synthetic; depth up to 8 and 400 nodes natural. Dependency planner may give nonminimal witnessed paths. Restricted action vocabulary/time abstraction; no global shortest claim."},
        "limitations": ["Most cases are synthetic controlled crafting/possession tasks; not a representative sample of whole games.",
                        "Recipe mothers share action mechanisms. Family count is not IID sample size; report source and mechanism cluster uncertainty.",
                        "State release variants are offline auxiliary checks and never counted as new independent hard families.",
                        "Missing types and split-specific coverage must be reported; they are not silently treated as covered."],
    }
    atomic_json(dest, selected)
    atomic_json(output / "manifest.json", manifest)
    atomic_json(output / "dataset_metadata.json", [{k: v for k, v in r.items() if k not in {"history", "initial_snapshot", "counterfactuals"}} for r in selected])
    print(json.dumps(manifest))


if __name__ == "__main__":
    main()
