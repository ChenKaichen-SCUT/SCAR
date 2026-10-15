# Public-state experiment protocol (2026-10-15)

This is a development study, **not a TTCL challenge submission**. TTCL uses its specified
Qwen models and 500 steps; this authorized development phase uses DeepSeek and 300 steps.
Scores are still calculated with the upstream official `challenge_eval.py`.

## Frozen comparison

- Engine: AgentOdyssey `248430692a9d4a61d38c6c03ab2126287faaf450`.
- Games: remnant, mark, metropolis; one rollout each, up to 300 environment actions.
- Methods: upstream STM (5 turns), upstream LongContext, ReflAct adaptation (full context),
  SCAR PublicState v1 (5 turns plus a persistent evidence notebook and goal/method frame).
- Model: `deepseek-flash`, official endpoint, thinking disabled, temperature 0.7,
  top_p 0.8, presence_penalty 0, output cap 1536; actual returned model logged per request.
- No manually selected environment seed. One fresh `seed=None` environment per game;
  its complete initial snapshot/RNG is reused by all methods and subsequent iterations.
  The drawn seed and snapshot hash are recorded. Memory resets between games.
- Each step uses one model request, except identical shared JSON-format/network retries.
  Invalid game actions consume a step. There is no applicability oracle or semantic repair.
- API concurrency ceiling 64. Initially 12 independent game processes; each game is sequential.
- Baselines are frozen after this round. Changing only our method does not rerun baselines.
  A common infrastructure defect would require reporting and correcting affected results.

## Implementation fidelity

STM and LongContext use the actual upstream factories. A shared config supplies the missing
`construct_user_prompt_long_context` method used by upstream STM, and routes both to the same
audited provider. Reflection/summarization options on LongContext are off.

ReflAct is a paper-derived AgentOdyssey adaptation, not an author-released AO implementation.
It replaces next-action explanation with goal-relative state reflection and keeps full history.
Source: [ReflAct, Section 4 and Appendix K](https://arxiv.org/html/2505.15182v2).
The original instruction is used; the output is serialized into the shared JSON fields.
No game demonstrations or game-specific solution knowledge are added.

PublicState v1 keeps at most 32 facts / 18,000 serialized characters, evicting least recently
updated entries. Each stored claim requires a verbatim quote in an observation already received.
This checks provenance **only**, not entailment or freshness. Facts carry their observation index.
The model may explicitly retract a fact. The current goal, method, missing condition and expected
feedback are hypotheses, revised each turn. No inferred condition blocks an action in code.
All updates are made in the action-generating request; there is no extra reflection call.

## Information boundary and resumability

Agent inputs are observation text and default action signatures. Evaluator state, reward
breakdowns, hidden quest progress, game rules and snapshots are never passed to the agent.
The logical agent is separate from the physical environment agent. Public memory and physical
environment/RNG are checkpointed together after each step; a completed-response cache prevents
recharging an already completed request on resume. A process lock prevents duplicate workers.
Each run manifest pins source revision, initial snapshot, model and inference settings.

## Accounting and stopping

All attempts (including retries) are logged. Usage-reported tokens are priced conservatively
at peak rates (USD/M tokens: cache hit .006, miss .30, output 1.20) from the official pricing page
checked 2026-10-15. Unknown-charge network/server failures are listed separately, never counted
as zero cost or falsely presented as invoice totals. The initial connectivity probe is separate.
Credentials live outside the repository, are read at request time, and are never serialized.

This round is exploratory: one run does not estimate variance or establish significance.
Primary outcome is the unweighted mean of raw main-quest reward; auxiliary outcomes use the
official supplementary sum. Fewer repeated actions or invalid actions are diagnostics, not success.
Inspect full trajectories after the comparison. Only pursue a further version when a concrete
failure mechanism predicts a main-task improvement. Stop a hypothesis branch after two targeted
revisions fail to improve its intended main-task bottleneck; report failed attempts as well.
Formal claims require independent replications and held-out generalization, not best-run selection.

## Run

Set `AGENTODYSSEY_ROOT` and `PYTHONPATH` to the pinned engine checkout and this source tree.
Install Python 3.12, gymnasium, termcolor, numpy, psutil, cloudpickle, requests and CPU torch.

```sh
python -m pytest scar_public/test_protocol.py -q
python -m scar_public.run prepare --root /path/to/runtime
python -m scar_public.run run --root /path/to/runtime --stage round1 --method stm \
  --game remnant --key /private/deepseek.key --revision COMMIT --steps 300
```

Use immutable deployed source directories. Keep raw API logs and binary snapshots outside Git;
commit source, protocol, summarized results and meaningful failure analysis.

## Revision v2: evidence-only memory (specified while round 1 runs)

Observed mechanism: in metropolis, PublicState v1 stayed at quest reward 4 from step 11
through at least step 111. Its notebook repeatedly inferred that an NPC's flavor description
required rewriting a document. The supporting quote established neither that requirement nor
that method. In the same initial world, ReflAct advanced by testing a direct alternative
interpretation of the publicly stated delivery goal. In remnant, v1 also deleted useful
mechanics when revising transient post-death state. These are observation-grounded diagnoses,
not hidden-engine solutions.

Replace the synthesized fact notebook with an append-only ledger of actions and verbatim
observation changes. Full observations remain in saved state; the prompt shows the initial
observation, changed lines with +/- markers, and the complete current observation. Removed
lines mean disappearance from the report, not necessarily a state reversal. No model-written
factual claim or past reasoning is promoted into this ledger; no learned fact eviction occurs.
The tentative execution frame has a verbatim task anchor, current method, assessment of the
last prediction, and expected observable result. The method can change without changing the
task's stated outcome. All operations remain in one request per action, with identical API
settings and initial snapshots; no game names or solution actions enter the algorithm.

Hypothesis: this redesign should reduce detours driven by invented prerequisites and improve
metropolis main-quest reward beyond v1's current plateau, while preserving useful public
mechanics for remnant/mark. This changes memory representation and execution prompting
together; a positive result alone would **not** isolate either component's causal contribution.
Run only `evidence_v2` on all three games for 300 steps in `round2`, without rerunning baselines.
The incomplete round-1 scores above are diagnostic checkpoints, not final comparison scores.

## Shared transport amendment

ReflAct/remnant stopped after 207 actions because three consecutive valid JSON responses
omitted `action`. They were not truncated and all are retained and charged in the audit.
The retry allowance is extended uniformly to six, with an explicit JSON shape after the
third malformed response. The first three requests are byte-for-byte unchanged. Completed
rollouts never reached this limit, so their decisions are unaffected and they are not rerun.
Any interrupted rollout resumes from its last checkpoint and reuses the three cached
responses before the additional formatting-only requests. No game feedback is introduced.
Original algorithm revision and amended transport revision are recorded separately.

## Revision v3: method-level feasibility

At v2/metropolis steps 207–211 the actor repeatedly dropped and picked up crafting materials:
two held items filled capacity, while its selected recipe needed three ingredient units.
Each local prediction (e.g. dropping frees a slot) was true, but the chosen sequence undid a
previous prerequisite. This is a distinct failure from forgetting or hallucinated memory.

Keep the evidence ledger and API unchanged; replace the action-success framing with a
method-level required arrangement and feasibility assessment. It must consider whether inputs
for one atomic operation can coexist under observed constraints, and whether preparation
reverses earlier preparation. This is scoped to the current method, not a global veto on the
goal, and does not require all resources for a multi-stage quest to coexist. No resource counts,
recipes, container names, solution actions or hidden-state checks are encoded in the prompt.

Run three fresh 300-step rollouts from the same shared initial snapshots in `round3`.
Hypothesis: fewer preparation cycles should translate into greater main-task reward, particularly
in metropolis and remnant. If only repetition metrics improve, regard the hypothesis as not
supported on the main task. V3 remains an LLM-interpreted contract, not a sound symbolic planner.
Finish this phase after this revision and report every version; do not keep tuning indefinitely.

## User-authorized continuation: task-bound trials (v4)

The user requested further diagnosis and improvement after the completed v3 report. Existing
baselines and all completed runs remain frozen. This is a new development phase, not an extension
of the previous claim or a replacement for its negative findings.

V3/metropolis repeatedly confused two public phrases serving different task roles. At checkpoint
62, an offline same-state action substitution yields quest 8 -> 10 for the task-bound phrase versus
8 -> 8 for the original phrase. At checkpoint 255 both phrases fail because the document already
contains other text and writing appends. These scripted, source-informed mechanistic replays are
NOT autonomous agent results. They do not enter the agent's inputs, memory or policy.

V4 replaces the v2+v3 prompt with one task-bound execution-trial representation: a quoted goal,
quoted argument bindings, a method's joint arrangement, an observable target test distinct from
the next command effect, and reviews of eight recent trials. Quotes are checked for provenance
only. Reviews are explicitly tentative model interpretations; a review's evidence must occur in
the current observation. No inferred review creates a hard action veto. No game-specific names,
phrases, recipes or solutions are encoded. One API call per action, shared inference settings.

First compare v3 and v4 for 30 actions from each of two identical v3 checkpoints: metropolis 62
(before the mistaken binding) and 178 (already contaminated document, repeated failed method).
Each pair restores identical environment, RNG and inherited public memory. Additional v4 fields
start empty. Record cost and failures separately; these are targeted diagnostics, not 300-step
benchmark scores. Two fresh v3 continuations are algorithm controls, not rerun baselines.

Only if these diagnostics show actual task gain or a directly observed repair of the intended
bottleneck, run v4 once from each shared initial world for the full 300 steps. Compare all three
scores with v3 and frozen baselines; retain regressions. Stop after this candidate unless a specific
implementation defect invalidates the test. Do not infer stable performance or novelty from it.
