"""Separate task specification from action generation; check local joint arrangements."""
import json
import re

from scar_public.evidence import EvidenceMemory
from scar_public.public_model import PublicModel


SPEC_SYSTEM = """You specify a currently unresolved task BEFORE an actor proposes any action.
Use only the supplied public evidence. Do not solve a different, easier task. Pick a concrete
pending subgoal that can plausibly advance now, considering danger and already completed stages.
Do not simply select the first listed subgoal. Old task lists may be stale; explicit completed
stages remain achieved even when their consumed resources are no longer held.

Write observable terminal conditions. Every entity, content and destination must be bound to its
role in this exact goal. Preserve multiple interpretations when public evidence does not resolve
them. Similar phrases can have different task roles; locate their original descriptions. Neither
a successful command nor the presence of an arbitrary phrase proves the requested outcome.
If the task does not specify exact versus partial matching, preserve that uncertainty; never
import a hidden evaluator rule. Conditions below are proposed interpretations, not ground truth.

Return JSON with reasoning (at most 100 words), action="specification_only", and specification:
{"goal_quote":"exact public task instruction", "conditions":[
 {"kind":"reported|held|at|text_equals|text_contains", "item":"object if applicable",
  "value":"task instruction / location / content if applicable", "count":1}],
 "hypotheses":[{"id":"H1", "interpretation":"precise reading of the task or uncertain operation",
                 "quote":"exact public evidence excerpt; provenance is not entailment"}],
 "focus":{"kind":"craft|navigate|write|other", "target":"item to craft / destination / writable object"}}.
Use at most 3 conditions and 3 hypotheses. A craft focus names the useful recipe output, never
an invented recipe. A focus is an implementation choice and can change without changing the task.
The action field is a schema placeholder; it is NOT an environment action. Keep JSON concise.
"""

ACT_INSTRUCTION = """
The task specification was generated separately before this action. It is tentative but you may
not silently rewrite it to fit an easy action. Parsed quantities and arrangement search are from
public observations. A proposed local plan is conditional on the stated assumptions, not a world
simulation. Unknown does not mean impossible. Use fresh feedback to revise method assumptions.
Only an explicit public stage-completion report confirms achievement; satisfied proposed
conditions alone do not certify that the specification was faithful to the task.

Choose one action advancing the specified goal or testing a consequential unresolved hypothesis.
Preparation must permit the required resources to coexist. Check capacity/quantity/location
arithmetic. If a method is blocked, change the arrangement or gather missing evidence. Do not
repeat a trial under the same relevant conditions. Command success is not the terminal outcome.

For a semantic experiment optionally add:
"experiment":{"hypotheses":["H1","H2"], "predictions":[true,false],
 "observe":{"kind":"reported|held|at|text_equals|text_contains", "item":"if needed",
            "value":"if needed", "count":1},
 "preconditions":[{"kind":"held", "item":"necessary object", "count":1}]}.
The booleans describe different observable outcomes under the two hypotheses. The experiment
is discriminating only if predictions differ and its preconditions are actually established.
If observation is unavailable, do not reject a hypothesis. Even a mismatch may reflect an
omitted condition; record it conditionally instead of banning a whole goal or method.
Keep reasoning under 120 words; return reasoning and action as required. No self-certified status.
"""


class SpecificationMemory(EvidenceMemory):
    def __init__(self):
        super().__init__()
        self.model = PublicModel()
        self.specification = {}
        self.spec_step = -100
        self.spec_records = []
        self.pending_experiment = None
        self.experiments = []

    def ingest(self, observation):
        self.model.observe(observation, self.last_action)
        if self.pending_experiment:
            trial = self.pending_experiment
            result = self.model.predicate(trial["observe"])
            trial["observed"] = result
            trial["outcome"] = "unobserved" if result is None else "conditional_evidence"
            trial["inconsistent_under_assumed_preconditions"] = ([name for name, prediction in
                zip(trial["hypotheses"], trial["predictions"]) if prediction != result] if result is not None else [])
            self.experiments.append(trial)
            self.pending_experiment = None
        super().prompt(observation)  # Maintains exact public ledger and checkpoint history.

    def specification_context(self, observation):
        return json.dumps({"pending_public_tasks": self.model.tasks, "completed_public_tasks": self.model.completed,
            "public_source_evidence": self.model.source_lines, "current_observation": observation,
            "observed_model": self.model.view(), "recent_experiments": self.experiments[-4:]}, ensure_ascii=False)

    def set_specification(self, parsed, step):
        proposed = parsed.get("specification", {})
        quote = proposed.get("goal_quote") if isinstance(proposed, dict) else None
        valid = isinstance(quote, str) and 12 <= len(quote) <= 1200 and any(quote in o for o in self.observations)
        if valid and isinstance(proposed.get("conditions"), list) and isinstance(proposed.get("focus"), dict):
            conditions = [c for c in proposed["conditions"][:3] if isinstance(c, dict) and c.get("kind") in
                          ("reported", "held", "at", "text_equals", "text_contains")]
            hypotheses = [h for h in proposed.get("hypotheses", [])[:3] if isinstance(h, dict) and
                all(isinstance(h.get(k), str) for k in ("id", "interpretation", "quote")) and
                len(h["quote"]) >= 8 and any(h["quote"] in o for o in self.observations)]
            self.specification = {"goal_quote": quote, "conditions": conditions, "hypotheses": hypotheses,
                                  "focus": proposed["focus"]}
        else:
            self.specification = {"goal_quote": "", "conditions": [], "hypotheses": [], "focus": {"kind": "other"}}
        self.spec_step = step
        self.spec_records.append({"step": step, "accepted_provenance_only": valid,
                                  "specification": self.specification, "reasoning": parsed.get("reasoning", "")})

    def register_experiment(self, parsed, step):
        trial = parsed.get("experiment")
        if not isinstance(trial, dict):
            return
        ids = trial.get("hypotheses", [])
        predictions = trial.get("predictions", [])
        known = {h["id"] for h in self.specification.get("hypotheses", [])}
        preconditions = trial.get("preconditions", [])
        valid = (isinstance(ids, list) and len(ids) == 2 and len(set(ids)) == 2 and set(ids) <= known and
                 isinstance(predictions, list) and len(predictions) == 2 and
                 all(type(p) is bool for p in predictions) and predictions[0] != predictions[1] and
                 isinstance(trial.get("observe"), dict) and isinstance(preconditions, list) and
                 bool(preconditions) and all(isinstance(c, dict) and self.model.predicate(c) is True for c in preconditions))
        if valid:
            self.pending_experiment = {"step": step, "action": parsed["action"], **trial,
                "qualification": "predictions and completeness of preconditions are model hypotheses"}
        else:
            self.audit.append({"step": step, "experiment": "not_discriminating_or_preconditions_unknown"})

    def state(self):
        return {k:v for k,v in vars(self).items() if k != "model"}

    def load(self, state):
        # Migrate raw public observations, never the previous actor's execution frame.
        for key in ("observations", "ledger", "last_action", "audit", "specification", "spec_step",
                    "spec_records", "pending_experiment", "experiments"):
            if key in state:
                setattr(self, key, state[key])
        self.frame = {}
        self.model = PublicModel()
        actions = {int(i): a for i,a in re.findall(r"^Action (\d+): (.*)$", self.ledger, re.M)}
        for i, obs in enumerate(self.observations):
            self.model.observe(obs, actions.get(i-1))


class SpecificationAgent:
    def __init__(self, llm, system_prompt):
        self.llm = llm
        self.system_prompt = system_prompt.replace("exactly these keys", "these required keys") + ACT_INSTRUCTION
        self.notebook = SpecificationMemory()

    def act(self, obs):
        memory = self.notebook
        memory.ingest(obs["text"])
        model = memory.model
        step = self.llm.step
        tokens_in = tokens_out = 0
        goal = memory.specification.get("goal_quote", "")
        if not goal or step - memory.spec_step >= 8 or goal in model.completed:
            compiled = self.llm.generate(memory.specification_context(obs["text"]), SPEC_SYSTEM)
            tokens_in += compiled["num_input_tokens"]; tokens_out += compiled["num_output_tokens"]
            memory.set_specification(json.loads(compiled["response"]), step)
        spec = memory.specification
        focus = spec.get("focus", {})
        arrangement = model.arrange(focus.get("target", "")) if focus.get("kind") == "craft" else None
        conditions = [{"condition": c, "value": model.predicate(c)} for c in spec.get("conditions", [])]
        # Replan after every real observation; do not execute an imagined suffix open-loop.
        if arrangement and arrangement.get("plan") and "I was attacked" not in obs["text"]:
            parsed = {"reasoning": "Execute the first action of a candidate joint arrangement; remaining assumptions need environment feedback.",
                      "action": arrangement["plan"][0], "decision_source": "local_arrangement_search"}
        else:
            prompt = ("My Memories: verbatim public evidence (no actor reasoning):\n" + "\n".join(model.source_lines) +
                "\nTask specification (proposed before action):\n" + json.dumps(spec, ensure_ascii=False) +
                "\nObserved model and candidate condition values:\n" + json.dumps({"model": model.view(),
                    "conditions": conditions, "arrangement": arrangement, "recent_experiments": memory.experiments[-4:]}, ensure_ascii=False) +
                "\nMy Current Observation:\n" + obs["text"] + "\nChoose ONE action. Return JSON.")
            generated = self.llm.generate(prompt, self.system_prompt)
            tokens_in += generated["num_input_tokens"]; tokens_out += generated["num_output_tokens"]
            parsed = json.loads(generated["response"])
            check = model.check_action(parsed["action"])
            if check["status"] == "contradicted":
                repaired = self.llm.generate(prompt + "\nProposed action: " + parsed["action"] +
                    "\nObserved constraint conflict: " + json.dumps(check) +
                    "\nChoose a different arrangement or an informative observation. One bounded repair only.", self.system_prompt)
                tokens_in += repaired["num_input_tokens"]; tokens_out += repaired["num_output_tokens"]
                parsed = json.loads(repaired["response"])
        parsed["specification"] = spec
        parsed["condition_values"] = conditions
        parsed["public_completion_confirmed"] = spec.get("goal_quote") in model.completed
        parsed["arrangement"] = arrangement
        parsed["constraint_check"] = model.check_action(parsed["action"])
        memory.register_experiment(parsed, step)
        memory.last_action = parsed["action"].strip()
        return memory.last_action, tokens_in, tokens_out, json.dumps(parsed, ensure_ascii=False)
