"""Strong simple baseline: same STM, exact observed-state cache and one replan."""
import json
from pathlib import Path
from functools import lru_cache

from agents.fixed_size.short_term_memory_agent import ShortTermMemoryAgent
from scar.agents.scar.state import VisibleState, action_key
from scar.agents.scar.detection import diagnose
from scar.io import atomic_json


class SimpleFailureRecovery(ShortTermMemoryAgent):
    def __init__(self, id, name, cfg=None):
        super().__init__(id, name, cfg)
        self.failures = []
        self.visible_state = None
        self.last_failure = None
        self.pending_transition = None
        self.decision = {}
        self.events = []
        self.memory_paths = ["memory.json", "simple.json"]

    def observe_transition(self, before_obs, action, after_obs):
        before = VisibleState.observe(before_obs, self.visible_state)
        after = VisibleState.observe(after_obs, before)
        event = diagnose(action, before, after)
        self.last_failure = event.feedback if event else None
        if event:
            self.failures.append({"action": action_key(action), "state": after.fingerprint, "step": before.step})
            self.failures = self.failures[-20:]
        self.visible_state = after
        self.pending_transition = None

    def _act(self, obs):
        if self.pending_transition:
            self.observe_transition(*self.pending_transition, obs)
        state = VisibleState.observe(obs, self.visible_state)
        start = (self.llm.tokens_in, self.llm.tokens_out)
        proposal, _, _, response = super()._act(obs)
        blocked = [f["action"] for f in self.failures if f["state"] == state.fingerprint and state.step - f["step"] < 8]
        actual = proposal
        if self.last_failure or action_key(proposal) in blocked:
            result = self.llm.generate(
                f"Current observation:\n{obs['text']}\nRecent memories:\n" + "\n".join(self.short_term_memory)
                + f"\nLast failure: {self.last_failure}\nRecently failed actions under identical observed state: {blocked}.\n"
                + "Replan once to recover and advance the current objective. Avoid those actions while conditions remain unchanged. "
                + self.cfg.action_prompt, self.cfg.system_prompt)
            actual = result["parsed"]["action"]
            # Bounded retry: after one replan, do not silently substitute wait.
        self.decision = {"proposed_action": proposal, "executed_action": actual,
                         "all_proposals": [proposal, actual] if actual != proposal else [proposal],
                         "intercepted": action_key(actual) != action_key(proposal), "reason": "simple_replan",
                         "rule_predictions": []}
        self.short_term_memory[-1] = f"{obs['text']}\nProposed: {proposal}\nExecuted action: {actual}"
        self.pending_transition = (obs, actual)
        return actual, self.llm.tokens_in - start[0], self.llm.tokens_out - start[1], response

    def save_memory(self, full_memory_dir):
        super().save_memory(full_memory_dir)
        atomic_json(Path(full_memory_dir) / "simple.json", {"failures": self.failures,
                    "visible_state": self.visible_state.__dict__ if self.visible_state else None,
                    "last_failure": self.last_failure, "pending_transition": self.pending_transition})

    def load_memory(self, full_memory_dir):
        super().load_memory(full_memory_dir)
        data = json.loads((Path(full_memory_dir) / "simple.json").read_text())
        self.failures = data["failures"]
        self.visible_state = VisibleState(**data["visible_state"]) if data["visible_state"] else None
        self.last_failure = data["last_failure"]
        self.pending_transition = data["pending_transition"]


@lru_cache(maxsize=None)
def create_simple_recovery_agent(Agent):
    return type(f"SimpleFailureRecovery__{Agent.__module__}.{Agent.__name__}",
                (SimpleFailureRecovery, Agent), {"__module__": Agent.__module__})
