"""AO-FR-Hard construction and search. OFFLINE ONLY: may inspect hidden state.

Synthetic cases alter initial allocations/topology, never action rules or feedback.
Every retained outcome and witness is replayed through the real engine. Family
identity excludes seeds. More conservative source/mechanism clusters are retained.
"""
import argparse
from collections import Counter, deque
from concurrent.futures import ProcessPoolExecutor
import contextlib
import copy
import hashlib
import json
import math
import multiprocessing as mp
from pathlib import Path
import random
import shlex
import tempfile

from scar.environment import AGENT_ID, create_environment, restore, snapshot, save_snapshot, state_digest
from scar.diagnostics.build import transition
from scar.diagnostics.scoring import score_candidate
from scar.io import atomic_json, digest


def base_id(env, oid):
    for mapping in [env.world.container_instances, env.world.writable_instances]:
        if oid in mapping:
            return oid.rsplit("_", 1)[0]
    return oid


def owned(env, oid):
    agent = env.agents[0]
    counts = Counter(agent.items_in_hands) + Counter(agent.equipped_items_in_limb)
    if agent.inventory.container:
        counts.update(agent.inventory.items)
    for hand in agent.items_in_hands:
        if hand in env.world.container_instances:
            counts.update(env.world.container_instances[hand].inventory)
    return sum(v for k, v in counts.items() if base_id(env, k) == oid)


def goal_reached(env, goal):
    if goal["kind"] == "possess":
        return owned(env, goal["object_id"]) >= goal.get("amount", 1)
    if goal["kind"] == "location":
        return env.curr_agents_state["area"][AGENT_ID] == goal["area_id"]
    raise ValueError("Unknown physical goal")


def relevant_actions(env, goal, materials, products):
    """Search vocabulary only; never supplied to an agent or used as a policy."""
    agent = env.agents[0]
    area = env.world.area_instances[env.curr_agents_state["area"][AGENT_ID]]
    names = {v: k for k, v in env.world.auxiliary["obj_name_to_id"].items()}
    relevant = set(materials) | set(products) | {goal.get("object_id"), "obj_key", "obj_torch"}
    containers = [c.name for cid, c in env.world.container_instances.items()
                  if cid in area.objects or cid in agent.items_in_hands or cid in agent.equipped_items_in_limb]
    destinations = containers + (["inventory"] if agent.inventory.container else [])
    actions = [f"enter {shlex.quote(env.world.area_instances[n].name)}" for n in area.neighbors]
    for oid in area.objects:
        if base_id(env, oid) in relevant or oid in env.world.container_instances:
            actions.append("pick up " + shlex.quote(names[oid]))
            if base_id(env, oid) in relevant:
                for container in destinations:
                    count = min(int(math.ceil(area.objects[oid])), int(materials.get(base_id(env, oid), 1)))
                    if count > 0:
                        actions.append(f"store {count} {shlex.quote(names[oid])} {shlex.quote(container)}")
    for oid in agent.items_in_hands:
        actions.append("drop " + shlex.quote(names[oid]))
        if oid in env.world.container_instances:
            actions.append("equip " + shlex.quote(names[oid]))
    for oid in products:
        if oid in env.world.objects and env.world.objects[oid].craft_ingredients:
            for amount in sorted({1, products[oid]}):
                actions.append(f"craft {amount} {shlex.quote(env.world.objects[oid].name)}")
    for container in destinations:
        contents = agent.inventory.items if container == "inventory" else next(c.inventory for c in env.world.container_instances.values() if c.name == container)
        for oid in contents:
            if base_id(env, oid) in relevant:
                actions.append(f"take out {shlex.quote(names[oid])} {shlex.quote(container)}")
    return sorted(set(actions))


def search_key(env):
    # Controlled construction has no moving NPCs. Excluding time suppresses pure
    # waiting loops; this is a bounded abstraction, not a global shortest-path proof.
    agent = env.agents[0]
    return digest([env.curr_agents_state["area"], agent.items_in_hands, agent.equipped_items_in_limb,
                   {k: c.inventory for k, c in env.world.container_instances.items()},
                   {k: [a.objects, a.npcs, {n: p.locked for n, p in a.neighbors.items()}]
                    for k, a in env.world.area_instances.items()}])


def bounded_search(start, goal, materials, products, max_depth=10, max_nodes=1500):
    queue = deque([(snapshot(start), [])])
    seen = {search_key(start)}
    expanded, full_depth = 0, -1
    while queue and expanded < max_nodes:
        data, prefix = queue.popleft()
        env = restore(data)
        expanded += 1
        if goal_reached(env, goal):
            return prefix, {"expanded": expanded, "frontier": len(queue), "found_depth": len(prefix),
                            "exhausted": False, "complete_through_depth": len(prefix)-1,
                            "vocabulary": "goal-relevant movement, containers, resource transfer and recipe actions"}
        if len(prefix) >= max_depth:
            continue
        if not queue or len(queue[0][1]) > len(prefix):
            full_depth = len(prefix)-1
        for action in relevant_actions(env, goal, materials, products):
            child = restore(data)
            result = transition(child, action)
            if result["semantic_rejection"] or result["done"]:
                continue
            key = search_key(child)
            if key not in seen:
                seen.add(key)
                queue.append((snapshot(child), prefix + [action]))
    return None, {"expanded": expanded, "frontier": len(queue), "found_depth": None,
                  "exhausted": not queue, "complete_through_depth": max_depth if not queue else len(queue[0][1])-1,
                  "vocabulary": "goal-relevant movement, containers, resource transfer and recipe actions"}


def replay(start, actions, goal):
    endings, histories = [], []
    for _ in range(2):
        env, history = restore(start), []
        for action in actions:
            result = transition(env, action)
            history.append(result)
            if result["semantic_rejection"]:
                return False, history
        if not goal_reached(env, goal):
            return False, history
        endings.append(state_digest(env)); histories.append(history)
    return endings[0] == endings[1], histories[0]


def recipe_plan(env, oid, serial):
    obj = env.world.objects[oid]
    if not obj.craft_ingredients or any(k not in env.world.objects for k in obj.craft_ingredients):
        raise ValueError("recipe has missing/undefined ingredients")
    products = {oid: 1}
    materials = {k: int(math.ceil(v)) for k, v in obj.craft_ingredients.items()}
    expand = next((k for k in sorted(materials) if env.world.objects[k].craft_ingredients
                   and env.world.objects[k].category != "container" and env.world.objects[k].usage != "writable"
                   and all(i in env.world.objects and env.world.objects[i].usage != "writable"
                           for i in env.world.objects[k].craft_ingredients)), None)
    if expand and serial % 2 == 0:
        amount = materials.pop(expand)
        products[expand] = amount
        for k, v in env.world.objects[expand].craft_ingredients.items():
            materials[k] = materials.get(k, 0) + int(math.ceil(v * amount))
    graph = {p: {"ingredients": env.world.objects[p].craft_ingredients,
                 "dependencies": env.world.objects[p].craft_dependencies} for p in sorted(products)}
    alternative = serial % 5 == 1 and obj.category != "container" and obj.usage != "writable"
    game = type(env).__module__.split(".")[-2]
    mechanism = digest([game, sorted((len(v["ingredients"]), sorted(v["ingredients"].values()), len(v["dependencies"]))
                                    for v in graph.values()), alternative])
    return products, materials, graph, alternative, mechanism


def construct_witness(start, goal, materials, products, container_name, work_area):
    """Dependency-directed planning, verified by execution, not a policy answer."""
    env, actions = restore(start), []
    def execute(action):
        r = transition(env, action)
        if r["semantic_rejection"]:
            raise ValueError("dependency planner action rejected: " + action)
        actions.append(action)
    execute("pick up " + shlex.quote(container_name))
    execute("equip " + shlex.quote(container_name))
    for oid, amount in sorted(materials.items()):
        execute(f"store {amount} {shlex.quote(env.world.objects[oid].name)} inventory")
    execute("enter " + shlex.quote(work_area))
    for oid, amount in sorted(products.items(), key=lambda x: x[0] == goal["object_id"]):
        execute(f"craft {amount} {shlex.quote(env.world.objects[oid].name)}")
        area = env.world.area_instances[env.curr_agents_state["area"][AGENT_ID]]
        found = [k for k in area.objects if base_id(env, k) == oid]
        if not found:
            raise ValueError("planner produced no matching object")
        names = {v: k for k, v in env.world.auxiliary["obj_name_to_id"].items()}
        if oid == goal["object_id"]:
            execute("pick up " + shlex.quote(names[found[0]]))
        else:
            execute(f"store {amount} {shlex.quote(names[found[0]])} inventory")
    return actions if goal_reached(env, goal) else None


def create_case(job):
    game, oid, serial, seed, output, nodes = job
    folder = Path(output) / "candidates" / f"{game}-{oid}"
    folder.mkdir(parents=True, exist_ok=True)
    result_file = folder / "construction.json"
    if result_file.exists():
        return json.loads(result_file.read_text())
    with (folder / "engine.log").open("a") as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        try:
            env, _ = create_environment(game, seed, folder / "world")
            before_construction = state_digest(env)
            obj = env.world.objects[oid]
            products, materials, recipe_graph, alternative, mechanism = recipe_plan(env, oid, serial)
            if any(env.world.objects[k].category == "container" or env.world.objects[k].usage == "writable" for k in materials):
                raise ValueError("instance ingredient construction not supported; retained as an exclusion")
            agent = env.agents[0]
            available_areas = [a for a in env.world.area_instances.values() if "tutorial" not in a.id]
            available_areas.sort(key=lambda a: a.id)
            if len(available_areas) < 4:
                raise ValueError("insufficient areas")
            selected = available_areas[:4]
            path_cls = type(next(p for a in available_areas for p in a.neighbors.values()))
            # Controlled initial configuration, recorded explicitly. All feedback
            # after it is generated by unmodified official action and step rules.
            for area in env.world.area_instances.values():
                area.objects, area.npcs, area.neighbors = {}, [], {}
                area.light = True
            for left, right in zip(selected, selected[1:]):
                left.neighbors[right.id] = path_cls(to_id=right.id, locked=False, object_to_unlock=None)
                right.neighbors[left.id] = path_cls(to_id=left.id, locked=False, object_to_unlock=None)
            for place in env.world.place_instances.values():
                place.unlocked = True
            tutorial = env.world.auxiliary.get("tutorial_room", {})
            if tutorial:
                tutorial["removed"] = True
            agent.items_in_hands, agent.equipped_items_in_limb = {}, {}
            agent.inventory.container = None
            agent.hp = 100
            env.curr_agents_state["area"][AGENT_ID] = selected[0].id
            if "active_combats" in env.curr_agents_state:
                env.curr_agents_state["active_combats"][AGENT_ID] = {}
            for container in env.world.container_instances.values():
                container.inventory = {}
            container = max(env.world.container_instances.values(), key=lambda c: c.capacity)
            selected[0].objects = dict(materials, **{container.id: 1})
            if "obj_coin" not in materials:
                selected[0].objects["obj_coin"] = 1
            dependencies = sorted({d for p in products for d in env.world.objects[p].craft_dependencies})
            for d in dependencies:
                if d not in env.world.objects:
                    raise ValueError("recipe references undefined dependency")
                selected[1].objects[d] = 1
            # Alternate acquisition exists only in a declared subset; the target
            # action is still craft, while the physical objective is possession.
            if alternative:
                selected[3].objects[oid] = 1
            target = f"craft 1 {shlex.quote(obj.name)}"
            goal = {"kind": "possess", "object_id": oid, "name": obj.name, "amount": 1}
            initialization = {
                "source": "programmatically_constructed_initial_state", "world_seed": seed,
                "source_world_hash": before_construction, "game": game, "recipe_target": oid,
                "edits": ["clear initial objects/NPCs and combat", "empty hands and inventory", "four existing areas connected in a line",
                          "enable light and place access", "disable introductory tutorial via existing completion flag",
                          "place recipe inputs and existing empty container in area 0", "place required workstations in area 1",
                          "optional alternate existing object in area 3"],
                "areas": [a.id for a in selected], "materials": materials, "products": products,
                "dependencies": dependencies, "alternative_object": alternative,
            }
            atomic_json(folder / "initialization.json", initialization)
            # Refresh observations using an actual action; never hand-write feedback.
            transition(env, "wait")
            history = []
            # Public inspections reveal recipes, but not hidden quantities/solutions.
            for material in sorted(materials)[:3]:
                r = transition(env, "inspect " + shlex.quote(env.world.objects[material].name))
                history.append({k: r[k] for k in ["before", "action", "after"]})
            initial_failure = transition(env, target)
            if not initial_failure["semantic_rejection"]:
                raise ValueError("target did not actually fail")
            history.append({k: initial_failure[k] for k in ["before", "action", "after"]})
            labels = ["ambiguous_feedback"] if "ingredients" in initial_failure["after"]["text"] else []
            counterfactuals = []
            if dependencies:
                cf = restore(snapshot(env))
                move = transition(cf, "enter " + shlex.quote(selected[1].name))
                retry = score_candidate(cf, target)
                if not move["semantic_rejection"] and retry["semantic_rejection"] and "ingredients" in retry["feedback"]:
                    labels += ["multiple_preconditions", "ambiguous_feedback"]
                    counterfactuals.append({"intervention": [move["action"]], "remaining_rejection": retry,
                                           "interpretation": "workstation availability alone does not restore execution"})
            if serial % 3 == 0 and "obj_coin" not in materials:
                before_truth = score_candidate(env, target)
                r = transition(env, "pick up coin")
                # The action happened even if it does not qualify as an irrelevant
                # perturbation. All algorithms must receive that observed history.
                history.append({k: r[k] for k in ["before", "action", "after"]})
                after_truth = score_candidate(env, target)
                if not r["semantic_rejection"] and before_truth["feedback"] == after_truth["feedback"]:
                    labels.append("irrelevant_change")
                    counterfactuals.append({"intervention": ["pick up coin"], "before": before_truth, "after": after_truth})
            start = snapshot(env)
            planned = None
            try:
                planned = construct_witness(start, goal, materials, products, container.name, selected[1].name)
            except ValueError:
                pass
            witness, search = bounded_search(env, goal, materials, products,
                                             max_depth=min(10, len(planned)-1) if planned else 10, max_nodes=nodes)
            if witness is None and planned:
                witness = planned
                search["witness_source"] = "executed_dependency_regression_plan"
                search["shortest_proven"] = False
            else:
                search["witness_source"] = "bounded_BFS"
                search["shortest_proven"] = "restricted vocabulary and abstraction only"
            if witness is None:
                raise ValueError(f"bounded search found no witness ({search})")
            if len(witness) < 4:
                raise ValueError(f"short solution found ({len(witness)} actions); not accepted as hard")
            valid, witnessed_history = replay(start, witness, goal)
            if not valid:
                raise ValueError("witness failed exact replay")
            target_indices = [i for i, r in enumerate(witnessed_history) if r["action"] == target]
            prerequisite_steps = target_indices[0] if target_indices else None
            if prerequisite_steps is not None and prerequisite_steps >= 3 and search["complete_through_depth"] >= 2:
                labels.append("long_recovery_chain")
            if not target_indices and alternative:
                labels.append("alternative_path")
            if not labels:
                raise ValueError("no validated hard mechanism")
            # The release checkpoint is an auxiliary counterfactual, not a new family
            # or an additional easy case in the principal hard recovery denominator.
            if target_indices:
                release = restore(start)
                for action in witness[:target_indices[0]]:
                    transition(release, action)
                released_truth = score_candidate(release, target)
                if not released_truth["semantic_rejection"]:
                    labels.append("state_release")
                    save_snapshot(folder / "released.pkl", release)
                    counterfactuals.append({"intervention": witness[:target_indices[0]], "released_truth": released_truth,
                                           "snapshot": str((folder / "released.pkl").resolve())})
            family = digest([game, oid, recipe_graph])
            state_file = folder / "initial.pkl"
            state_file.write_bytes(start)
            result = {"id": "hard-" + family[:16], "family": family, "mechanism_cluster": mechanism,
                      "source_cluster": f"{game}-procedural-world-{seed}", "game": game, "seed": seed,
                      "source": "synthetic_initial_configuration_real_engine", "target_action": target,
                      "goal": goal, "public_goal": f"Obtain at least one {obj.name} in your possession; the previous craft attempt failed. Any valid route is allowed.",
                      "initial_snapshot": str(state_file.resolve()), "history": history,
                      "types": sorted(set(labels)), "witness": witness, "witness_length": len(witness),
                      "prerequisite_steps": prerequisite_steps, "counterfactuals": counterfactuals,
                      "recipe_graph": recipe_graph, "state_hash": state_digest(restore(start)),
                      "search": search, "validated": True, "recoverable": True,
                      "limitations": "Bounded BFS over goal-relevant actions with time-abstracted deduplication. Minimal only within this search vocabulary and abstraction; not globally shortest. All initial-state edits are synthetic and recorded."}
        except Exception as exc:
            result = {"game": game, "target_id": oid, "validated": False, "reason": str(exc), "error_type": type(exc).__name__}
        atomic_json(result_file, result)
    return result


def build(output, workers=8, limit=120, nodes=1500):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    jobs = []
    for game in ["remnant", "mark", "metropolis"]:
        with tempfile.TemporaryDirectory() as tmp:
            env, _ = create_environment(game, 1101, tmp)
            targets = sorted(o.id for o in env.world.objects.values() if o.craft_ingredients)
            for i, oid in enumerate(targets):
                try:
                    _, _, _, _, mechanism = recipe_plan(env, oid, i)
                    seed = (1101 if int(mechanism[:8], 16) % 5 == 0 else 1201) + i % 4
                except ValueError:
                    seed = 1201 + i % 4
                jobs.append((game, oid, i, seed, str(output), nodes))
    # Test splitting depends only on mechanism identity, never on a tested policy.
    random.Random(314159).shuffle(jobs)
    if limit:
        jobs = jobs[:limit]
    results = []
    with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("spawn")) as pool:
        for row in pool.map(create_case, jobs):
            results.append(row)
            print(json.dumps({"done": len(results), "accepted": sum(r["validated"] for r in results),
                              "game": row["game"], "id": row.get("id"), "reason": row.get("reason"), "length": row.get("witness_length")}), flush=True)
    accepted = sorted([r for r in results if r["validated"]], key=lambda r: r["family"])
    seen = set()
    for row in accepted:
        assert row["family"] not in seen
        seen.add(row["family"])
        row["split"] = "dev" if int(row["mechanism_cluster"][:8], 16) % 5 == 0 else "test"
    atomic_json(output / "candidate_cases.json", accepted)
    atomic_json(output / "construction_summary.json", {
        "stage": "candidate_dataset_not_yet_frozen", "attempted": len(results), "accepted_families": len(accepted),
        "source_clusters": len({r["source_cluster"] for r in accepted}), "mechanism_clusters": len({r["mechanism_cluster"] for r in accepted}),
        "types": dict(Counter(t for r in accepted for t in r["types"])), "splits": dict(Counter(r["split"] for r in accepted)),
        "unverified": [r for r in results if not r["validated"]], "sha256": digest(accepted),
        "missing_requirements": ["natural-source hard candidates pending", "real task-goal-switch construction pending", "independent final validation pending"],
        "independence": "Seed is excluded from family identity; different target dependency graphs define mothers. Source and coarser mechanism clusters must also be reported. Variants never increase family count."})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--limit", type=int, default=120)
    parser.add_argument("--nodes", type=int, default=1500)
    args = parser.parse_args()
    build(args.output, args.workers, args.limit, args.nodes)
