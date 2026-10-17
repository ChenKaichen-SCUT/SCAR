#!/bin/bash
set -euo pipefail
ROOT=/root/scar_evidence_repair_20261017
BASE=/root/scar_research_20261015
export PYTHONPATH="$ROOT/followup_code:$BASE/source/AgentOdyssey:$BASE/causal_adapter_20261016/deps"
export AGENTODYSSEY_ROOT="$BASE/source/AgentOdyssey"
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
cd "$ROOT/followup_code"
"$BASE/venv/bin/python" -m pytest scar_public/test_evidence_repair.py scar_public/test_resource_evidence.py scar_public/test_resource_trial.py scar_public/test_resource_competition.py scar_public/test_causal_model.py scar_public/test_protocol.py -q > "$ROOT/logs/followup_tests.log" 2>&1
REV=$(sha256sum source_manifest.json | cut -d ' ' -f 1)
exec "$BASE/venv/bin/python" -m scar_public.run run --root "$ROOT/runtime" \
  --stage attributes_structured --method evidence_repair_v11 --game metropolis --steps 300 \
  --evidence-mode structured --evidence-context-scope attributes \
  --key "$BASE/private/deepseek.key" --revision "source-manifest-sha256:$REV" \
  --fork-checkpoint "$ROOT/runtime/structured/evidence_repair_v11/metropolis/checkpoints/0075"
