Compact progress study: exact frozen evidence and reproduction

The open manuscript was not edited. Read ../COMPACT_PROGRESS_NOTES.txt first.
Results are in ../results/2026-10-16-compact-progress/.
Three versions are preserved; do not run an old frozen manifest with current code.

1. Extract reproduction.zip to a fresh directory.
2. python restore.py v2 /path/to/restored
   This restores exact top-level scar_public source bytes, the three raw result
   directories in frozen_results/, and diagnostic/analysis scripts.
3. Install Python dependencies z3-solver, numpy and scipy. For the server runs:
   Python 3.10.12, z3 4.8.12, numpy 1.21.5, scipy 1.8.0. Platform/core details are
   in the per-batch environment.json files. Local diagnostics used Python 3.13.12
   and z3 5.0.0; do not compare local timings with server total times.
4. Fetch the pinned public inputs into CACHE using input_sources.json. Hashes
   are mandatory. Inputs are not bundled; no credential is needed.
5. From the restored root, on Linux:
   python -m scar_public.study_reachable_labels --cache CACHE --output NEW_OUTPUT --suite development --modes compact_count compact_relation compact_matching
   Use suite reused_author for the six previously held-out Rover configurations.
   V2 scale: --suite compact_scale --modes compact_count compact_relation amortized_relation resource_tree
   V3 modes: compact_continue factored_relation factored_continue
   Run suites sequentially: each runner already uses eight distinct physical cores.
   Original results have a 30 second timeout, 2GiB memory cap, one repetition,
   all preprocessing included and no LLM/API calls.

Rebuild aggregate summaries with current checkout analysis script:
 python -m scar_public.experiments.analyze_compact_progress EVIDENCE_DIR OUTPUT_DIR
EVIDENCE_DIR contains v1/results_dev, v1/results_reused, and corresponding v2/v3;
only v2 also has results_scale. The ZIP contains these files under evidence/.

Cold query ablation with v3 restored source:
 python -m scar_public.experiments.ablate_progress_query CACHE diagnostics/interrupted_query.json query_result.json
The diagnostic is selected development evidence, not a fresh benchmark. It
demonstrates capacity separation but does not establish a production speedup.
The file relation_certificates.json is intentionally empty: zero NEW relation
certificates completed in the 167 server full runs. The separate offline query
certificate is in query_factor_ablation.json and the diagnostic evidence.

Run correctness checks with pytest:
 python -m pytest scar_public/test_compact_progress.py scar_public/test_factored_progress.py scar_public/test_progress_carrier.py scar_public/test_reachable_labels.py scar_public/test_theory_strengthening.py scar_public/test_label_comparison.py -q
29 passed on the recorded final source. Tests include all small candidate
restrictions against the materialized recurrence, independent exact planning,
policy replay, a genuine separation, full-pattern collapse, and interruption.
