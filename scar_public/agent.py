"""Minimal persistent public evidence and a revisable goal/method frame."""
import json


PUBLIC_INSTRUCTION = """
Keep a small execution notebook across turns. The recent history is limited to 5 turns.
Separate the desired outcome from the method currently being tried. A method's failed
prerequisite does not invalidate the outcome or alternative methods. Keep useful discoveries
and previous milestones, but never treat a historical possession as a current possession.
Current observation overrides stale state. Do not preserve a resource after its normal use.
Learn from the observed outcome of the last action before choosing the next action.
If progress stalls, identify the missing evidence or prerequisite; do not repeat a failed
method without a relevant change. Unknown prerequisites are hypotheses, not prohibitions.

In addition to reasoning and action, return:
"frame": {"goal": "desired outcome", "method": "current way to achieve it",
          "missing": "next unresolved prerequisite or uncertainty",
          "expected": "observable result expected from the action"},
"upsert": [{"key": "short stable topic", "kind": "rule|discovery|milestone",
            "claim": "concise fact with its scope/conditions",
            "quote": "exact contiguous quote from a visible observation"}],
"forget": ["keys of facts contradicted or superseded by new evidence"].
Use at most 3 upserts and short quotes. Preserve useful commands, learned mechanics,
locations and task requirements; avoid copying transient status or obvious observations.
Only record observed evidence, never reasoning as evidence. Existing facts persist unless
replaced/forgotten. A rule is conditional on the quoted situation, not a universal ban.
The frame is a revisable hypothesis, not an asserted fact. Empty updates are allowed.
"""


class Notebook:
    def __init__(self):
        self.facts = {}
        self.frame = {}
        self.history = []
        self.observations = []
        self.audit = []

    def prompt(self, observation):
        self.observations.append(observation)
        return ("Persistent public evidence (conditional; check freshness):\n" +
                json.dumps(list(self.facts.values()), ensure_ascii=False) +
                "\nRevisable goal/method frame:\n" + json.dumps(self.frame, ensure_ascii=False) +
                "\nRecent interaction:\n" + "\n".join(self.history[-5:]) +
                "\nMy Current Observation: " + observation +
                "\nUpdate the notebook from observed feedback and choose ONE action. Return only JSON.")

    def update(self, parsed, observation, step):
        visible = self.observations
        events = []
        # Forgetting is a model decision, logged for retrospective error analysis.
        forget = parsed.get("forget", [])
        if isinstance(forget, list):
            for key in forget:
                if isinstance(key, str) and key in self.facts:
                    del self.facts[key]
                    events.append({"forgot": key})
        updates = parsed.get("upsert", [])
        if isinstance(updates, list):
            for fact in updates[:3]:
                valid = isinstance(fact, dict) and all(isinstance(fact.get(k), str)
                    for k in ("key", "kind", "claim", "quote"))
                if not valid:
                    events.append({"rejected": "schema"})
                    continue
                key, quote = fact["key"].strip(), fact["quote"]
                if (not key or len(key) > 100 or len(fact["claim"]) > 600 or
                    fact["kind"] not in ("rule", "discovery", "milestone") or
                    not 12 <= len(quote) <= 1000 or not any(quote in o for o in visible)):
                    events.append({"rejected": "untraceable_or_oversized", "key": key})
                    continue
                source = max(i for i, o in enumerate(visible) if quote in o)
                self.facts[key] = {k: fact[k] for k in ("key", "kind", "claim", "quote")}
                self.facts[key].update(source_observation=source, updated=step)
                events.append({"accepted": key})
        # Bounded, deterministic eviction; never silently claim unlimited persistence.
        while len(self.facts) > 32 or sum(len(json.dumps(v)) for v in self.facts.values()) > 18000:
            key = min(self.facts, key=lambda k: self.facts[k]["updated"])
            del self.facts[key]
            events.append({"evicted": key})
        frame = parsed.get("frame", {})
        if isinstance(frame, dict) and all(isinstance(frame.get(k), str) and len(frame[k]) <= 700
                                         for k in ("goal", "method", "missing", "expected")):
            self.frame = {k: frame[k] for k in ("goal", "method", "missing", "expected")}
        else:
            events.append({"rejected": "frame_schema"})
        self.history.append(observation + "\nReasoning: " + parsed["reasoning"] + "\nAction: " + parsed["action"])
        self.history = self.history[-5:]
        self.audit.append({"step": step, "events": events})

    def state(self):
        return vars(self)

    def load(self, state):
        self.__dict__.update(state)


class PublicAgent:
    def __init__(self, llm, system_prompt):
        self.llm = llm
        # Replace the exact-keys instruction to permit notebook updates.
        self.system_prompt = system_prompt.replace("exactly these keys", "these required keys") + PUBLIC_INSTRUCTION
        self.notebook = Notebook()

    def act(self, obs):
        result = self.llm.generate(user_prompt=self.notebook.prompt(obs["text"]), system_prompt=self.system_prompt)
        parsed = json.loads(result["response"])
        self.notebook.update(parsed, obs["text"], self.llm.step)
        return parsed["action"].strip(), result["num_input_tokens"], result["num_output_tokens"], result["response"]
