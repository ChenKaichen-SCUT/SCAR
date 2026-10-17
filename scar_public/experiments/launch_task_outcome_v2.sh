#!/bin/bash
set -euo pipefail
ROOT=/root/scar_task_outcome_20261017
BASE=/root/scar_research_20261015
export PYTHONPATH="$ROOT/code_v2:$BASE/source/AgentOdyssey:$BASE/causal_adapter_20261016/deps"
export AGENTODYSSEY_ROOT="$BASE/source/AgentOdyssey"
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
cd "$ROOT/code_v2"
for game in remnant mark metropolis; do
  "$BASE/venv/bin/python" -m scar_public.experiments.full_task_outcome --root "$ROOT/corrected/$game" --initial "$BASE/runtime/initial/$game/initial.pkl" --game "$game" --key "$BASE/private/deepseek.key" --steps 300 --arms v15 --reuse-api "$ROOT/full/$game/api" > "$ROOT/logs/v2_$game.log" 2>&1 &
done
wait
