"""Modules B and D: scoped evidence, contradiction updates and bounded retry."""
from dataclasses import dataclass, field, asdict

from scar.io import digest
from .state import action_key


@dataclass
class FailureRule:
    id: str
    action: str
    key: str
    conditions: dict
    cause: str
    evidence: list
    candidates: list
    confidence: float
    scope: str
    last_step: int
    failures: int = 1
    successes: int = 0
    status: str = "active"
    probes: int = 0


class FailureMemory:
    def __init__(self, cooldown=8, max_rules=256, threshold=0.75):
        self.cooldown, self.max_rules, self.threshold = cooldown, max_rules, threshold
        self.rules = []

    def learn(self, event):
        rule_id = digest([event.action_key, event.conditions, event.cause])[:16]
        existing = next((r for r in self.rules if r.id == rule_id), None)
        if existing:
            existing.failures += 1
            existing.confidence = min(0.98, existing.confidence + 0.08)
            existing.last_step = event.step
            existing.status = "active"
            if event.feedback not in existing.evidence:
                existing.evidence = (existing.evidence + [event.feedback])[-4:]
            return existing
        rule = FailureRule(rule_id, event.action, event.action_key, event.conditions, event.cause,
                           [event.feedback], event.recovery_candidates, event.confidence,
                           event.location, event.step)
        self.rules.append(rule)
        if len(self.rules) > self.max_rules:
            self.rules.sort(key=lambda r: (r.status == "active", r.last_step))
            self.rules.pop(0)
        return rule

    @staticmethod
    def matches(rule, state):
        return all(state.fields.get(k) == v for k, v in rule.conditions.items())

    def retrieve(self, action, state):
        return sorted([r for r in self.rules if r.key == action_key(action)],
                      key=lambda r: (self.matches(r, state), r.confidence, r.last_step), reverse=True)

    def assess(self, action, state):
        for rule in self.retrieve(action, state):
            if rule.status == "contradicted" or not self.matches(rule, state):
                continue
            age = state.step - rule.last_step
            if age >= self.cooldown:
                return "probe", rule
            if rule.confidence >= self.threshold:
                return "block", rule
            return "uncertain", rule
        return "allow", None

    def revise(self, action, before, after, failed):
        updates = []
        for rule in self.retrieve(action, before):
            if failed:
                continue
            # Absence of an error alone is insufficient evidence of success.
            changed = before.fields != after.fields
            explicit = any(word in after.feedback.lower() for word in
                           ("entered ", "picked up ", "crafted ", "equipped ", "took out ", "stored ", "unlocked "))
            if not (changed or explicit):
                continue
            rule.successes += 1
            if self.matches(rule, before):
                rule.confidence *= 0.35
                rule.status = "contradicted"
                updates.append({"event": "rule_contradicted", "rule": rule.id})
            else:
                rule.status = "conditional_success"
                updates.append({"event": "safe_retry_success", "rule": rule.id})
        return updates

    def to_dict(self):
        return {"cooldown": self.cooldown, "max_rules": self.max_rules,
                "threshold": self.threshold, "rules": [asdict(r) for r in self.rules]}

    @classmethod
    def from_dict(cls, data):
        result = cls(data["cooldown"], data["max_rules"], data["threshold"])
        result.rules = [FailureRule(**r) for r in data["rules"]]
        return result
