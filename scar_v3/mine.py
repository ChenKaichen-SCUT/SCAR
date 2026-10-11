"""Mine genuinely new hard mothers from archived natural STM trajectories, offline."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import multiprocessing as mp
from pathlib import Path

from scar.environment import restore, snapshot, save_snapshot, AGENT_ID, state_digest
from scar.diagnostics.build import transition
from scar.diagnostics.scoring import score_candidate
from scar.io import digest, atomic_json
from scar.agents.scar.state import action_key
from scar_v3.state import parse_action, PublicState
from scar_v3.hard import goal_reached, owned, bounded_search, replay


def mine_one(job):
    source, index, output, excluded = job
    source, output = Path(source), Path(output)
    task = json.loads((source / "task.json").read_text())["task"]
    paths = sorted(source.glob("steps/*/transition.json"))
    rows = [json.loads(p.read_text()) for p in paths]
    row = rows[index]
    target = row["executed_action"]
    a = parse_action(target)
    env = restore(paths[index].with_name("environment.pkl"))
    if state_digest(env) in excluded:
        return {"accepted": False, "reason": "old_diagnostic_mother"}
    if a.verb == "enter":
        areas = [area for area in env.world.area_instances.values() if area.name == a.target]
        if len(areas) != 1:
            return {"accepted": False, "reason": "ambiguous_area_name"}
        goal = {"kind": "location", "area_id": areas[0].id, "name": a.target}
        materials, products = {}, {}
    else:
        oid = env.world.auxiliary["obj_name_to_id"].get(a.target)
        if not oid or oid not in env.world.objects:
            return {"accepted": False, "reason": "instance_or_unknown_object"}
        goal = {"kind": "possess", "object_id": oid, "name": a.target, "amount": owned(env, oid) + 1}
        obj = env.world.objects[oid]
        materials, products = dict(obj.craft_ingredients or {}), {oid: 1}
    initial_truth = score_candidate(env, target)
    if not initial_truth["semantic_rejection"] or goal_reached(env, goal):
        return {"accepted": False, "reason": "not_initially_blocked"}
    start = snapshot(env)
    witness = []
    # Replay the subsequent natural choices on a fresh engine copy. A removed
    # rejected choice cannot carry its old outcome: each remaining action is rerun.
    for next_row in rows[index+1:index+41]:
        action = next_row["executed_action"]
        if score_candidate(env, action)["semantic_rejection"]:
            continue
        observed = transition(env, action)
        if observed["semantic_rejection"]:
            break
        witness.append(action)
        if goal_reached(env, goal):
            break
    if not goal_reached(env, goal) or not 4 <= len(witness) <= 16:
        return {"accepted": False, "reason": "natural_continuation_no_hard_witness", "length": len(witness)}
    shorter, search = bounded_search(restore(start), goal, materials, products, max_depth=min(len(witness)-1, 8), max_nodes=400)
    if shorter:
        witness = shorter
    if len(witness) < 4:
        return {"accepted": False, "reason": "shorter_solution_found", "length": len(witness)}
    valid, verified = replay(start, witness, goal)
    if not valid:
        return {"accepted": False, "reason": "witness_replay_failed"}
    history = [{"before": r["observation"], "action": r["executed_action"], "after": r["next_observation"]} for r in rows[:index+1]]
    public = PublicState.observe(row["next_observation"])
    signature = {k: v.truth for k, v in public.features(target).items()}
    mechanism = digest([task["game"], a.verb, signature, goal["kind"]])
    family = digest([task["game"], action_key(target), signature, initial_truth["feedback"], public.location])
    labels = []
    if "ingredients" in initial_truth["feedback"] or "Nothing happens" in initial_truth["feedback"]:
        labels.append("ambiguous_feedback")
    original = [i for i, r in enumerate(verified) if action_key(r["action"]) == action_key(target)]
    if original and original[0] >= 3:
        labels.append("long_recovery_chain")
    if not original:
        labels.append("alternative_path")
    # Mere tutorial goal changes somewhere in the history are insufficient.
    # Require a currently explicit new goal, matching this case's objective, plus
    # an actually failed previous goal superseded by the new public instruction.
    current_goal = PublicState.observe(row["next_observation"]).goal
    superseded = [r for r in rows[max(0,index-12):index] if r["semantic_rejection"]
                  and (g := PublicState.observe(r["observation"]).goal)
                  and action_key(g) == action_key(r["executed_action"])
                  and current_goal and action_key(g) != action_key(current_goal)]
    if current_goal and action_key(current_goal) == action_key(target) and superseded:
        labels.append("task_goal_switch")
    if not labels:
        return {"accepted": False, "reason": "no_validated_hard_type"}
    folder = output / family[:16]
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "initial.pkl").write_bytes(start)
    case = {"id": "natural-hard-" + family[:16], "family": family, "mechanism_cluster": mechanism,
            "source_cluster": source.name, "source_seed_cluster": f"{task['game']}-{task['seed']}",
            "game": task["game"], "seed": task["seed"], "source": "natural_STM_failure_replayed_continuation",
            "source_task": source.name, "source_index": index, "target_action": target, "goal": goal,
            "public_goal": f"Recover the previously blocked objective: {target}. Reach the corresponding location or acquire the target object; another valid route is allowed.",
            "initial_snapshot": str((folder / "initial.pkl").resolve()), "history": history,
            "types": labels, "witness": witness, "witness_length": len(witness),
            "prerequisite_steps": original[0] if original else None, "state_hash": state_digest(restore(start)),
            "initial_truth": initial_truth, "search": search, "validated": True, "recoverable": True,
            "split": "dev" if task["seed"] == 202 else "test",
            "limitations": "Natural follow-up supplies a replayed witness; shorter search is bounded and uses a restricted action vocabulary. Global minimality is not claimed."}
    atomic_json(folder / "case.json", case)
    return {"accepted": True, "case": case}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--historical-runtime", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    root, output = Path(args.historical_runtime), Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    excluded = {c["state_hash"] for c in json.loads((root / "ao_fr_frozen/cases.json").read_text())}
    jobs = []
    for path in sorted((root / "runs").glob("*/task.json")):
        task = json.loads(path.read_text())["task"]
        if task["algorithm"] != "ShortTermMemoryAgent" or task.get("stage") not in {"long", "cost"} or task["seed"] not in {202, 303}:
            continue
        seen = set()
        for p in sorted(path.parent.glob("steps/*/transition.json")):
            r = json.loads(p.read_text())
            key = (action_key(r["executed_action"]), r["visible_state_hash"])
            if r["semantic_rejection"] and parse_action(r["executed_action"]).verb in {"enter", "craft", "pick up", "take out"} and key not in seen:
                seen.add(key)
                jobs.append((str(path.parent), r["index"], str(output), excluded))
    results = []
    with ProcessPoolExecutor(max_workers=args.workers, mp_context=mp.get_context("spawn")) as pool:
        for i, result in enumerate(pool.map(mine_one, jobs)):
            results.append(result)
            print(json.dumps({"done": i+1, "total": len(jobs), "accepted": sum(r["accepted"] for r in results)}), flush=True)
    # A mechanism-matched mother cannot appear in both dev and test. Prefer dev
    # for duplicate families, without consulting any SCAR score.
    grouped = {}
    for r in sorted((r["case"] for r in results if r["accepted"]), key=lambda r: (r["split"] != "dev", r["source_task"], r["source_index"])):
        grouped.setdefault(r["family"], r)
    atomic_json(output / "candidate_cases.json", list(grouped.values()))
    atomic_json(output / "mining_summary.json", {"attempted": len(jobs), "accepted_before_dedup": sum(r["accepted"] for r in results),
                "families": len(grouped), "excluded": [r for r in results if not r["accepted"]]})


if __name__ == "__main__":
    main()
