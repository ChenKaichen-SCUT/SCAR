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
