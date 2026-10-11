"""Full SCAR-V3 agent: online learning plus evidence-gated recovery selection."""
from functools import lru_cache
import json
from pathlib import Path
import shlex

from agents.fixed_size.short_term_memory_agent import ShortTermMemoryAgent
from scar.agents.scar.repair import valid_syntax
from scar.agents.scar.state import action_key
from scar.io import atomic_json
from scar.providers.deepseek import ModelResponseError
from scar_v3.state import PublicState, Truth, parse_action
from scar_v3.learning import PreconditionLearner, public_outcome
from scar_v3.selection import Selector


class SCARV3Agent(ShortTermMemoryAgent):
    def __init__(self, id, name, cfg=None):
        super().__init__(id, name, cfg)
        self.learner = PreconditionLearner()
        self.selector = Selector()
        self.public_state = None
        self.pending_transition = None
        self.goal_action = ""
        self.plan = {"actions": [], "goal": "", "created": 0, "location": None}
        self.events, self.decision = [], {}
        self.last_intervention = None
        self.public_objective = None
        self.memory_paths = ["memory.json", "scar_v3.json"]

    def set_recovery_objective(self, target_action, public_objective):
        self.goal_action = target_action
        self.public_objective = public_objective

    def observe_transition(self, before_obs, action, after_obs):
        before = PublicState.observe(before_obs, self.public_state)
        after = PublicState.observe(after_obs, before, action)
        learned = self.learner.observe(action, before, after)
        if learned:
            self.events.append({"event": "online_sample", "action": action, **learned})
        self.events += self.learner.events
        self.learner.events.clear()
        if not self.public_objective and before.goal and after.goal and before.goal != after.goal:
            self.events.append({"event": "goal_superseded", "old": before.goal, "new": after.goal})
            self.plan["actions"] = []
            self.goal_action = after.goal
        elif learned and not learned["success"] and not self.goal_action:
            self.goal_action = action
        if self.last_intervention:
            old = self.learner.features(self.goal_action, before)
            new = self.learner.features(self.goal_action, after)
            improvement = any(old[k].truth == Truth.FALSE and new.get(k) and new[k].truth == Truth.TRUE for k in old)
            improvement |= action_key(action) == action_key(self.goal_action) and bool(learned and learned["success"])
            self.selector.update(action, learned["success"] if learned else None, improvement)
            self.events.append({"event": "intervention_feedback", "action": action,
                                "public_success": learned["success"] if learned else None,
                                "public_condition_improved": improvement,
                                "scope": "observation-derived proxy; evaluator separately checks physical goal"})
        if learned and learned["success"] and action_key(action) == action_key(self.goal_action):
            self.plan["actions"] = []
            if self.public_objective and parse_action(action).verb == "craft":
                self.goal_action = "pick up " + shlex.quote(parse_action(action).target)
            elif not self.public_objective and not (after.goal and after.goal != before.goal):
                self.goal_action = ""
        elif learned and not learned["success"] and action in self.plan["actions"]:
            self.plan["actions"] = []
        self.public_state, self.pending_transition, self.last_intervention = after, None, None

    def _local_candidates(self, state):
        candidates = []
        goal_prediction = self.learner.predict(self.goal_action, state)
        if "hands.space" in goal_prediction.violated and state.hands:
            for item in state.hands:
                if item != parse_action(self.goal_action).target:
                    candidates.append("drop " + shlex.quote(item))
                if any(word in item for word in ["bag", "pouch", "satchel", "pack"]):
                    candidates.append("equip " + shlex.quote(item))
        if goal_prediction.unknown:
            for item in state.hands or {}:
                if any(word in item for word in ["bag", "pouch", "satchel", "pack"]):
                    candidates.append("inspect " + shlex.quote(item))
        if (self.plan["goal"] == self.goal_action and self.plan["location"] == state.location
                and state.step-self.plan["created"] <= 12):
            candidates += self.plan["actions"]
        else:
            if self.plan["actions"]:
                self.events.append({"event": "plan_invalidated", "step": state.step})
            self.plan["actions"] = []
        return list(dict.fromkeys(candidates))

    def _act(self, obs):
        if self.pending_transition:
            self.observe_transition(*self.pending_transition, obs)
        state = PublicState.observe(obs, self.public_state)
        self.public_state = state
        tokens = self.llm.tokens_in, self.llm.tokens_out
        proposed, _, _, response = ShortTermMemoryAgent._act(self, obs)
        if not self.goal_action:
            self.goal_action = state.goal or proposed
        syntax_ok = valid_syntax(proposed, self.available_actions)
        base = self.selector.score(proposed, self.goal_action, state, self.learner, syntax_ok)
        candidates = self._local_candidates(state)
        values = [self.selector.score(c, self.goal_action, state, self.learner,
                                      valid_syntax(c, self.available_actions), switching=True) for c in candidates]
        chosen, reason = self.selector.choose(base, values)
        prediction = self.learner.predict(proposed, state)
        extra = False
        if chosen.action == proposed and (not syntax_ok or prediction.status == "REJECT" and prediction.confidence >= .65):
            prompt = (
                f"Current observation:\n{obs['text']}\nRecent memories:\n" + "\n".join(self.short_term_memory[-5:])
                + f"\nRecovery objective: {self.public_objective or self.goal_action}\nCurrent candidate: {proposed}\n"
                + f"Observed/learned evidence: {json.dumps(prediction.to_dict())}\n"
                + "Suggest at most three short recovery or information-gathering actions that address the evidence. "
                "Use only observed entities. Unknown facts are not false. Do not insist on an obsolete goal. "
                "Return JSON with reasoning, action and plan (action strings).\n" + self.cfg.action_prompt)
            parsed = self.llm.generate(prompt, self.cfg.system_prompt)["parsed"]
            extra = True
            suggested = [parsed["action"]] + (parsed.get("plan", []) if isinstance(parsed.get("plan"), list) else [])
            suggested = list(dict.fromkeys(c.strip() for c in suggested if isinstance(c, str)))[:3]
            candidates += suggested
            values += [self.selector.score(c, self.goal_action, state, self.learner,
                                          valid_syntax(c, self.available_actions), extra_call_cost=1, switching=True) for c in suggested]
            chosen, reason = self.selector.choose(base, values)
            self.plan = {"actions": [c for c in suggested if valid_syntax(c, self.available_actions)],
                         "goal": self.goal_action, "created": state.step, "location": state.location}
        if not chosen.allowed:
            # A format correction is a separate mandatory signature check, still
            # fully costed and never replaced silently with wait.
            valid = [v for v in values if v.allowed]
            if not valid:
                raise ModelResponseError("No public-signature-valid action after bounded V3 format repair")
            chosen = max(valid, key=lambda v: v.value)
            reason = "mandatory_format_correction"
        actual = chosen.action
        if actual in self.plan["actions"]:
            self.plan["actions"].remove(actual)
        intercepted = actual != proposed and (action_key(actual) != action_key(proposed) or not syntax_ok)
        self.decision = {"proposed_action": proposed, "executed_action": actual,
                         "all_proposals": list(dict.fromkeys([proposed]+candidates)), "intercepted": intercepted,
                         "reason": reason, "base_value": base.to_dict(), "executed_value": chosen.to_dict(),
                         "candidate_values": [v.to_dict() for v in values], "extra_repair_call": extra,
                         "goal_action": self.goal_action, "rule_predictions": [
                             {"action": proposed, "rule_id": "v3-prequential", "predict_invalid": prediction.status == "REJECT",
                              "prediction_status": prediction.status, "failure_probability": prediction.failure_probability,
                              "confidence": prediction.confidence}]}
        self.events.append({"event": "intervention_decision", "step": state.step, "intercepted": intercepted,
                            "reason": reason, "net_value": chosen.value-base.value, "rules": prediction.rules,
                            "support": chosen.support})
        self.last_intervention = self.decision if intercepted else None
        self.short_term_memory[-1] = f"{obs['text']}\nProposed: {proposed}\nExecuted action: {actual}"
        self.pending_transition = obs, actual
        return actual, self.llm.tokens_in-tokens[0], self.llm.tokens_out-tokens[1], response

    def save_memory(self, full_memory_dir):
        super().save_memory(full_memory_dir)
        atomic_json(Path(full_memory_dir) / "scar_v3.json", {
            "learner": self.learner.to_dict(), "selector_outcomes": self.selector.outcomes,
            "public_state": self.public_state.to_dict() if self.public_state else None,
            "goal_action": self.goal_action, "public_objective": self.public_objective,
            "plan": self.plan, "pending_transition": self.pending_transition, "last_intervention": self.last_intervention})

    def load_memory(self, full_memory_dir):
        super().load_memory(full_memory_dir)
        data = json.loads((Path(full_memory_dir) / "scar_v3.json").read_text())
        self.learner = PreconditionLearner.from_dict(data["learner"])
        self.selector.outcomes = data["selector_outcomes"]
        self.public_state = PublicState.from_dict(data["public_state"]) if data["public_state"] else None
        for key in ["goal_action", "public_objective", "plan", "pending_transition", "last_intervention"]:
            setattr(self, key, data[key])


@lru_cache(maxsize=None)
def create_scar_v3_agent(Agent):
    return type(f"SCARV3Agent__{Agent.__module__}.{Agent.__name__}", (SCARV3Agent, Agent), {"__module__": Agent.__module__})


def make_agent(algorithm, game, provider, settings, memory_dir):
    if algorithm == "SCARV2Agent":
        from scar_v2.agent import make_agent as factory
        return factory(algorithm, game, provider, settings, memory_dir)
    if algorithm != "SCARV3Agent":
        from scar.integration import make_agent as factory
        return factory(algorithm, game, provider, settings, memory_dir)
    from scar.integration import DeepSeekMemoryConfig
    from utils import dynamic_load_game_class
    cfg = DeepSeekMemoryConfig(llm_name=settings["model"], llm_provider="deepseek", embed_name=settings["embedding_model"],
                              max_new_tokens=settings["max_tokens"], temperature=settings["temperature"],
                              short_term_memory_size=5, torch_seed=settings.get("seed", 42), full_mem_path=str(memory_dir))
    cfg.scar_provider = provider
    return create_scar_v3_agent(dynamic_load_game_class(game, "agent", "Agent"))(
        id=AGENT_NAME, name="adam_davis", cfg=cfg)


AGENT_NAME = "agent_adam_davis"
