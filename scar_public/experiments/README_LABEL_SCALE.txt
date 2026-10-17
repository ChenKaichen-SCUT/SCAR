Frozen labelled-abstraction comparison and public scaling study

The mathematical comparison in paper/coverage_theory.tex specifies the
cross-world LUG goal-level test, including pairwise mutex reasoning. It proves
incomparability with existential candidate coverage. This is not a claim to
reimplement or outperform every LUG heuristic or the POND planner.

Matched-engine experiment:
 python -m scar_public.study_label_scale --cache PATH --output PATH --freeze
 python -m scar_public.study_label_scale --cache PATH --output PATH
 python scar_public/experiments/analyze_label_scale.py RESULT_PATH
 python -m scar_public.experiments.audit_label_inputs CACHE_PATH RESULT_PATH

The manifest hashes every top-level scar_public Python source. Reproduction
requires the frozen source snapshot, not a mixture with later top-level files.
Analysis/diagnostic scripts in this subdirectory are outside that solver hash.

42 configurations = 21 author-published source pairs x original-structure and
explicit a16s1 overlay. Five methods, 30 seconds, 2 GiB, H=60, <=2048 initial
models and <=20000 grounded actions. Finite strong-policy objective, optimal
worst-case action count. Check every returned policy with the exact interpreter.
No LLM calls. No prescribed random seeds. Separate independent processes pinned
to eight physical cores. Parsing, grounding, initialization and inference are
included. Imports/startup are separately recorded. Failure to finish means
UNKNOWN, not infeasibility.

IMPORTANT SOURCE AUDIT:
The frontend interprets the explicitly supplied domain/problem pair and does
not check that the problem's :domain name matches the supplied domain name.
The author archive has inconsistent names in BT and Medical. Interpret those
16 configurations as declared paired-file variants, not untouched strict PDDL.
The domain-name-coherent subset has 24 configurations, 22 supported. Ring-3 has
an extra closing parenthesis and is rejected, not silently repaired. Ring-6
exceeds the exact enumeration cap. Name coherence is not a complete PDDL
conformance certification. Preserve all rows and report both strata. This
quality audit was performed after the first outcome inspection.

TIMING:
The first 210-run batch is a pilot: an approximately two-second legacy POND
build overlapped its startup. Do not use its wall times for the primary table.
An unchanged second batch runs after all builds/native diagnostics finish,
with no competing computation. The second manifest has the same solver/input
hashes. This is timing validation, not a new independent instance cohort.
One isolated timing observation per case is still insufficient for claims of
small statistically significant speed differences.

EXTERNAL POND:
SVN revision 313 builds with portability repairs. The 2005 benchmark dialect
is not directly accepted by the 2011 parser. Native input failures are NOT
planner losses. The grounded adapter is restricted to resource-free conformant
tasks; its roundtrip is tested with our interpreter. The built native executable
still fails a solvable two-world/two-action smoke test (LUGRP A*: assertion;
LUGLEVEL with mutex: crash; EHC: invalid empty plan). Therefore no native POND
time, success count, or optimality assertion belongs in the comparison table.
The regular -mutex flag is not the theoretical Appendix-B cross-world variant.
Do not repeatedly run a nonconforming executable on a large benchmark suite.

The experiment distinguishes scalar coverage C0 from lineage coverage CL on
the same selected projection. Any improvements shared by both belong to their
common coverage relaxation. A theoretical separation of CL does not imply a
practical independent CL gain on these public tasks.
