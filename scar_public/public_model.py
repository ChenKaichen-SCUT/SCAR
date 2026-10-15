"""Small observation-derived model. Unknown is never silently converted to false.

This adapter parses the public AgentOdyssey text interface, not engine objects/rules.
Its search is a local inventory arrangement model, not a simulator or a sound world model.
"""
from collections import deque
import copy
import re


def quantities(text):
    return {name: float(number) for number, name in re.findall(r"(?:^|, )([0-9]+(?:\.[0-9]+)?) ([\w-]+)", text)}


def state_from_text(text):
    state = {"holding": None, "ground": None, "equipped": None, "location": None, "neighbors": []}
    for line in text.splitlines():
        if line.startswith("Current Location: "):
            state["location"] = line.removeprefix("Current Location: ").strip()
        for prefix, suffix, key in (("I am holding ", ".", "holding"),
                                    ("I have equipped ", ".", "equipped"),
                                    ("I see ", " near me.", "ground")):
            if line.startswith(prefix) and line.endswith(suffix):
                state[key] = quantities(line[len(prefix):-len(suffix)])
        if line.startswith("Neighboring areas: "):
            state["neighbors"] = line.removeprefix("Neighboring areas: ").rstrip(".").split(", ")
    return state


class PublicModel:
    def __init__(self):
        self.current = {}
        self.capacity_lower = 0
        self.capacity_upper = None
        self.capacity_evidence = []
        self.recipes = {}
        self.stations = {}
        self.containers = {}
        self.locations = {}
        self.edges = {}
        self.completed = []
        self.completion_reports = []
        self.known_tasks = []
        self.tasks = []
        self.inspected = []
        self.discovery_checks = []
        self.documents = {}
        self.source_lines = []
        self.seen_lines = set()
        self.last_action = None
        self.history = []
        self.failed_crafts = []

    def observe(self, text, last_action=None):
        previous = self.current
        if last_action and last_action.startswith("craft ") and re.search(r"Cannot craft", text):
            self.failed_crafts.append({"target": last_action.split()[-1], "location": previous.get("location"),
                "holding": previous.get("holding"), "equipped": previous.get("equipped"),
                "known_contents": {n: copy.deepcopy(b["items"]) for n,b in self.containers.items()},
                "feedback": next(line for line in text.splitlines() if "Cannot craft" in line)})
        state = state_from_text(text)
        self.current = state
        holding = state["holding"]
        if holding is not None:
            count = sum(holding.values())
            if self.capacity_upper is not None and count > self.capacity_upper:
                self.capacity_upper = None  # A changed capacity invalidates the old bound.
            self.capacity_lower = max(self.capacity_lower, count)
            rejected = re.search(r"Cannot (?:pick up|take out) [^\n]+, not enough space in hand\.", text)
            if rejected:
                self.capacity_upper = count if self.capacity_upper is None else min(count, self.capacity_upper)
                self.capacity_evidence.append(rejected.group(0))
        location = state["location"]
        if location and state["ground"] is not None:
            self.locations[location] = {"objects": state["ground"], "neighbors": state["neighbors"]}
        if (last_action and last_action.startswith("enter ") and previous.get("location") and location and
                location != previous["location"] and "I entered " in text):
            self.edges.setdefault(previous["location"], {})[last_action[6:]] = location
        tasks = re.findall(r"^\[\d+\] (.+)$", text, re.M)
        self.current["fresh_tasks"] = tasks
        if tasks:
            self.tasks = tasks
            self.known_tasks = list(dict.fromkeys(self.known_tasks + tasks))
        for goal in re.findall(r"^Stage completed: (.+)$", text, re.M):
            if goal not in self.completion_reports:
                self.completion_reports.append(goal)
        # The public interface sometimes truncates the task title. Resolve only a unique
        # sufficiently long prefix among titles actually observed, never a fuzzy semantic match.
        self.completed = []
        for report in self.completion_reports:
            candidates = [task for task in self.known_tasks if task == report or
                          (len(report) >= 24 and task.startswith(report))]
            if len(candidates) == 1:
                self.completed.append(candidates[0])
            elif not candidates:
                self.completed.append(report)
        self.tasks = [task for task in self.tasks if task not in self.completed]
        for line in text.splitlines():
            if "It can be used to craft:" in line:
                for target, parts in re.findall(r"([\w-]+) \(([^()]*)\)", line):
                    recipe = quantities(parts)
                    if recipe and all(n > 0 for n in recipe.values()):
                        self.recipes[target] = {"needs": recipe, "quote": line.strip()}
            missing = re.search(r"Cannot craft ([\w-]+)\. Missing necessary ([\w-]+) in the current area\.", line)
            if missing:
                self.stations[missing[1]] = {"name": missing[2], "quote": line}
            # Keep source evidence separate from model-written hypotheses.
            if (line.strip() and line not in self.seen_lines and not line.startswith(("Current Time:", "My health",
                    "My experience", "My attack", "My defense", "My level", "I am holding", "I see ",
                    "I have equipped", "Current Location:", "Neighboring areas:"))):
                self.source_lines.append(line)
                self.seen_lines.add(line)
        inspected = re.search(r"I inspected ([\w-]+):", text)
        if inspected:
            if inspected[1] not in self.inspected:
                self.inspected.append(inspected[1])
            contents = re.search(r"It contains: (.*?) \(capacity: ([\d.]+)/([\d.]+)\)\.", text)
            if contents:
                self.containers[inspected[1]] = {"items": quantities(contents[1]),
                    "used": float(contents[2]), "capacity": float(contents[3]), "quote": contents[0]}
            written = re.search(r"^It writes: (.*)$", text, re.M)
            if written:
                self.documents[inspected[1]] = {"text": written[1], "observed_at": len(self.history)}
            elif "nothing written" in text:
                self.documents[inspected[1]] = {"text": "", "observed_at": len(self.history)}
        # Explicit operation feedback updates only previously inspected container contents.
        for pattern, direction in ((r"I stored ([\d.]+) ([\w-]+) in ([\w-]+)\.", 1),
                                   (r"I took out ([\d.]+) ([\w-]+) from ([\w-]+)\.", -1)):
            match = re.search(pattern, text)
            if match and match[3] in self.containers:
                bag = self.containers[match[3]]
                bag["items"][match[2]] = max(0, bag["items"].get(match[2], 0) + direction * float(match[1]))
                bag["used"] = max(0, bag["used"] + direction * float(match[1]))
        if re.search(r"I successfully crafted ", text):
            # Without an explicit consumption location, old container counts may be stale.
            for bag in self.containers.values():
                bag["uncertain_after_craft"] = True
        if last_action and last_action.startswith("write "):
            name = last_action.rsplit(" ", 1)[-1]
            self.documents.pop(name, None)  # Command acceptance does not expose full final text.
        self.last_action = last_action
        self.history.append({"action": last_action, "location": location})

    @property
    def hand_capacity(self):
        return self.capacity_upper if self.capacity_upper == self.capacity_lower else None

    def view(self):
        return {"current": self.current, "hand_capacity": self.hand_capacity,
                "capacity_bounds": [self.capacity_lower, self.capacity_upper],
                "capacity_evidence": self.capacity_evidence[-2:], "recipes": self.recipes,
                "stations": self.stations, "containers": self.containers, "documents": self.documents,
                "tasks": self.tasks, "completed": self.completed, "failed_crafts": self.failed_crafts[-3:],
                "last_observed_locations_not_guaranteed_current": self.locations,
                "previously_successful_directed_routes": self.edges}

    def predicate(self, condition):
        """Three-valued evaluation of a proposed condition, NOT task success."""
        kind = condition.get("kind")
        item, value = condition.get("item"), condition.get("value")
        if kind == "held":
            inventory = self.current.get("holding")
            try:
                return None if inventory is None else inventory.get(item, 0) >= float(condition.get("count", 1))
            except (TypeError, ValueError):
                return None
        if kind == "at":
            loc = self.current.get("location")
            return None if loc is None else value in (loc, loc.split(", ")[-1])
        if kind in ("text_equals", "text_contains"):
            doc = self.documents.get(item)
            # A historical inspection is not a current observation of a mutable document.
            if not doc or doc["observed_at"] != len(self.history) - 1 or not isinstance(value, str):
                return None
            return doc["text"] == value if kind == "text_equals" else value in doc["text"]
        if kind == "reported":
            return True if value in self.completed else (False if value in self.current.get("fresh_tasks", []) else None)
        return None

    def check_action(self, action):
        """Reject only simple contradictions with current parsed observations."""
        h = self.current.get("holding")
        cap = self.hand_capacity
        if action.startswith("pick up ") and h is not None and cap is not None and sum(h.values()) + 1 > cap:
            return {"status": "contradicted", "reason": "pickup exceeds observed hand capacity",
                    "holding_count": sum(h.values()), "capacity": cap}
        if action.startswith("enter ") and self.current.get("neighbors"):
            target = action[6:]
            if target not in self.current["neighbors"]:
                return {"status": "contradicted", "reason": "destination is absent from current adjacent areas"}
        return {"status": "unknown", "reason": "no contradiction established; success is not guaranteed"}

    def route(self, target):
        start = self.current.get("location")
        queue = deque([(start, [])])
        seen = {start}
        while queue:
            node, path = queue.popleft()
            if node and target in (node, node.split(", ")[-1]):
                return path
            for action_target, dest in self.edges.get(node, {}).items():
                if dest not in seen:
                    seen.add(dest)
                    queue.append((dest, path + ["enter " + action_target]))
        return None

    def arrange(self, target, max_nodes=12000):
        """Find a small joint arrangement; execute only its first action, then observe again.

        Storage/crafting semantics beyond public quantities remain an explicit hypothesis.
        The planned craft is an environment experiment if bag accessibility is unverified.
        """
        s = self.current
        if s.get("holding") is None or s.get("ground") is None:
            return {"status": "unknown", "reason": "current inventory/ground not observable"}
        if s["holding"].get(target, 0) >= 1:
            return {"status": "arrangement_observed", "plan": []}
        if s["ground"].get(target, 0) >= 1 and (self.hand_capacity is None or sum(s["holding"].values()) < self.hand_capacity):
            return {"status": "candidate", "plan": ["pick up " + target]}
        recipe = self.recipes.get(target)
        if not recipe or self.hand_capacity is None:
            return {"status": "unknown", "reason": "recipe or exact hand capacity not yet observed"}
        station = self.stations.get(target, {}).get("name")
        if station and not s["ground"].get(station):
            options = [self.route(loc) for loc, data in self.locations.items() if data["objects"].get(station)]
            options = [p for p in options if p]
            if options:
                return {"status": "candidate", "plan": min(options, key=len), "assumption": "previously traversed route remains open"}
            return {"status": "unknown", "reason": "observed station absent; route unknown"}
        needs = recipe["needs"]
        equipped_now = s.get("equipped") or {}
        bags = {name: b for name, b in self.containers.items() if not b.get("uncertain_after_craft") and
                (s["holding"].get(name) or equipped_now.get(name) or s["ground"].get(name))}
        # Search one observed container at a time, including the no-container model.
        candidates = []
        for bagname in [None] + list(bags):
            bag = bags.get(bagname, {"items": {}, "used": 0, "capacity": 0})
            names = sorted(set(needs) | set(s["holding"]) | ({bagname} if bagname else set()))
            def vector(d): return tuple(d.get(name, 0) for name in names)
            h0, g0, b0 = vector(s["holding"]), vector(s["ground"]), vector(bag["items"])
            e0 = bool(bagname and equipped_now.get(bagname))
            start = (h0, g0, b0, e0)
            queue, seen = deque([(start, [])]), {start}
            while queue and len(seen) <= max_nodes:
                (h, g, b, equipped), path = queue.popleft()
                attached = equipped or bool(bagname and h[names.index(bagname)] > 0)
                proposed_h = {name:n for name,n in zip(names,h) if n}
                proposed_e = {**equipped_now, **({bagname:1.0} if equipped else {})}
                proposed_contents = {n: copy.deepcopy(v["items"]) for n,v in self.containers.items()}
                if bagname:
                    proposed_contents[bagname].update({name:n for name,n in zip(names,b)})
                def clean(d): return {k:v for k,v in (d or {}).items() if v}
                failed = any(f["target"] == target and f["location"] == s["location"] and
                    clean(f["holding"]) == proposed_h and clean(f["equipped"]) == clean(proposed_e) and
                    all(clean(f["known_contents"].get(n)) == clean(v) for n,v in proposed_contents.items())
                    for f in self.failed_crafts)
                if not failed and all(h[names.index(item)] + (b[names.index(item)] if attached else 0) >= count for item, count in needs.items()):
                    candidates.append({"status": "candidate", "plan": path + [f"craft 1 {target}"],
                        "assumption": "crafting accepts these carried inputs; unverified until actual execution",
                        "required": needs, "capacity": self.hand_capacity, "container": bagname,
                        "search_nodes": len(seen)})
                    break
                if len(path) >= 9:
                    continue
                options = []
                for i, name in enumerate(names):
                    if g[i] >= 1 and sum(h) + 1 <= self.hand_capacity and (name in needs or name == bagname):
                        hh, gg = list(h), list(g); hh[i] += 1; gg[i] -= 1
                        options.append(((tuple(hh), tuple(gg), b, equipped), "pick up " + name))
                    if h[i] >= 1:
                        hh, gg = list(h), list(g); hh[i] -= 1; gg[i] += 1
                        options.append(((tuple(hh), tuple(gg), b, equipped), "drop " + name))
                        if bagname and name != bagname and attached and bag["used"] - sum(b0) + sum(b) + 1 <= bag["capacity"]:
                            hh, bb = list(h), list(b); hh[i] -= 1; bb[i] += 1
                            options.append(((tuple(hh), g, tuple(bb), equipped), f"store 1 {name} {bagname}"))
                        if name == bagname and not equipped and not equipped_now:
                            hh = list(h); hh[i] -= 1
                            options.append(((tuple(hh), g, b, True), "equip " + name))
                for successor, action in options:
                    if successor not in seen:
                        seen.add(successor)
                        queue.append((successor, path + [action]))
        if candidates:
            return min(candidates, key=lambda c: len(c["plan"]))
        conflict = sum(needs.values()) > self.hand_capacity
        if conflict:
            # Search failure identifies the missing affordance: more carried capacity. Acquire
            # object attributes through the public inspect interface, at most six queries per
            # target recipe. This does not assume that an uninspected object is a container.
            tried = [x for x in self.discovery_checks if x["target"] == target]
            unknown_objects = [name for name in s["ground"] if name not in needs and name != station and
                               name not in self.inspected and name not in bags]
            if unknown_objects and len(tried) < 6:
                item = unknown_objects[0]
                # Count emitted inspection proposals; the next call checks real feedback.
                self.discovery_checks.append({"target":target, "item":item})
                return {"status":"capacity_discovery", "plan":["inspect " + item],
                        "required":needs, "hand_capacity":self.hand_capacity,
                        "assumption":"unknown object may expose a capacity affordance; observation required"}
        return {"status": "unknown", "reason": "no arrangement within local observed inventory/search bound",
                "required": needs, "hand_capacity": self.hand_capacity,
                "hand_only_conflict": conflict}
