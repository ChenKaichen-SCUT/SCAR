#!/usr/bin/env bash
set -euo pipefail
BASE=/root/scar_research_20261015
ROOT=/root/scar_task_progress_20261017
export PYTHONPATH="$ROOT/code:$BASE/source/AgentOdyssey:$BASE/causal_adapter_20261016/deps"
export AGENTODYSSEY_ROOT="$BASE/source/AgentOdyssey"
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
cd "$ROOT/code"
for entry in remnant:0177 mark:0220 metropolis:0145; do
  g=${entry%:*}; cp=${entry#*:}; arms=(execute)
  if [ "$g" = remnant ]; then arms=(execute observe); fi
  "$BASE/venv/bin/python" -m scar_public.experiments.run_task_progress --root "$ROOT/selected/$g" --game "$g" --initial "$BASE/runtime/initial/$g/initial.pkl" --checkpoint "/root/scar_task_outcome_20261017/corrected/$g/v15/checkpoints/$cp" --key "$BASE/private/deepseek.key" --reuse-api "/root/scar_task_outcome_20261017/corrected/$g/api" --arms "${arms[@]}" >"$ROOT/logs/selected_$g.log" 2>&1 &
done
wait
