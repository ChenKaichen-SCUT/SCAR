#!/bin/bash
set -euo pipefail
ROOT=/root/scar_method_repair_20261017
BASE=/root/scar_research_20261015
export PYTHONPATH="$ROOT/code:$BASE/source/AgentOdyssey:$BASE/causal_adapter_20261016/deps"
export AGENTODYSSEY_ROOT="$BASE/source/AgentOdyssey"
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
cd "$ROOT/code"
REV=$(sha256sum source_manifest.json | cut -d ' ' -f 1)
for GAME in remnant mark metropolis; do
  "$BASE/venv/bin/python" -m scar_public.run run --root "$ROOT/runtime" \
    --stage full_clock --method method_repair_v12 --game "$GAME" --steps 300 \
    --evidence-mode structured --evidence-context-scope clock \
    --key "$BASE/private/deepseek.key" --revision "source-manifest-sha256:$REV" \
    > "$ROOT/logs/full_${GAME}.log" 2>&1 &
done
wait
