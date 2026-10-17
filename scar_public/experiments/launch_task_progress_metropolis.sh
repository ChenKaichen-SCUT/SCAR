#!/usr/bin/env bash
set -euo pipefail
BASE=/root/scar_research_20261015
ROOT=/root/scar_task_progress_20261017
export PYTHONPATH="$ROOT/code_v2:$BASE/source/AgentOdyssey:$BASE/causal_adapter_20261016/deps"
export AGENTODYSSEY_ROOT="$BASE/source/AgentOdyssey"
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
cd "$ROOT/code_v2"
"$BASE/venv/bin/python" -m scar_public.experiments.run_task_progress --root "$ROOT/selected_v2/metropolis" --game metropolis --initial "$BASE/runtime/initial/metropolis/initial.pkl" --checkpoint /root/scar_task_outcome_20261017/corrected/metropolis/v15/checkpoints/0145 --key "$BASE/private/deepseek.key" --reuse-api /root/scar_task_outcome_20261017/corrected/metropolis/api
