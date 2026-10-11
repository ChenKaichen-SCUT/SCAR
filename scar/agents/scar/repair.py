"""Module C: executable rolling repair plan with rule checks at every step."""
from dataclasses import dataclass, field, asdict
import shlex

from .state import action_key


@dataclass
class RepairPlan:
    goal_action: str = ""
    pending: list = field(default_factory=list)
    origin_step: int = 0
    context_location: str = ""
    last_action: str = ""
    status: str = "idle"

    def install(self, goal, candidates, state, memory, max_steps=3):
        self.goal_action = goal
        self.origin_step = state.step
        self.context_location = state.fields.get("location", "")
        self.pending = []
        seen = {action_key(goal)}
        for action in candidates:
            key = action_key(action)
            if key not in seen and memory.assess(action, state)[0] != "block":
                self.pending.append(action)
                seen.add(key)
            if len(self.pending) >= max_steps:
                break
        self.status = "repairing" if self.pending else "needs_information"

    def choose(self, proposal, state, memory):
        if self.status in {"idle", "complete", "failed"}:
            return proposal, "base"
        if state.step - self.origin_step > 20:
            self.status = "expired"
            self.pending.clear()
            return proposal, "expired"
        # Changed conditions release the remembered subgoal; retry is a real action.
        assessment, rule = memory.assess(self.goal_action, state)
        if assessment in {"allow", "probe"} and action_key(self.last_action) != action_key(self.goal_action):
            self.last_action = self.goal_action
            self.pending.clear()
            self.status = "retrying"
            return self.goal_action, "safe_retry"
        # A new location can invalidate a planned local action; ask base policy to replan.
        if state.fields.get("location", "") != self.context_location:
            self.pending.clear()
        while self.pending:
            candidate = self.pending.pop(0)
            if memory.assess(candidate, state)[0] != "block":
                self.last_action = candidate
                return candidate, "repair_step"
        return proposal, "base"

    def observe(self, action, failed, success_evidence):
        if action_key(action) == action_key(self.goal_action):
            if failed:
                self.status = "failed"
            elif success_evidence:
                self.status = "complete"
                self.pending.clear()
        elif failed and action_key(action) == action_key(self.last_action):
            self.pending.clear()
            self.status = "needs_information"

    def to_dict(self):
        return asdict(self)


def valid_syntax(action, actions):
    """Checks public action signatures only; does not query environment validity."""
    for spec in sorted(actions, key=lambda a: len(a.verb), reverse=True):
        if action == spec.verb or action.startswith(spec.verb + " "):
            try:
                params = shlex.split(action[len(spec.verb):])
            except ValueError:
                return False
            return len(params) == len(spec.params)
    return False
