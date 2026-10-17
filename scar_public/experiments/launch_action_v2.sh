#!/bin/bash
set -euo pipefail
ROOT=/root/scar_action_repair_20261017
BASE=/root/scar_research_20261015
export PYTHONPATH="$ROOT/code_v2:$BASE/source/AgentOdyssey:$BASE/causal_adapter_20261016/deps"
export AGENTODYSSEY_ROOT="$BASE/source/AgentOdyssey"
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
cd "$ROOT/code_v2"
COMMON=(--root "$ROOT/pairs_v2/metropolis" --checkpoint /root/scar_evidence_repair_20261017/runtime/attributes_structured/evidence_repair_v11/metropolis/checkpoints/0093
 --key "$BASE/private/deepseek.key" --scope attributes --steps 300 --reuse-api "$ROOT/pairs/metropolis/api"
 --stop-report 'Stage completed: Obtain and equip a weapon before engaging enemies.')
"$BASE/venv/bin/python" -m scar_public.experiments.paired_action_repair "${COMMON[@]}" --arms execute > "$ROOT/logs/v2_metropolis_execute.log" 2>&1 &
EXEC_PID=$!
"$BASE/venv/bin/python" -m scar_public.experiments.paired_action_repair \
 --root "$ROOT/pairs_v2/remnant" --checkpoint /root/scar_method_repair_20261017/runtime/full_clock/method_repair_v12/remnant/checkpoints/0090 \
 --key "$BASE/private/deepseek.key" --scope clock --steps 300 --reuse-api "$ROOT/pairs/remnant/api" \
 --stop-report 'Stage completed. The weight in your hand is steady.' > "$ROOT/logs/v2_remnant.log" 2>&1 &
REM_PID=$!
wait "$EXEC_PID"
# The observe replay must not outrun its already paid cache source.
while ! "$BASE/venv/bin/python" -c 'import json,sys; sys.exit(not json.load(open(sys.argv[1]))["complete"])' "$ROOT/pairs/metropolis/observe/current.json"; do sleep 5; done
"$BASE/venv/bin/python" -m scar_public.experiments.paired_action_repair "${COMMON[@]}" --arms observe > "$ROOT/logs/v2_metropolis_observe.log" 2>&1
wait "$REM_PID"
