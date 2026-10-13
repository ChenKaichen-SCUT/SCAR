# Stage17 offline diagnosis

Only saved data is read. All entry points deny Python socket connections. They do
not instantiate an API provider, change frozen algorithms, restart a failed model
run, or create Stage18 experiments. `input_manifest.json` fixes the 2,976 previously
tracked files at commit `edb56befb071d297663c6d1d1e833ba572f62330`.

Use the original Python 3.12 environment and engine revision from
`results/stage17/sources.json`. On the original server:

```bash
cd /root/scar_workspace/project
export AGENTODYSSEY_ROOT=/root/scar_workspace/dependencies/agentodyssey
export PYTHONHASHSEED=0 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export PYTHONPATH=.
/root/scar_workspace/venv/bin/python -m scar_stage17_diagnostics.counterfactual --site server
/root/scar_workspace/venv/bin/python -m scar_stage17_diagnostics.analyze
```

Locally substitute `/mnt/Space0/scar_dependencies/agentodyssey` and
`/mnt/Space0/scar_dependencies/venv/bin/python`, with `--site local`. Then:

```bash
python -m scar_stage17_diagnostics.report
python -m unittest scar_stage17_diagnostics.test_analysis
python -m scar_stage17_diagnostics.verify
```

Do **not** run `scar_stage17.run`, `batch`, or `publish` for this diagnosis.
Do not overwrite the original `per_task.json`, `analysis.json`, or raw run files.
The report generator combines computed data with explicit, reviewable evidence
annotations in `case_notes.json`. It does not invent diagnoses from success labels.

## Artifacts (`results/stage17/diagnostics`)

- `paired_24.csv`: exactly 24 fully paired wide rows; `per_run.csv/json`: 120 rows.
- `statistics.json`: all-method totals, four-way per-task paired outcomes, conditional
  action differences, disclosure coverage, controller and request statistics.
- `knowledge.json`: 120 complete disclosure timelines, initial and new recipes,
  checkpoints, first complete relation/quantity time, per-recipe craft latency,
  unknown quantity/station facts, explicit registration discrepancies.
- `model_context_evidence.jsonl.gz`: actual request IDs joined to prior native
  disclosures and attested system recipe records. Absence is a conservative
  literal-evidence result, not proof of semantic forgetting. A3 plan assertions
  and model guesses are never promoted to public evidence.
- `action_evidence.jsonl.gz`: all 5,042 actual actions, feedback, physical hashes,
  production/rejection metrics and native knowledge changes.
- `controller_audit.jsonl.gz`: all 635 SCAR proposals, S1/P1/P3 candidates, override
  provenance, partial public support and actual information/material/production gains.
- `counterfactual_local.jsonl.gz`: 635 factual replay rows and 471 alternate native
  single steps. Both local and server replay receipts contain the same body hash;
  the identical server body is not duplicated in Git. A server-only recomputation
  can use `counterfactual_server.jsonl.gz` for analysis.
- `response_errors.json`: all 108 anomalous attempts, original response bodies,
  exact saved request positions, offline schema/JSON failure diagnosis, recovery
  and terminal flags. Seven terminal runs include 21 final failed attempts.
- `failure_classifications.json`: all 14 SCAR failures and overlapping, qualified
  A–H tags, hand-audited action references and cross-method comparisons.
- `evidence_index.json` / `evidence_index.jsonl.gz` and `evidence/*.md`: per-task
  readable raw feedback for all five methods, stable per-action anchors, request
  IDs, and full counterfactual feedback for overridden SCAR actions.
- `validation.json`: input immutability, metric reconciliation, native hash parity,
  action/run counts and offline guard verification. `artifact_manifest.json` lists
  code, report, and data hashes (excluding itself).
- `server_analysis_receipt.json`: nine analysis artifacts independently recomputed
  on the server and byte-for-byte matched against local outputs.

## Measurement boundaries

Evaluation actions are 1-based; the common 28-step quarantine tutorial is step 0
for knowledge discovery. Terminated episodes carry their last observed coverage
forward to later budget cutoffs, with explicit termination/censoring fields.
Goal knowledge, static ancestral closure, and independently generated feasibility
witness scope are distinguished. Natural resources may bypass closure recipes.
Hidden recipes label necessary products/material scope only; their quantitative
and station conditions do not complete the knowledge table. Missing-station
feedback establishes a required subset, not an exhaustive station set. Without
an explicit complete disclosure, even a recipe with no actual station requirement
has unconfirmed station completeness. Public quantities must enumerate the
publicly disclosed ingredient relation; no hidden weights are read to fill gaps.

Counterfactuals restore native world and Python/NumPy RNG state and invoke one
saved proposal. Factual next-state hashes and feedback must exactly match before
proceeding. Terminal damage/death is tracked even when the engine revives the
agent to 100 HP. They identify local dimensions, not eventual success or a policy
ablation. Actual-controller advantages are also recorded; they must not be
subtracted from incomparable proposal benefits to infer total utility.

All costs derive from saved token usage under frozen protocol rates, not an
account invoice. No usage is missing this round. Retries and invalid responses
remain charged. No significance claim is made from a single model sample on
24 correlated tasks in two games.
