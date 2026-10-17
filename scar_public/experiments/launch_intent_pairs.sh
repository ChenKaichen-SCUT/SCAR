#!/bin/bash
set -euo pipefail
ROOT=/root/scar_intent_repair_20261017
BASE=/root/scar_research_20261015
export PYTHONPATH="$ROOT/code:$BASE/source/AgentOdyssey:$BASE/causal_adapter_20261016/deps"
export AGENTODYSSEY_ROOT="$BASE/source/AgentOdyssey"
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
cd "$ROOT/code"
"$BASE/venv/bin/python" -m scar_public.experiments.paired_intent_repair \
  --root "$ROOT/pairs/metropolis" --checkpoint /root/scar_method_repair_20261017/runtime/full_clock/method_repair_v12/metropolis/checkpoints/0061 \
  --key "$BASE/private/deepseek.key" --steps 300 \
  --stop-report 'Stage completed: Obtain and equip a weapon before engaging enemies.' > "$ROOT/logs/metropolis.log" 2>&1 &
"$BASE/venv/bin/python" -m scar_public.experiments.paired_intent_repair \
  --root "$ROOT/pairs/remnant" --checkpoint /root/scar_method_repair_20261017/runtime/full_clock/method_repair_v12/remnant/checkpoints/0090 \
  --key "$BASE/private/deepseek.key" --steps 300 \
  --stop-report 'Stage completed. The weight in your hand is steady.' > "$ROOT/logs/remnant.log" 2>&1 &
wait
