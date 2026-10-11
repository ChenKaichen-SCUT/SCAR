"""Observation-only state estimation. No world, engine flags or valid-action oracle."""
import re
import shlex
from dataclasses import dataclass, field

from scar.io import digest


def action_key(action):
    try:
        return " ".join(shlex.split(action)).casefold()
    except ValueError:
        return " ".join(action.split()).casefold()


def feedback_text(text):
    # Engine feedback occurs between Current Location and the public status block.
    match = re.search(r"Current Location:[^\n]*\n(.*?)(?:\nI am holding |\nMy level is |\Z)", text, re.S)
    return (match.group(1) if match else text).strip()


@dataclass
class VisibleState:
    fields: dict = field(default_factory=dict)
    step: int = 0
    feedback: str = ""

    @property
    def fingerprint(self):
        return digest(self.fields)

    @classmethod
    def observe(cls, obs, previous=None):
        text = obs["text"]
        # Only persist deliberately remembered facts; refresh directly visible fields.
        fields = {k: v for k, v in (previous.fields if previous else {}).items()
                  if k in {"combat", "inventory_evidence", "goal"}}
        patterns = {
            "location": r"Current Location: ([^\n]+)",
            "hands": r"I am holding ([^\n]+)",
            "equipment": r"I have equipped ([^\n]+)",
            "objects": r"I see ([^\n]+) near me\.",
            "npcs": r"I see ([^\n]+) nearby\.",
            "neighbors": r"Neighboring areas: ([^\n]+)",
        }
        for key, pattern in patterns.items():
            match = re.search(pattern, text)
            if match:
                fields[key] = match.group(1).strip()
        feedback = feedback_text(text)
        if re.search(r"blocked the way out|in combat|attacks? (?:me|you)|attacked (?:me|you)", feedback, re.I):
            fields["combat"] = "active"
        if re.search(r"combat (?:has )?ended|no longer in combat|(?:killed|defeated) .+|.+ (?:was|is) defeated", feedback, re.I):
            # May be multiple enemies: a change is evidence for retry, not certainty.
            fields["combat"] = "possibly_ended"
        if previous and fields.get("location") != previous.fields.get("location"):
            fields.pop("combat", None)
        inventory = re.search(r"(?:inventory|container) (?:contains|contents)[^\n]*", feedback, re.I)
        if inventory:
            fields["inventory_evidence"] = inventory.group(0)
        # Changes caused by inventory actions are observable even when no contents listed.
        if re.search(r"(?:stored|took out|crafted|bought|sold|consumed) ", feedback, re.I):
            fields["inventory_evidence"] = feedback
        goals = re.findall(r"[^\n]*(?:your (?:task|goal)|objective|quest:|next task)[^\n]*", feedback, re.I)
        if goals:
            fields["goal"] = goals[-1]
        return cls(fields, int(obs.get("step", 0)), feedback)
