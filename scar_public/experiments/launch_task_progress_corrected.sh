#!/usr/bin/env bash
set -euo pipefail
BASE=/root/scar_research_20261015
ROOT=/root/scar_task_progress_20261017
export PYTHONPATH="$ROOT/code_v3:$BASE/source/AgentOdyssey:$BASE/causal_adapter_20261016/deps"
export AGENTODYSSEY_ROOT="$BASE/source/AgentOdyssey"
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
cd "$ROOT/code_v3"
for g in remnant mark metropolis; do
  "$BASE/venv/bin/python" -m scar_public.experiments.run_task_progress --root "$ROOT/corrected/$g" --game "$g" --initial "$BASE/runtime/initial/$g/initial.pkl" --key "$BASE/private/deepseek.key" --arms observe --reuse-api "$ROOT/ablation/$g/api" >"$ROOT/logs/corrected_$g.log" 2>&1 &
done
wait
