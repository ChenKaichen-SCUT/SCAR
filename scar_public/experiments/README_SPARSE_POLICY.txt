Sparse-policy evidence and reproduction

Read ../SPARSE_POLICY_NOTES.txt for claims, proofs, negative results, and sources.
Results: ../results/2026-10-16-sparse-policy/. The manuscript was not edited.

reproduction.zip contains:
 - exact frozen server top-level sources (snapshot v1), verified against all manifests;
 - final source snapshot for diagnostics (diagnostic_current), not a new server run;
 - raw 69 runs, manifests, environment metadata, logs;
 - Ring single-core, captured Cube queries, pair/compression diagnostics;
 - reproduction/analysis programs and public input URLs/hashes, no credentials.

Extract ZIP, then:
 python restore.py v1 /path/to/restored
Install z3-solver, numpy, scipy, pytest. Server was Python3.10.12, Z3 4.8.12,
numpy1.21.5, scipy1.8.0. Diagnostics were Python3.13.12 and Z3 5.0.0.
Download pinned datasets listed in input_sources.json into CACHE; hashes required.

Run the suites sequentially, each already uses eight separate physical cores:
 python -m scar_public.study_reachable_labels --cache CACHE --output NEW_DEV --modes sparse_policy sparse_fresh sparse_full
 python -m scar_public.study_reachable_labels --cache CACHE --output NEW_REUSED --suite reused_author --modes sparse_policy sparse_fresh sparse_full
 python -m scar_public.study_reachable_labels --cache CACHE --output NEW_SCALE --suite reused_scale --modes sparse_policy sparse_fresh sparse_full
30s process timeout, 2GiB cap, one run per configuration, same old search engine.
All these inputs were used in earlier development; none is an independent holdout.

Rebuild aggregate results using the final checkout analysis program:
 python -m scar_public.experiments.analyze_sparse_policy SPARSE_EVIDENCE PREVIOUS_COMPACT_EVIDENCE OUTPUT
SPARSE_EVIDENCE contains v1/results_dev, v1/results_reused, v1/results_scale.
The previous compact reproduction ZIP provides the PREVIOUS_COMPACT_EVIDENCE tree.
Baselines are read from frozen prior results, not rerun. The local snapshot is not
substituted for v1 when reporting its timings.

Restore diagnostic_current for new diagnostics and current tests:
 python -m scar_public.experiments.diagnose_sparse_cores CACHE ring.json
 python -m scar_public.experiments.diagnose_sparse_queries CACHE cube.json
 python -m scar_public.experiments.compress_sparse_cores CACHE cube.json compressed.json
The Cube search is a diagnostic rerun: soft budgets and Z3 versions can change
which queries get captured. Existing query states and core assumptions are saved.
Use compress_sparse_cores on the bundled cube_queries.json for the same contexts.
Do not interpret the timed diagnostic as a second independent server benchmark.
Rule replay reconstructs the encoder in a new solver; it is not an independently
verified SMT proof checker. Separate small-task/selected-pair tests use an unpruned
planning oracle. SAT optimistic traces are never returned as executable policies.

Tests (38 passed):
 python -m pytest scar_public/test_sparse_policy.py scar_public/test_compact_progress.py scar_public/test_factored_progress.py scar_public/test_progress_carrier.py scar_public/test_reachable_labels.py scar_public/test_theory_strengthening.py scar_public/test_label_comparison.py -q
Current compression includes explicit interruption safety, a compressible core,
and a real three-candidate conflict where every pair is feasible.
