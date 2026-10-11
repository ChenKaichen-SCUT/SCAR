"""Auditable action value comparison, independent from candidate generation."""
from dataclasses import dataclass, asdict
import re

from scar_v3.state import Truth, parse_action


@dataclass
class ActionValue:
    action: str
    allowed: bool
    probability_of_success: float
    task_relevance: float
    expected_condition_progress: float
    information_value: float
    evidence_confidence: float
    uncertainty: float
    extra_call_cost: float
    value: float
    support: list
    prediction: dict

    def to_dict(self):
        return asdict(self)


def relevance(action, goal, state):
    a, g = parse_action(action), parse_action(goal)
    if a == g:
        return 1.0
    if a.target and a.target == g.target:
        return .85
    if a.target in state.recipes.get(g.target, []):
        return .8
    return .1


def affordance(action, state):
    """Weak public-semantic prior, explicitly distinguished from learned evidence."""
    a = parse_action(action)
    features = state.features(action)
    required = {"drop": ["target.held"], "pick up": ["target.ground", "hands.space"],
                "take out": ["container.accessible", "container.has_target", "hands.space"]}.get(a.verb, [])
    if required and all(features[k].truth == Truth.TRUE for k in required):
        return .2, .8, ["public_action_description_and_observed_arguments"]
    if a.verb == "inspect" and (a.target in (state.ground or {}) or a.target in (state.hands or {}) or a.target in state.containers):
        return .2, .8, ["observed_inspectable_target"]
    return .5, 0, []


def condition_effect(action, goal_prediction, state):
    a = parse_action(action)
    violated = set(goal_prediction.violated)
    if "hands.space" in violated and a.verb == "drop" and state.hands and a.target in state.hands:
        return .9, ["public_drop_effect_on_hand_count"]
    if "hands.space" in violated and a.verb == "equip" and state.hands and a.target in state.hands and re.search(r"bag|pouch|satchel|pack", a.target):
        return .75, ["public_container_equip_effect"]
    if a.verb in {"pick up", "take out", "buy"} and any(k.startswith("resource:" + a.target + ">=") for k in violated):
        return .8, ["acquiring_a_measured_missing_resource"]
    return 0, []


class Selector:
    def __init__(self, margin=.2):
        self.margin = margin
        self.outcomes = {}

    def score(self, action, goal, state, learner, syntax_ok, extra_call_cost=0, switching=False):
        predicted = learner.predict(action, state)
        probability, confidence, support = predicted.failure_probability, predicted.confidence, list(predicted.support)
        if predicted.status == "UNKNOWN":
            prior, known, provenance = affordance(action, state)
            if known:
                probability, confidence = prior, known
                support += provenance
        a = parse_action(action)
        target_prediction = learner.predict(goal, state) if goal else predicted
        progress, effect_support = condition_effect(action, target_prediction, state)
        support += effect_support
        history = self.outcomes.get(a.verb, {"beneficial": 0, "other": 0})
        empirical = (history["beneficial"] + 1) / (history["beneficial"] + history["other"] + 2)
        progress *= .5 + .5 * empirical
        informative = a.verb == "inspect" and bool(target_prediction.unknown or target_prediction.status == "UNKNOWN")
        information = .6 if informative and confidence >= .7 else 0
        rel = relevance(action, goal, state) if goal else .5
        # No LLM-produced probability or progress score is trusted here.
        uncertainty = 1-confidence
        value = (1-probability) * (.7*rel + .7*progress + .3*information) - .8*probability - .35*uncertainty
        value -= .08*extra_call_cost + (.15 if switching else 0)
        if not syntax_ok:
            probability, value = 1.0, -2.0
        return ActionValue(action, syntax_ok, 1-probability, rel, progress, information, confidence,
                           uncertainty, extra_call_cost, value, support, predicted.to_dict())

    def choose(self, base, candidates):
        eligible = [c for c in candidates if c.allowed and c.value-base.value > self.margin
                    and c.evidence_confidence >= .65
                    and (c.expected_condition_progress > 0 or c.task_relevance >= .8 or c.information_value > 0)]
        if not eligible:
            return base, "insufficient_evidence_of_net_benefit"
        best = max(eligible, key=lambda c: (c.value, c.action))
        return best, "evidence_supported_net_benefit"

    def update(self, action, successful, condition_improved):
        if successful is None:
            return
        row = self.outcomes.setdefault(parse_action(action).verb, {"beneficial": 0, "other": 0})
        row["beneficial" if successful and condition_improved else "other"] += 1
