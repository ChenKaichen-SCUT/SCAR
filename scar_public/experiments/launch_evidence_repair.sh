#!/bin/bash
set -euo pipefail
ROOT=/root/scar_evidence_repair_20261017
BASE=/root/scar_research_20261015
export PYTHONPATH="$ROOT/code:$BASE/source/AgentOdyssey:$BASE/causal_adapter_20261016/deps"
export AGENTODYSSEY_ROOT="$BASE/source/AgentOdyssey"
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
cd "$ROOT/code"
mkdir -p "$ROOT/logs"
"$BASE/venv/bin/python" -m pytest scar_public/test_evidence_repair.py scar_public/test_resource_evidence.py scar_public/test_resource_trial.py scar_public/test_resource_competition.py scar_public/test_causal_model.py scar_public/test_protocol.py -q > "$ROOT/logs/tests.log" 2>&1
"$BASE/venv/bin/python" -m scar_public.run prepare --root "$ROOT/runtime" > "$ROOT/logs/prepare.log" 2>&1
REV=$(sha256sum source_manifest.json | cut -d ' ' -f 1)
for game in remnant mark metropolis; do
  for arm in none prompt cache structured; do
    nohup "$BASE/venv/bin/python" -m scar_public.run run --root "$ROOT/runtime" \
      --stage "$arm" --method evidence_repair_v11 --game "$game" --steps 300 \
      --evidence-mode "$arm" --key "$BASE/private/deepseek.key" \
      --revision "source-manifest-sha256:$REV" > "$ROOT/logs/${game}_${arm}.log" 2>&1 < /dev/null &
    echo "$!" > "$ROOT/logs/${game}_${arm}.pid"
    echo "Started $game $arm PID $!"
  done
done
