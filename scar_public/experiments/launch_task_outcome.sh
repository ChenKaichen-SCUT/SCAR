#!/bin/bash
set -euo pipefail
ROOT=/root/scar_task_outcome_20261017
BASE=/root/scar_research_20261015
export PYTHONPATH="$ROOT/code:$BASE/source/AgentOdyssey:$BASE/causal_adapter_20261016/deps"
export AGENTODYSSEY_ROOT="$BASE/source/AgentOdyssey"
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
cd "$ROOT/code"
for game in remnant mark metropolis; do
  "$BASE/venv/bin/python" -m scar_public.experiments.full_task_outcome --root "$ROOT/full/$game" --initial "$BASE/runtime/initial/$game/initial.pkl" --game "$game" --key "$BASE/private/deepseek.key" --steps 300 > "$ROOT/logs/$game.log" 2>&1 &
done
wait
