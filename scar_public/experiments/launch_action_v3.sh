#!/bin/bash
set -euo pipefail
ROOT=/root/scar_action_repair_20261017
BASE=/root/scar_research_20261015
export PYTHONPATH="$ROOT/code_v3:$BASE/source/AgentOdyssey:$BASE/causal_adapter_20261016/deps"
export AGENTODYSSEY_ROOT="$BASE/source/AgentOdyssey"
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
cd "$ROOT/code_v3"
"$BASE/venv/bin/python" -m scar_public.experiments.paired_action_repair \
  --root "$ROOT/pairs_v3/metropolis" --checkpoint /root/scar_evidence_repair_20261017/runtime/attributes_structured/evidence_repair_v11/metropolis/checkpoints/0093 \
  --key "$BASE/private/deepseek.key" --scope attributes --steps 300 --reuse-api "$ROOT/pairs_v2/metropolis/api" \
  --stop-report 'Stage completed: Obtain and equip a weapon before engaging enemies.' > "$ROOT/logs/v3_metropolis.log" 2>&1 &
"$BASE/venv/bin/python" -m scar_public.experiments.paired_action_repair \
  --root "$ROOT/pairs_v3/remnant" --checkpoint /root/scar_method_repair_20261017/runtime/full_clock/method_repair_v12/remnant/checkpoints/0090 \
  --key "$BASE/private/deepseek.key" --scope clock --steps 300 --reuse-api "$ROOT/pairs_v2/remnant/api" \
  --stop-report 'Stage completed. The weight in your hand is steady.' > "$ROOT/logs/v3_remnant.log" 2>&1 &
wait
