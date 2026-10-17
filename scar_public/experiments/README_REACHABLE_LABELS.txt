Reproduction of candidate-to-progress experiments

The result directory is scar_public/results/2026-10-16-reachable-labels.
The reproduction ZIP deduplicates exact source bytes by SHA-256. Extract it,
then run `python restore.py holdout DESTINATION` (or development_v1/development_v2).
This restores each frozen source tree and its raw runs.jsonl under frozen_results.
Use the restored tree in an isolated directory before rerunning:
the manifest hashes all top-level scar_public/*.py, including tests. Mixing a
later source tree with a frozen manifest intentionally fails the hash check.
The current runner corrects the frozen protocol's <= wording to SOFT inference
budgets; a single atomic SAT call can exceed the checkpoint deadline.

Cached sources (SHA-256 pinned in loaders):
 https://rakaposhi.eas.asu.edu/belief-search/BKS_jair_domains.tgz
 https://fai.cs.uni-saarland.de/hoffmann/ff/contff-tests.tgz
CPOR Localize source is the previously pinned revision in benchmark_suite.py.
No credentials or API keys are required for these planning experiments.

Linux with numpy, scipy, z3-solver:
 python -m scar_public.study_reachable_labels --cache CACHE --output NEW_PATH --freeze
 python -m scar_public.study_reachable_labels --cache CACHE --output NEW_PATH

Development v2 uses:
 --modes reachable_count reachable_relation carrier_count carrier_relation
The unchanged fixed/resource baselines from development v1 are reused.

Held-out author cases use:
 --suite holdout --modes amortized_count amortized_relation resource_tree carrier_count carrier_relation
These six configurations are three source tasks, each with two budget settings;
they are related to the development family and are now consumed as validation.

Reproduce audits/analysis without running planners:
 python -m scar_public.experiments.audit_reachable_inputs CACHE OUTPUT_JSON
 python -m scar_public.experiments.analyze_reachable_labels RAW_RESULT_DIR OUTPUT_DIR

Run validation:
 python -m pytest scar_public/test_reachable_labels.py scar_public/test_progress_carrier.py scar_public/test_theory_strengthening.py scar_public/test_label_comparison.py -q

Never count UNKNOWN_TIMEOUT as infeasible. NO_STRONG_POLICY_WITHIN_H only rejects
the declared horizon. Every returned policy is replayed by the exact interpreter.
All timings include parsing, grounding, construction, optional inference and
exact search. Imports are separately measured. One run per case; no confidence
intervals or small timing-effect claims. Zero LLM API calls.
