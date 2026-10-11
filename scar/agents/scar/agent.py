"""SCAR as an official AgentOdyssey agent mixin and factory."""
import json
from pathlib import Path
from functools import lru_cache

from agents.fixed_size.short_term_memory_agent import ShortTermMemoryAgent
from scar.io import atomic_json
from .state import VisibleState, action_key
from .detection import diagnose
from .memory import FailureMemory
from .repair import RepairPlan, valid_syntax


class SCARAgent(ShortTermMemoryAgent):
    def __init__(self, id, name, cfg=None):
        super().__init__(id, name, cfg)
        settings = getattr(cfg, "scar_settings", {})
        self.failure_memory = FailureMemory(**{k: v for k, v in settings.items() if k != "max_plan_steps"})
        self.max_plan_steps = settings.get("max_plan_steps", 3)
        self.plan = RepairPlan()
        self.visible_state = None
        self.pending_transition = None
        self.last_failure = None
        self.events = []
        self.decision = {}
        self.memory_paths = ["memory.json", "scar.json"]

    def observe_transition(self, before_obs, action, after_obs):
        before = VisibleState.observe(before_obs, self.visible_state)
        after = VisibleState.observe(after_obs, before)
        failure = diagnose(action, before, after)
        if failure:
            rule = self.failure_memory.learn(failure)
            self.events.append({"event": "failure_learned", "step": before.step,
                                "rule": rule.id, "failure": failure.to_dict()})
            self.last_failure = failure
        else:
            self.last_failure = None
        updates = self.failure_memory.revise(action, before, after, failure is not None)
        self.events.extend(dict(update, step=after.step) for update in updates)
        self.plan.observe(action, failure is not None, bool(updates) or before.fields != after.fields)
        self.visible_state = after
        self.pending_transition = None

    def _act(self, obs):
        if self.pending_transition:
            self.observe_transition(*self.pending_transition, obs)
        state = VisibleState.observe(obs, self.visible_state)
        self.visible_state = state
        start_tokens = (self.llm.tokens_in, self.llm.tokens_out)
        proposed, _, _, base_response = super()._act(obs)
        actual, reason = self.plan.choose(proposed, state, self.failure_memory)
        assessment, rule = self.failure_memory.assess(actual, state)
        proposals = [proposed]
        if rule:
            self.events.append({"event": "memory_hit", "step": state.step,
                                "action": actual, "rule": rule.id, "assessment": assessment})
        if assessment == "probe":
            rule.probes += 1
            self.events.append({"event": "cooldown_retry", "step": state.step, "rule": rule.id})
        if assessment == "block" or (self.last_failure and self.plan.status in {"idle", "failed", "needs_information"}):
            goal = actual if assessment == "block" else self.last_failure.action
            evidence = [r.__dict__ for r in self.failure_memory.retrieve(goal, state)[:3]]
            repair_prompt = (
                f"Current observation:\n{obs['text']}\nRecent memory:\n" + "\n".join(self.short_term_memory[-5:])
                + f"\nBlocked subgoal: {goal}\nConditional failure evidence: {json.dumps(evidence)}\n"
                "Propose a short local recovery plan to remove the blocker or advance the same goal via another route. "
                "Use only observed entities and the public action space. An unknown prerequisite is a hypothesis. "
                "Prefer useful information gathering when uncertain. Return JSON with reasoning, action (first step), "
                "and plan (a list of at most 3 action strings)."
            )
            result = self.llm.generate(repair_prompt, self.cfg.system_prompt)
            parsed = result["parsed"]
            candidates = [parsed["action"]] + (parsed.get("plan", []) if isinstance(parsed.get("plan"), list) else [])
            candidates = [a for a in candidates if isinstance(a, str) and valid_syntax(a, self.available_actions)]
            proposals.extend(candidates)
            self.plan.install(goal, candidates, state, self.failure_memory, self.max_plan_steps)
            for candidate in list(self.plan.pending):
                if self.failure_memory.assess(candidate, state)[0] != "block":
                    actual = candidate
                    self.plan.pending.remove(candidate)
                    self.plan.last_action = candidate
                    reason = "repair"
                    break
            else:
                # Explicit bounded verification, not a fabricated successful repair.
                actual, reason = proposed, "verification_fallback"
            self.events.append({"event": "plan_repair", "step": state.step,
                                "plan": self.plan.to_dict(), "executed": actual, "reason": reason})
        self.decision = {"proposed_action": proposed, "executed_action": actual,
                         "all_proposals": proposals, "intercepted": action_key(actual) != action_key(proposed),
                         "reason": reason, "rule_predictions": [
                             {"rule_id": r.id, "action": r.action, "predict_invalid":
                              self.failure_memory.assess(r.action, state)[0] == "block"}
                             for r in self.failure_memory.rules if r.status != "contradicted"]}
        if self.decision["intercepted"]:
            self.events.append({"event": "action_intercepted", "step": state.step,
                                "proposed": proposed, "executed": actual})
        # Correct the official STM entry: memory must reflect the executed action.
        self.short_term_memory[-1] = f"{obs['text']}\nProposed: {proposed}\nExecuted action: {actual}"
        self.pending_transition = (obs, actual)
        return actual, self.llm.tokens_in - start_tokens[0], self.llm.tokens_out - start_tokens[1], base_response

    def save_memory(self, full_memory_dir):
        super().save_memory(full_memory_dir)
        atomic_json(Path(full_memory_dir) / "scar.json", {
            "failure_memory": self.failure_memory.to_dict(), "plan": self.plan.to_dict(),
            "visible_state": self.visible_state.__dict__ if self.visible_state else None,
            "pending_transition": self.pending_transition,
            "last_failure": self.last_failure.to_dict() if self.last_failure else None,
        })

    def load_memory(self, full_memory_dir):
        from .detection import FailureEvent
        super().load_memory(full_memory_dir)
        data = json.loads((Path(full_memory_dir) / "scar.json").read_text())
        self.failure_memory = FailureMemory.from_dict(data["failure_memory"])
        self.plan = RepairPlan(**data["plan"])
        self.visible_state = VisibleState(**data["visible_state"]) if data["visible_state"] else None
        self.pending_transition = data["pending_transition"]
        self.last_failure = FailureEvent(**data["last_failure"]) if data["last_failure"] else None


@lru_cache(maxsize=None)
def create_scar_agent(Agent):
    return type(f"SCARAgent__{Agent.__module__}.{Agent.__name__}", (SCARAgent, Agent), {"__module__": Agent.__module__})
