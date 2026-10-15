"""Evidence-only memory: reversible observation deltas, no synthesized factual claims."""
import difflib
import json

from scar_public.agent import PublicAgent

EVIDENCE_INSTRUCTION = """
Your memory contains an exact chronological ledger of public observations and actions.
Observation deltas show removed lines (-) and added lines (+); they describe changes in
the report, not necessarily changes in the world. The full current observation is authoritative
for currently visible state. Past reasoning is deliberately not stored as factual memory.

Keep the task's stated outcome distinct from your proposed method. Anchor the goal to an exact
quote of the task instruction in a visible observation. Do not silently add prerequisites from
flavor text, real-world assumptions, or an unsuccessful attempt. If the literal goal appears
satisfied but no completion is reported, test a simple alternative interpretation of that
same outcome before embarking on an unsupported chain of prerequisites.

At each turn assess whether the previous action produced its predicted change. A failed
prediction revises the method/assumption, not the stated task. Repeating an action is useful
only when its observed effect supports further progress or a relevant condition has changed.
If an outcome is ambiguous, choose an inexpensive, reversible action that distinguishes
plausible methods. Treat historical achievements separately from current possession and
capability; normal consumption of a resource need not undo the achievement it enabled.

Return reasoning and action as usual, plus a concise "frame" object:
{"goal_quote": "exact task instruction quote from observation",
 "method": "current proposed method, explicitly tentative if untested",
 "assessment": "last prediction vs observed feedback; revise unsupported assumptions",
 "expected": "specific observable change predicted from this action"}.
Do not produce a fact summary, general lesson, upsert or forget list. Keep the frame short.
Your reasoning should connect observed evidence to the task and the selected next test/action.
"""


def observation_delta(previous, current):
    """A lossless delta used for presentation; original observations remain in state."""
    return list(difflib.ndiff(previous.splitlines(keepends=True), current.splitlines(keepends=True)))


class EvidenceMemory:
    def __init__(self):
        self.observations = []
        self.ledger = ""
        self.frame = {}
        self.last_action = None
        self.audit = []

    def prompt(self, observation):
        index = len(self.observations)
        if not self.observations:
            self.ledger = "Observation 0 (full):\n" + observation + "\n"
        else:
            delta = observation_delta(self.observations[-1], observation)
            changes = "".join(line if line.endswith("\n") else line + "\n"
                              for line in delta if line.startswith(("+ ", "- ")))
            self.ledger += f"\nAction {index-1}: {self.last_action}\nObservation {index} changes:\n" + changes
        self.observations.append(observation)
        return ("My Memories: public evidence ledger. Old entries describe past observations, not current state.\n" +
                self.ledger + "\nTentative execution frame (not established fact):\n" +
                json.dumps(self.frame, ensure_ascii=False) +
                "\nMy Current Observation:\n" + observation +
                "\nAssess the observed result against the previous prediction; choose ONE action. Return JSON.")

    def update(self, parsed, observation, step):
        frame = parsed.get("frame", {})
        fields = ("goal_quote", "method", "assessment", "expected")
        valid = isinstance(frame, dict) and all(isinstance(frame.get(k), str) and len(frame[k]) <= 1200
                                              for k in fields)
        if valid:
            quote = frame["goal_quote"]
            grounded = len(quote) >= 12 and any(quote in o for o in self.observations)
            if grounded:
                self.frame = {k: frame[k] for k in fields}
                self.audit.append({"step": step, "frame": "accepted"})
            else:
                # Keep the existing task anchor; still revise the tentative method.
                self.frame.update({k: frame[k] for k in fields if k != "goal_quote"})
                self.audit.append({"step": step, "frame": "goal_quote_rejected"})
        else:
            self.audit.append({"step": step, "frame": "schema_rejected"})
        self.last_action = parsed["action"].strip()

    def state(self):
        return vars(self)

    def load(self, state):
        self.__dict__.update(state)


class EvidenceAgent(PublicAgent):
    def __init__(self, llm, system_prompt):
        self.llm = llm
        self.system_prompt = system_prompt.replace("exactly these keys", "these required keys") + EVIDENCE_INSTRUCTION
        self.notebook = EvidenceMemory()
