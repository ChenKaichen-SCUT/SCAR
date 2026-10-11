"""Module A: conservative deterministic diagnosis from public feedback."""
import re
from dataclasses import dataclass, asdict

from .state import VisibleState, action_key


@dataclass
class FailureEvent:
    action: str
    action_key: str
    goal: str
    step: int
    location: str
    before: dict
    feedback: str
    cause: str
    conditions: dict
    confidence: float
    retry_worthwhile: bool
    recovery_candidates: list

    def to_dict(self):
        return asdict(self)


FAILURE = re.compile(
    r"\b(?:cannot|can't|could not|failed to|invalid action|invalid amount|not enough|"
    r"not found|does not exist|do not have|don't have|not holding|must be|"
    r"needs to be equipped|no inventory found|nothing happens|unable to)\b", re.I)


def diagnose(action: str, before: VisibleState, after: VisibleState):
    feedback = after.feedback
    if not FAILURE.search(feedback):
        return None
    cause, keys, confidence = "unknown", list(before.fields), 0.45
    if re.search(r"blocked the way out|during combat|in combat", feedback, re.I):
        cause, keys, confidence = "combat_block", ["location", "npcs", "combat"], 0.85
    elif re.search(r"space in hand", feedback, re.I):
        cause, keys, confidence = "hands_full", ["hands"], 0.90
    elif re.search(r"locked", feedback, re.I):
        cause, keys, confidence = "locked", ["location", "hands", "equipment", "inventory_evidence"], 0.80
    elif re.search(r"ingredients|missing necessary|not enough|do not have|don't have|no inventory|needs to be equipped", feedback, re.I):
        cause, keys, confidence = "missing_resource", ["location", "hands", "equipment", "objects", "inventory_evidence"], 0.80
    elif re.search(r"not found|no path|not (?:here|nearby)|does not exist", feedback, re.I):
        cause, keys, confidence = "target_unavailable", ["location", "objects", "npcs", "neighbors"], 0.85
    elif re.search(r"invalid action|failed to parse|invalid amount", feedback, re.I):
        cause, keys, confidence = "syntax", ["location"], 0.90
    conditions = {key: before.fields.get(key) for key in keys}
    # Feedback can establish a fact that was unknown immediately before the action.
    if cause == "combat_block":
        conditions["combat"] = "active"
    return FailureEvent(action, action_key(action), before.fields.get("goal", "advance the current task"),
                        before.step, before.fields.get("location", "unknown"), dict(before.fields),
                        feedback, cause, conditions, confidence, True, [])
