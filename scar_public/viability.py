"""Method-level feasibility replaces the previous single-action success criterion."""
import json
from scar_public.evidence import EvidenceMemory, EVIDENCE_INSTRUCTION
from scar_public.agent import PublicAgent

VIABILITY_INSTRUCTION = """
Use a METHOD-LEVEL execution contract, not just a prediction for the next action.
An action succeeding is not sufficient progress: it may undo a prerequisite established by
an earlier action. Check the final arrangement required by the current method against the
capacity, location, tools and resource constraints actually observed. Inputs for ONE atomic
operation must be jointly available in an allowed arrangement. Do not demand that resources
for an entire multi-stage quest coexist: earlier stages can be completed and consumed normally.

Before more setup actions, ask whether this method can reach its required arrangement at all.
If repeated preparation restores an earlier arrangement without satisfying another prerequisite,
identify the structural conflict. Revise the arrangement or acquisition/execution method; do
not keep cycling through individually successful moves. Compare the WHOLE method's unmet
conditions across turns, not merely whether the latest action did what it was asked to do.
Use observed interfaces to test alternative arrangements instead of inventing new prerequisites.
An infeasible or unverified method does not make the desired outcome infeasible.

Replace the earlier frame schema with:
{"goal_quote": "exact public task instruction quote",
 "method": "specific current method; tentative if untested",
 "required_state": "the minimal arrangement needed for this method's next substantive operation",
 "feasibility": "jointly possible / contradicted / unknown, with observed evidence and the bottleneck",
 "assessment": "which method prerequisite was gained or lost; whether setup undid earlier progress",
 "expected": "observable result and how it reduces this method's remaining gap"}.
Keep all fields concise. The frame is a hypothesis, never a permanent fact or a hard action ban.
"""


class ViabilityMemory(EvidenceMemory):
    def update(self, parsed, observation, step):
        super().update(parsed, observation, step)
        frame = parsed.get("frame", {})
        if isinstance(frame, dict):
            for key in ("required_state", "feasibility"):
                value = frame.get(key)
                if isinstance(value, str) and len(value) <= 1200:
                    self.frame[key] = value
                else:
                    self.frame.pop(key, None)


class ViabilityAgent(PublicAgent):
    def __init__(self, llm, system_prompt):
        self.llm = llm
        self.system_prompt = (system_prompt.replace("exactly these keys", "these required keys") +
                              EVIDENCE_INSTRUCTION + VIABILITY_INSTRUCTION)
        self.notebook = ViabilityMemory()
