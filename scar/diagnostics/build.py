"""Build validated AO-FR cases from natural failures and real-engine action prefixes.

No agent sees witnesses, validity oracles, complete world state or case labels.
Search failure is 'unverified', never a proof of irrecoverability.
"""
import argparse
import copy
import json
from pathlib import Path
import random

from scar.io import atomic_json, digest
from scar.environment import AGENT_ID, restore, snapshot, save_snapshot, state_digest
from scar.diagnostics.scoring import outcome
from scar.agents.scar.state import action_key


def all_actions(env):
    actions = env.get_all_valid_actions(env.agents[0])
    if isinstance(actions, dict):
        actions = [item for values in actions.values() for item in values]
    return sorted(set(actions))


def transition(env, action):
    before = copy.deepcopy(env.obs[AGENT_ID])
    after, rewards, done, info = env.step({AGENT_ID: action})
    env.update_scores(rewards)
    return {"before": before, "action": action, "after": copy.deepcopy(after[AGENT_ID]),
            **outcome(after, info), "done": done}


def physical_goal(env, action):
    """Ground-truth progress definition fixed from the failed target action."""
    verb, params = env.parse_action(env.agents[0], action)
    if not params:
        return None
    if verb == "enter":
        return {"kind": "location", "name": params[0]}
    if verb in {"pick up", "take out", "craft", "buy", "equip"}:
        object_id = env.world.auxiliary.get("obj_name_to_id", {}).get(params[0])
        if object_id:
            return {"kind": "equipped" if verb == "equip" else "possess", "object_id": object_id,
                    "name": params[0], "baseline": possession(env, object_id, verb == "equip")}
    return None


def possession(env, object_id, equipped=False):
    agent = env.agents[0]
    if equipped:
        return agent.equipped_items_in_limb.get(object_id, 0)
    total = agent.items_in_hands.get(object_id, 0) + agent.equipped_items_in_limb.get(object_id, 0)
    if agent.inventory.container:
        total += agent.inventory.items.get(object_id, 0)
    return total


def goal_reached(env, goal):
    if goal["kind"] == "location":
        return env.world.area_instances[env.curr_agents_state["area"][AGENT_ID]].name == goal["name"]
    return possession(env, goal["object_id"], goal["kind"] == "equipped") > goal["baseline"]


def find_witness(start, target, goal, max_nodes=80):
    # Offline broad, deterministic bounded search. Includes no hardcoded quest route.
    queue = [(snapshot(start), [])]
    seen = set()
    explored = 0
    while queue and explored < max_nodes:
        data, prefix = queue.pop(0)
        env = restore(data)
        explored += 1
        trial = restore(data)
        result = transition(trial, target)
        if not result["semantic_rejection"] and goal_reached(trial, goal):
            return prefix + [target], explored
        if len(prefix) >= 2:
            continue
        candidates = all_actions(env)
        # Prioritize generic precondition-changing actions, not game-specific entities.
        candidates.sort(key=lambda a: (not a.startswith(("equip ", "store ", "drop ", "pick up ", "enter ", "attack ")), a))
        for action in candidates[:24]:
            if action_key(action) == action_key(target):
                continue
            child = restore(data)
            result = transition(child, action)
            if result["semantic_rejection"] or result["done"]:
                continue
            fingerprint = digest([child.curr_agents_state["area"], child.agents[0].to_dict(), child.world.to_dict()])
            if fingerprint not in seen:
                seen.add(fingerprint)
                queue.append((snapshot(child), prefix + [action]))
    return None, explored


def verify(case, start, witness, goal):
    endings = []
    for _ in range(2):
        env = restore(start)
        for action in witness:
            result = transition(env, action)
            if result["semantic_rejection"]:
                return False
        if not goal_reached(env, goal):
            return False
        endings.append(state_digest(env))
    return endings[0] == endings[1]


def natural_statistics(runtime):
    counts = {"total_actions": 0, "semantic_failures": 0, "A_repeated_same_state": 0,
              "B_later_success_changed_state": 0, "C_unknown_diagnosis": 0,
              "D_alternative_recovery": None}
    failures = []
    from scar.agents.scar.state import VisibleState
    from scar.agents.scar.detection import diagnose
    for task_file in sorted((Path(runtime) / "runs").glob("pilot-ShortTermMemoryAgent-*/task.json")):
        run = task_file.parent
        task = json.loads(task_file.read_text())["task"]
        rows = [json.loads(p.read_text()) for p in sorted((run / "steps").glob("*/transition.json"))]
        seen = set()
        for i, row in enumerate(rows):
            counts["total_actions"] += 1
            if not row["semantic_rejection"]:
                continue
            counts["semantic_failures"] += 1
            key = (action_key(row["executed_action"]), row["visible_state_hash"])
            counts["A_repeated_same_state"] += key in seen
            seen.add(key)
            later_success = any(action_key(r["executed_action"]) == key[0] and not r["semantic_rejection"]
                                and r["visible_state_hash"] != key[1] for r in rows[i + 1:])
            counts["B_later_success_changed_state"] += later_success
            before = VisibleState.observe(row["observation"])
            after = VisibleState.observe(row["next_observation"], before)
            event = diagnose(row["executed_action"], before, after)
            counts["C_unknown_diagnosis"] += event is None or event.cause == "unknown"
            failures.append({"task": task, "row": row, "run": str(run), "index": i,
                             "history": [{"before": r["observation"], "action": r["executed_action"],
                                          "after": r["next_observation"]} for r in rows[:i + 1]]})
    return counts, failures


def build(runtime, output, limit=24):
    runtime, output = Path(runtime), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    counts, failures = natural_statistics(runtime)
    atomic_json(output / "natural_frequencies.json", counts)
    candidates = []
    # Natural failures take priority. No duplicate action/condition family inflated by seeds.
    for item in failures:
        row = item["row"]
        data = Path(item["run"]) / "steps" / f"{item['index'] + 1:04}" / "environment.pkl"
        env = restore(data)
        goal = physical_goal(env, row["executed_action"])
        if goal:
            candidates.append((env, row["executed_action"], item["history"], "natural", item["task"], goal))
    # If natural failures are scarce, construct genuine hand-capacity failures by
    # executing a prefix on the official engine. No fabricated feedback or hidden edits.
    for initial in sorted((runtime / "initials").glob("*.pkl")):
        game, seed = initial.stem.rsplit("-", 1)
        if int(seed) != 7:
            continue
        env = restore(initial)
        picks = [a for a in all_actions(env) if a.startswith("pick up ")]
        for shift in range(min(len(picks), 6)):
            trial = restore(initial)
            history = []
            ordered = picks[shift:] + picks[:shift]
            for action in ordered[:4]:
                result = transition(trial, action)
                history.append({k: result[k] for k in ("before", "action", "after")})
                if result["semantic_rejection"]:
                    goal = physical_goal(trial, action)
                    if goal:
                        candidates.append((trial, action, history, "synthetic_action_prefix",
                                           {"game": game, "seed": int(seed)}, goal))
                    break
    records, seen, unverified = [], set(), []
    rng = random.Random(8675309)
    rng.shuffle(candidates)
    for env, target, history, source, task, goal in candidates:
        family = digest([task["game"], action_key(target), history[-1]["after"]["text"].split("I am holding")[-1], goal])
        if family in seen:
            continue
        seen.add(family)
        witness, explored = find_witness(env, target, goal)
        if witness is None:
            unverified.append({"game": task["game"], "action": target, "reason": "bounded_search_no_witness", "nodes": explored})
            continue
        case_id = digest([task["game"], target, goal, history])[:16]
        directory = output / case_id
        directory.mkdir(exist_ok=True)
        state_file = directory / "initial.pkl"
        save_snapshot(state_file, env)
        case = {"id": case_id, "game": task["game"], "seed": task["seed"], "source": source,
                "family": family, "split": "dev" if int(family[:8], 16) % 5 == 0 else "test",
                "types": ["A", "D"] if len(witness) > 1 else ["B"],
                "initial_snapshot": str(state_file.resolve()), "target_action": target,
                "history": history, "recoverable": True, "goal": goal,
                "witness": witness, "state_hash": state_digest(env), "search_nodes": explored}
        case["validated"] = verify(case, state_file, witness, goal)
        if case["validated"]:
            atomic_json(directory / "case.json", case)
            records.append(case)
            if len(witness) > 1:
                # A matched condition-release variant shares the family and split;
                # it is not counted as a new independent mechanism.
                released = restore(state_file)
                release_history = list(history)
                for action in witness[:-1]:
                    result = transition(released, action)
                    release_history.append({k: result[k] for k in ("before", "action", "after")})
                release_id = case_id + "-released"
                release_dir = output / release_id
                release_dir.mkdir(exist_ok=True)
                release_file = release_dir / "initial.pkl"
                save_snapshot(release_file, released)
                variant = dict(case, id=release_id, parent_case_id=case_id, types=["B"],
                               history=release_history, initial_snapshot=str(release_file.resolve()),
                               witness=[target], state_hash=state_digest(released))
                variant["validated"] = verify(variant, release_file, [target], goal)
                if variant["validated"]:
                    atomic_json(release_dir / "case.json", variant)
                    records.append(variant)
        if len(records) >= limit:
            break
    atomic_json(output / "cases.json", records)
    atomic_json(output / "validation.json", {"count": len(records), "unverified": unverified,
                "type_counts": {t: sum(t in r["types"] for r in records) for t in "ABCD"},
                "split_counts": {s: sum(r["split"] == s for r in records) for s in ("dev", "test")},
                "independence": "one case per deduplicated observed action/state family; types overlap",
                "frozen_sha256": digest(records),
                "limitations": "D labels witness-based prerequisite chains, not verified distinct map routes. C may be absent. Search failures excluded, not declared irrecoverable."})
    print(json.dumps({"cases": len(records), "natural": counts, "unverified": len(unverified)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--limit", type=int, default=24)
    args = parser.parse_args()
    build(args.runtime, args.output, args.limit)
