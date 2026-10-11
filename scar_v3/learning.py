"""Contrastive online induction of necessary conjunctions under missing values.

For each schema, a literal is admissible iff at least one known success satisfies
it and no known success contradicts it. Each failure supplies a disjunction of
admissible literals it violates. We maintain minimum-cardinality hitting sets of
those disjunctions (up to four literals), i.e. a bounded version space. Unknown
observations neither satisfy nor contradict a literal. Unsupported failures are
explicitly counted as unexplained, never silently imputed.
"""
from dataclasses import dataclass, asdict, field
from itertools import combinations
import re

from scar.io import digest
from scar_v3.state import Truth, Evidence, PublicState, conjunction, parse_action


def public_outcome(action, before, after):
    a = parse_action(action)
    text = after.feedback
    # Use action-addressed public feedback rather than hidden engine flags.
    if re.search(r"Invalid action|Invalid amount|failed to parse", text, re.I):
        return False
    if re.search(r"(?:Cannot|Can't|Could not) (?:" + re.escape(a.verb) + r"|find)\b", text, re.I):
        return False
    if a.verb == "enter" and before.location and after.location and before.location != after.location:
        return True
    past = {"pick up": "picked up", "drop": "dropped", "equip": "equipped", "unequip": "unequipped",
            "take out": "took out", "store": "stored", "craft": "(?:successfully )?crafted", "inspect": "inspected",
            "buy": "bought", "sell": "sold", "eat": "ate", "attack": "attacked", "talk to": "talked to",
            "discard": "discarded", "write": "wrote", "lockpick": "(?:unlocked|lockpicked)"}
    phrase = past.get(a.verb)
    if phrase and re.search(r"\b(?:I|You) " + phrase + r"\b", text, re.I):
        return True
    return None  # Absence of an error does not become a positive label.


@dataclass
class Prediction:
    status: str = "UNKNOWN"
    failure_probability: float = .5
    confidence: float = 0.0
    permission: str = "attempt_permitted"
    violated: list = field(default_factory=list)
    unknown: list = field(default_factory=list)
    rules: list = field(default_factory=list)
    support: list = field(default_factory=list)
    hypotheses: list = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


class PreconditionLearner:
    def __init__(self, max_samples=64, max_models=128, max_literals=4):
        self.max_samples, self.max_models, self.max_literals = max_samples, max_models, max_literals
        self.models = {}
        self.feedback_rules = {}
        self.required_keys = {}
        self.events = []
        self.sequence = 0

    @staticmethod
    def keys(action):
        a = parse_action(action)
        return ["specific:" + a.schema, "verb:" + a.verb]

    def features(self, action, state):
        facts = state.features(action, self.required_keys.get(parse_action(action).schema, []))
        deps = [v for k, v in facts.items() if k in self.required_keys.get(parse_action(action).schema, []) and k.startswith("ground:")]
        facts["workstations.present"] = Evidence(conjunction([d.truth for d in deps]), "learned_dependencies_and_current_observation",
                                                 state.step, min([d.confidence for d in deps], default=0), state.location or "unknown")
        return facts

    def _refit(self, model):
        samples = model["samples"]
        positives = [s for s in samples if s["success"]]
        negatives = [s for s in samples if not s["success"]]
        features = sorted({k for s in samples for k in s["facts"]})
        literals = []
        for key in features:
            observed_successes = [s["facts"].get(key, Truth.UNKNOWN) for s in positives]
            known = [v for v in observed_successes if v != Truth.UNKNOWN]
            if not known or len(set(known)) != 1:
                continue
            expected = known[0]
            mask = sum(1 << i for i, s in enumerate(negatives)
                       if s["facts"].get(key, Truth.UNKNOWN) not in {Truth.UNKNOWN, expected})
            if mask:
                literals.append((key, expected, mask, len(known)))
        literals.sort(key=lambda x: (-x[2].bit_count(), -x[3], x[0], x[1]))
        # Fixed computational bound, logged with the rule; not a tuned test setting.
        truncated = len(literals) > 20
        literals = literals[:20]
        target = 0
        for _, _, mask, _ in literals:
            target |= mask
        hypotheses = []
        if target:
            for size in range(1, min(self.max_literals, len(literals)) + 1):
                for chosen in combinations(literals, size):
                    union = 0
                    for _, _, mask, _ in chosen:
                        union |= mask
                    if union == target:
                        hypotheses.append({k: v for k, v, _, _ in chosen})
                        if len(hypotheses) >= 128:
                            break
                if hypotheses:
                    break
        changed = hypotheses != model.get("hypotheses", [])
        model.update(hypotheses=hypotheses, unexplained_failures=len(negatives)-target.bit_count(),
                     candidate_limit_reached=truncated, positive_samples=len(positives), negative_samples=len(negatives))
        if changed:
            model["version"] += 1
        return changed

    def predict(self, action, state):
        keys = self.keys(action)
        facts = self.features(action, state)
        result = Prediction()
        votes, support = [], []
        for key in keys:
            model = self.models.get(key)
            if not model:
                continue
            for hypothesis in model.get("hypotheses", []):
                evaluations = []
                for name, expected in hypothesis.items():
                    actual = facts.get(name, Evidence()).truth
                    evaluations.append(Truth.UNKNOWN if actual == Truth.UNKNOWN else Truth.TRUE if actual == expected else Truth.FALSE)
                    if actual == Truth.UNKNOWN:
                        result.unknown.append(name)
                    elif actual != expected:
                        result.violated.append(name)
                votes.append(conjunction(evaluations))
                result.hypotheses.append({"model": key, "version": model["version"], "conditions": hypothesis})
            if model.get("hypotheses"):
                support += [s["id"] for s in model["samples"]]
        for rid, rule in self.feedback_rules.items():
            if rule["scope"] not in keys or rule["status"] != "active":
                continue
            fact = facts.get(rule["predicate"], Evidence())
            result.rules.append(rid)
            if fact.truth == Truth.UNKNOWN:
                result.unknown.append(rule["predicate"])
            elif fact.truth != rule["expected"]:
                result.violated.append(rule["predicate"])
                result.status = "REJECT"
                result.confidence = max(result.confidence, rule["confidence"] * fact.confidence)
                result.failure_probability = max(result.failure_probability, rule["confidence"])
                support += rule["support"]
        if votes and all(v == Truth.FALSE for v in votes):
            result.status = "REJECT"
            result.confidence = max(result.confidence, min(.95, .55 + .08 * len(set(support))))
            # Empirical Beta estimate from analogous known-violation samples.
            nfail = nsuccess = 0
            counted = set()
            for key in keys:
                for sample in self.models.get(key, {}).get("samples", []):
                    if sample["id"] not in counted and any(sample["facts"].get(k) == facts.get(k, Evidence()).truth
                           for k in result.violated if facts.get(k, Evidence()).truth != Truth.UNKNOWN):
                        counted.add(sample["id"])
                        nsuccess += sample["success"]
                        nfail += not sample["success"]
            result.failure_probability = max(result.failure_probability, (nfail + 1) / (nfail + nsuccess + 2))
        elif votes and all(v == Truth.TRUE for v in votes) and result.status != "REJECT":
            result.status = "SUPPORTED"
            # Necessary conditions being satisfied is not sufficient for success.
            # Estimate residual rejection from matching public samples, retaining
            # failures the current conjunction does not yet explain.
            model = self.models.get(keys[0]) or self.models.get(keys[1])
            names = {k for h in model.get("hypotheses", []) for k in h}
            similar = [s for s in model["samples"] if names and all(
                facts.get(k, Evidence()).truth != Truth.UNKNOWN
                and s["facts"].get(k, Truth.UNKNOWN) == facts[k].truth for k in names)]
            result.failure_probability = (sum(not s["success"] for s in similar)+1)/(len(similar)+2)
            result.confidence = min(.9, .5 + .04 * len(set(support)))
        else:
            model = self.models.get(keys[0]) or self.models.get(keys[1])
            if model and result.status == "UNKNOWN":
                success = sum(s["success"] for s in model["samples"])
                result.failure_probability = (len(model["samples"])-success+1)/(len(model["samples"])+2)
        result.support = sorted(set(support))[-32:]
        result.violated = sorted(set(result.violated)); result.unknown = sorted(set(result.unknown))
        # Risk is not a permission ban. Selection may still choose a justified probe.
        return result

    def _feedback_requirements(self, action, feedback):
        a = parse_action(action)
        rules = []
        if re.search(r"space in hand", feedback, re.I):
            rules.append(("hands.space", "verb:" + a.verb))
        if a.verb == "enter" and re.search(r"blocked the way out|in combat", feedback, re.I):
            rules.append(("combat.clear", "specific:" + a.schema))
        missing = re.search(r"Missing necessary (.+?) in the current area", feedback, re.I)
        if a.verb == "craft" and missing:
            for name in missing[1].split(", "):
                predicate = "ground:" + name.strip()
                known = self.required_keys.setdefault(a.schema, [])
                if predicate not in known:
                    known.append(predicate)
                rules.append((predicate, "specific:" + a.schema))
        if a.verb == "pick up" and re.search(r"not found in current area", feedback, re.I):
            rules.append(("target.ground", "specific:" + a.schema))
        if a.verb in {"equip", "drop"} and re.search(r"not found in hand|not holding", feedback, re.I):
            rules.append(("target.held", "specific:" + a.schema))
        return rules

    def observe(self, action, before, after):
        success = public_outcome(action, before, after)
        if success is None:
            return None
        prediction = self.predict(action, before)
        facts = self.features(action, before)
        self.sequence += 1
        sample_id = digest([self.sequence, action, before.to_dict(), after.feedback, success])[:20]
        if not success:
            for predicate, scope in self._feedback_requirements(action, after.feedback):
                rid = digest([predicate, scope])[:16]
                if rid not in self.feedback_rules:
                    self.feedback_rules[rid] = {"predicate": predicate, "expected": Truth.TRUE, "scope": scope,
                        "status": "active", "confidence": .9, "support": [], "contradictions": [], "source": "explicit_public_failure"}
                rule = self.feedback_rules[rid]
                rule["support"] = (rule["support"] + [sample_id])[-32:]
                # The feedback establishes this failure's condition only. It never
                # fills in an unknown future observation or a hidden test state.
                facts[predicate] = Evidence(Truth.FALSE, "explicit_public_failure", before.step, .9, before.location or "unknown")
                self.events.append({"event": "feedback_condition", "rule": rid, "sample": sample_id, "predicate": predicate})
        else:
            for rid, rule in self.feedback_rules.items():
                if rule["scope"] in self.keys(action) and facts.get(rule["predicate"], Evidence()).truth == Truth.FALSE:
                    rule["status"] = "contradicted"
                    rule["confidence"] *= .3
                    rule["contradictions"].append(sample_id)
                    self.events.append({"event": "precondition_revised", "rule": rid, "sample": sample_id})
        for key in self.keys(action):
            values = {k: v.truth for k, v in facts.items() if not key.startswith("verb:") or ":" not in k}
            model = self.models.pop(key, {"samples": [], "hypotheses": [], "version": 0})
            self.models[key] = model  # Recently updated schema remains in the bounded store.
            model["samples"].append({"id": sample_id, "facts": values, "success": success, "step": before.step,
                                     "action": action, "source": "public_transition"})
            model["samples"] = model["samples"][-self.max_samples:]
            if self._refit(model):
                self.events.append({"event": "contrastive_rule_update", "model": key, "version": model["version"],
                                    "sample": sample_id, "hypotheses": model["hypotheses"],
                                    "support": [s["id"] for s in model["samples"]], "unexplained_failures": model["unexplained_failures"]})
        while len(self.models) > self.max_models:
            self.models.pop(next(iter(self.models)))
        return {"sample": sample_id, "success": success, "prequential_prediction": prediction.to_dict()}

    def to_dict(self):
        return {"max_samples": self.max_samples, "max_models": self.max_models, "max_literals": self.max_literals,
                "models": self.models, "feedback_rules": self.feedback_rules, "required_keys": self.required_keys, "sequence": self.sequence}

    @classmethod
    def from_dict(cls, data):
        result = cls(data["max_samples"], data["max_models"], data["max_literals"])
        for key in ["models", "feedback_rules", "required_keys", "sequence"]:
            setattr(result, key, data[key])
        return result
