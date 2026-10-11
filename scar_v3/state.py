"""Public-observation predicates with explicit unknowns and evidence provenance.

No imports from the environment, world definitions, scoring or dataset builders.
Transient absent fields are never filled from old observations. Container facts
persist only while their public access and mutation provenance remain valid.
"""
from dataclasses import dataclass, field, asdict
from enum import Enum
import re
import shlex

from scar.io import digest
from scar.agents.scar.state import feedback_text


class Truth(str, Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"


def tri(value):
    return Truth.UNKNOWN if value is None else Truth.TRUE if value else Truth.FALSE


def conjunction(values):
    values = list(values)
    if Truth.FALSE in values:
        return Truth.FALSE
    return Truth.UNKNOWN if not values or Truth.UNKNOWN in values else Truth.TRUE


@dataclass
class Evidence:
    truth: Truth = Truth.UNKNOWN
    source: str = "missing_observation"
    step: int = -1
    confidence: float = 0.0
    scope: str = "current_observation"
    dependencies: tuple = ()

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class Action:
    verb: str
    args: tuple
    target: str

    @property
    def schema(self):
        # Recipe, requested quantity and target identity cannot be pooled blindly.
        return digest([self.verb, self.args])[:20]


def parse_action(action):
    try:
        parts = shlex.split(action)
    except ValueError:
        return Action("invalid", (), "")
    if not parts:
        return Action("invalid", (), "")
    verbs = {"pick up", "take out", "talk to", "invoke law", "file objection", "appeal verdict"}
    first = " ".join(parts[:2])
    verb, args = (first, tuple(parts[2:])) if first in verbs else (parts[0], tuple(parts[1:]))
    index = 1 if verb in {"craft", "buy", "sell", "store", "discard"} else 0
    return Action(verb, args, args[index] if len(args) > index else "")


def parse_counts(text):
    if text is None:
        return None
    text = text.strip().rstrip(".")
    if text.lower() in {"nothing", "no objects", "none"}:
        return {}
    result = {}
    for part in text.split(", "):
        match = re.fullmatch(r"(\d+(?:\.\d+)?) (.+)", part.strip())
        if not match:
            return None  # An unparsed field supplies no negative evidence.
        result[match[2]] = float(match[1])
    return result


@dataclass
class PublicState:
    step: int = 0
    location: str | None = None
    hands: dict | None = None
    equipment: dict | None = None
    ground: dict | None = None
    npcs: list | None = None
    neighbors: list | None = None
    containers: dict = field(default_factory=dict)
    recipes: dict = field(default_factory=dict)
    combat: Evidence = field(default_factory=Evidence)
    goal: str | None = None
    feedback: str = ""

    @classmethod
    def observe(cls, obs, previous=None, action=None):
        text, step = obs["text"], int(obs.get("step", 0))
        state = cls(step=step, feedback=feedback_text(text))
        def match(pattern):
            found = re.search(pattern, text)
            return found[1].strip().rstrip(".") if found else None
        state.location = match(r"Current Location: ([^\n]+)")
        state.hands = parse_counts(match(r"I am holding ([^\n]+)"))
        state.equipment = parse_counts(match(r"I have equipped ([^\n]+)"))
        state.ground = parse_counts(match(r"I see ([^\n]+) near me\."))
        for key, pattern, empty in [("npcs", r"I see ([^\n]+) nearby\.", "no one"),
                                    ("neighbors", r"Neighboring areas: ([^\n]+)", "no neighboring areas")]:
            value = match(pattern)
            setattr(state, key, None if value is None else [] if value == empty else value.split(", "))
        if previous:
            state.recipes = {k: list(v) for k, v in previous.recipes.items()}
            state.goal = previous.goal
            # Contents persist as memory, but access is separately tri-valued.
            state.containers = {k: dict(v) for k, v in previous.containers.items()}
            # No time-based assumption that a previously blocked exit is now safe.
            if state.location == previous.location and previous.combat.truth == Truth.FALSE:
                state.combat = previous.combat
        public_goal = re.findall(r"(?:Required action:|Your (?:task|goal) is|Objective:)\s*([^\n]+)", state.feedback, re.I)
        if public_goal:
            state.goal = public_goal[-1].strip(" `.")
        if re.search(r"blocked the way out|in combat|is attacking|attacked .+lost", state.feedback, re.I):
            state.combat = Evidence(Truth.FALSE, "public_combat_feedback", step, .95, state.location or "unknown", ("location", "combat"))
        elif state.npcs == []:
            state.combat = Evidence(Truth.TRUE, "observed_no_npcs", step, .95, state.location or "unknown", ("npcs",))
        elif re.search(r"combat (?:has )?ended|no longer in combat", state.feedback, re.I):
            state.combat = Evidence(Truth.TRUE, "explicit_combat_end", step, .95, state.location or "unknown", ("combat",))
        elif re.search(r"defeated|killed", state.feedback, re.I):
            # One defeated enemy does not establish that every enemy is gone.
            state.combat = Evidence()
        if action:
            parsed = parse_action(action)
            # Container mutation invalidates old counts, even when success is unclear.
            if parsed.verb in {"store", "discard", "take out"} and parsed.args:
                state.containers.pop(parsed.args[-1], None)
            if parsed.verb in {"craft", "buy", "sell", "eat", "disassemble"}:
                state.containers.clear()
            if parsed.verb == "inspect":
                contents = re.search(r"It contains: (.*?) \(capacity:", state.feedback)
                if contents and (counts := parse_counts(contents[1])) is not None:
                    state.containers[parsed.target] = {"counts": counts, "step": step, "source": "container_inspection", "location": state.location}
                for recipe, ingredients in re.findall(r"([\w-]+) \(made of ([^)]+)\)", state.feedback):
                    state.recipes[recipe] = [x.strip() for x in ingredients.split(",")]
        return state

    def _fact(self, value, source, *deps):
        return Evidence(tri(value), source if value is not None else "missing_observation", self.step,
                        .95 if value is not None else 0, self.location or "unknown", deps)

    def count_fact(self, collection, name, amount=1):
        values = getattr(self, collection)
        return self._fact(None if values is None else values.get(name, 0) >= amount,
                          "observation:" + collection, collection + ":" + name)

    def accessible_count(self, name, minimum=1):
        if self.hands is None or self.equipment is None:
            return None
        total = self.hands.get(name, 0) + self.equipment.get(name, 0)
        # Unknown contents of a possible held/equipped container prevent a negative claim.
        known_containers = set(self.containers)
        possible = {n for n in self.hands | self.equipment if re.search(r"bag|pouch|satchel|pack|container", n)}
        for container, info in self.containers.items():
            accessible = container in self.hands or container in self.equipment or container == "inventory" and bool(self.equipment)
            if accessible:
                total += info["counts"].get(name, 0)
        unknown = possible - known_containers
        if "inventory" in known_containers:
            unknown -= set(self.equipment)
        if unknown and total < minimum:
            return None
        return total

    def features(self, action, extra=()):
        a = parse_action(action)
        facts = {}
        def add(key, fact):
            facts[key] = fact
        if a.verb in {"pick up", "take out", "unequip", "buy"}:
            # Public game interaction model: two hand slots. This is a state feature,
            # not a pre-installed prohibition; necessity is learned from experience.
            add("hands.space", self._fact(None if self.hands is None else sum(self.hands.values()) < 2,
                                         "observation:hand_count", "hands"))
        if a.verb == "enter":
            add("combat.clear", self.combat)
            add("target.neighbor", self._fact(None if self.neighbors is None else a.target in self.neighbors, "observation:neighbors", "neighbors:" + a.target))
            n = self.accessible_count("key")
            add("resource:key>=1", self._fact(None if n is None else n >= 1, "public_possession", "key"))
        if a.verb in {"pick up", "inspect", "store"}:
            add("target.ground", self.count_fact("ground", a.target))
        if a.verb in {"drop", "equip", "throw", "eat", "inspect", "store"}:
            add("target.held", self.count_fact("hands", a.target))
        if a.verb == "unequip":
            add("target.equipped", self.count_fact("equipment", a.target))
        if a.verb in {"attack", "talk to", "buy", "sell", "throw"}:
            npc = a.args[-1] if a.verb in {"buy", "sell", "throw"} and a.args else a.target
            add("target.npc", self._fact(None if self.npcs is None else npc in self.npcs, "observation:npcs", "npcs:" + npc))
        if a.verb in {"store", "take out", "discard"} and a.args:
            container = a.args[-1]
            if container == "inventory":
                visible = None if self.equipment is None else any(re.search(r"bag|pouch|satchel|pack", n) for n in self.equipment)
            elif self.hands is None or self.ground is None or self.equipment is None:
                visible = True if any(container in (x or {}) for x in [self.hands, self.ground, self.equipment]) else None
            else:
                visible = container in self.hands or container in self.ground or container in self.equipment
            add("container.accessible", self._fact(visible, "observation:container", container))
            stored = self.containers.get(container)
            add("container.has_target", Evidence(tri(stored["counts"].get(a.target, 0) >= 1 if stored and visible else None),
                                                  stored["source"] if stored else "missing_inspection", stored["step"] if stored else self.step,
                                                  .95 if stored and visible else 0, container, ("container:" + container,)))
        # Only publicly discovered recipe ingredients and learned dependencies are used.
        keys = set(extra)
        if a.verb == "craft":
            keys.update("ground:" + n for n in ["workbench", "furnace"])
            for material in self.recipes.get(a.target, []):
                keys.update(f"resource:{material}>={q}" for q in [.5, 1, 2, 3, 4, 5, 6, 8])
        for key in sorted(keys):
            if key in facts:
                continue
            if key.startswith("ground:"):
                add(key, self.count_fact("ground", key[7:]))
            elif key.startswith("resource:"):
                name, amount = key[9:].rsplit(">=", 1)
                count = self.accessible_count(name, float(amount))
                add(key, self._fact(None if count is None else count >= float(amount), "public_possession", name))
            elif key.startswith("at:"):
                add(key, self._fact(None if self.location is None else self.location == key[3:], "observation:location", "location"))
            else:
                add(key, Evidence())
        return facts

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        data = dict(data)
        data["combat"] = Evidence(**data["combat"])
        return cls(**data)


def match_conditions(conditions, facts):
    values = []
    for key, expected in conditions.items():
        observed = facts.get(key, Evidence()).truth
        if expected is None or expected == Truth.UNKNOWN or observed == Truth.UNKNOWN:
            values.append(Truth.UNKNOWN)
        else:
            values.append(Truth.TRUE if observed == expected else Truth.FALSE)
    return conjunction(values)
