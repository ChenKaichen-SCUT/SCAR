"""Task-bound execution trials with persistent, explicitly tentative reviews."""
import json

from scar_public.agent import PublicAgent
from scar_public.evidence import EvidenceMemory


CONTRACT_INSTRUCTION = """
You receive a chronological ledger of public observations, the current observation, and recent
execution trials. Observation deltas are changes in the REPORT, not necessarily world changes.
Old observations establish past state. Trial interpretations are hypotheses, not facts.

Plan backwards from a specific task outcome. Bind every consequential action argument to the
role it has in that outcome: which entity, content, destination, or stage is actually requested?
A genuine quotation can describe a DIFFERENT target or stage. A quotation proves its words
were observed; it does not prove that your interpretation or proposed action achieves this goal.
Use one or two short quoted bindings for the decisive arguments; mark unsupported links unknown.

Separate two predictions: (1) the immediate action effect and (2) evidence of the task outcome.
An accepted command or successful preparation does not certify the second. Check the resulting
state, including collateral changes and whether preparation reverses an earlier prerequisite.
For one atomic operation, required inputs must coexist in an allowed arrangement; do not demand
all resources for a multi-stage quest simultaneously. A route should reduce the remaining path
from the CURRENT location, not restart the route from its original beginning each turn.

Review the last trial against fresh feedback before choosing the next. If the action succeeded
but the desired outcome did not follow, review the causal link, argument binding, or final state.
Do not infer an entire method impossible from one stochastic failure. Absence of confirmation
is uncertainty, not proof of failure; an old task list is not a fresh completion check.

Recent trial reviews persist. A repeated test is informative only if a relevant condition changed
or it distinguishes still-plausible explanations. State that difference explicitly. In particular,
do not describe a previously observed unsuccessful arrangement as untested. When evidence
contradicts the predicted outcome, revise that exact assumption instead of paraphrasing it.
You may retry under changed conditions; these tentative reviews are never permanent action bans.
Prefer a cheap test that distinguishes explanations before repeating costly setup. Do not assume
an action is reversible merely because it is cheap. If a goal is blocked, pursue another supported
subgoal while retaining the unresolved condition, without inventing extra task requirements.

Return reasoning and action, plus these concise objects (keep the entire reply under 1000 words):
"frame": {
  "goal_quote": "exact public task instruction",
  "bindings": [{"role": "argument's role in THIS goal", "value": "chosen argument",
                "quote": "exact supporting public observation excerpt"}],
  "method": "tentative method and its jointly required arrangement",
  "target_test": "what observable outcome would establish this task/subgoal, beyond command success",
  "expected": "immediate effect of this action; remaining gap or uncertainty"},
"review": {"verdict": "progress|counterexample|uncertain",
           "quote": "exact excerpt from the CURRENT observation relevant to the last trial",
           "interpretation": "which prediction is supported or contradicted; what changes in the method"}.
At most two bindings. Empty bindings/review are allowed when evidence is unavailable. The review
is your interpretation; a verified quote alone does not establish that the interpretation is true.
"""


class ContractMemory(EvidenceMemory):
    def __init__(self):
        super().__init__()
        self.trials = []

    def prompt(self, observation):
        prompt = super().prompt(observation)
        marker = "\nTentative execution frame (not established fact):\n"
        left, right = prompt.split(marker, 1)
        return (left + "\nRecent execution trials (MODEL HYPOTHESES, not established facts):\n" +
                json.dumps(self.trials[-8:], ensure_ascii=False) + marker + right)

    def update(self, parsed, observation, step):
        review = parsed.get("review", {})
        if self.trials and isinstance(review, dict):
            quote = review.get("quote", "")
            interpretation = review.get("interpretation", "")
            if (review.get("verdict") in ("progress", "counterexample", "uncertain") and
                    isinstance(quote, str) and 8 <= len(quote) <= 600 and quote in observation and
                    isinstance(interpretation, str) and len(interpretation) <= 1000):
                self.trials[-1]["review"] = {k: review[k] for k in ("verdict", "quote", "interpretation")}
            else:
                self.trials[-1]["review"] = {"verdict": "uncertain", "reason": "missing or untraceable review"}
        frame = parsed.get("frame", {})
        fields = ("goal_quote", "method", "target_test", "expected")
        valid = isinstance(frame, dict) and all(isinstance(frame.get(k), str) and len(frame[k]) <= 1000
                                              for k in fields)
        if valid and len(frame["goal_quote"]) >= 12 and any(frame["goal_quote"] in o for o in self.observations):
            self.frame = {k: frame[k] for k in fields}
            bindings = frame.get("bindings", [])
            kept = []
            if isinstance(bindings, list):
                for binding in bindings[:2]:
                    if (isinstance(binding, dict) and all(isinstance(binding.get(k), str) and
                            len(binding[k]) <= 600 for k in ("role", "value", "quote")) and
                            len(binding["quote"]) >= 8 and any(binding["quote"] in o for o in self.observations)):
                        kept.append({k: binding[k] for k in ("role", "value", "quote")})
            self.frame["bindings"] = kept
            self.audit.append({"step": step, "frame": "traceable_not_semantically_verified"})
        else:
            # Do not silently carry a rejected new method forward as a valid contract.
            self.frame = {"status": "unverified: invalid schema or untraceable task anchor"}
            self.audit.append({"step": step, "frame": "rejected"})
        self.last_action = parsed["action"].strip()
        self.trials.append({"step": step, "action": self.last_action, "contract": dict(self.frame)})
        self.trials = self.trials[-8:]


class ContractAgent(PublicAgent):
    def __init__(self, llm, system_prompt):
        self.llm = llm
        self.system_prompt = system_prompt.replace("exactly these keys", "these required keys") + CONTRACT_INSTRUCTION
        self.notebook = ContractMemory()
