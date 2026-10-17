#!/usr/bin/env bash
set -euo pipefail
BASE=/root/scar_research_20261015
ROOT=/root/scar_task_progress_20261017
export PYTHONPATH="$ROOT/final_code:$BASE/source/AgentOdyssey:$BASE/causal_adapter_20261016/deps"
export AGENTODYSSEY_ROOT="$BASE/source/AgentOdyssey"
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
cd "$ROOT/final_code"
until "$BASE/venv/bin/python" -c 'import json,pathlib; r=pathlib.Path("/root/scar_task_progress_20261017"); p=[p for g in ("selected","selected_v2","full","ablation","corrected") for p in (r/g).glob("*/*/current.json")]; assert len(p)==14 and all(json.loads(x.read_text())["complete"] for x in p)' 2>/dev/null; do sleep 10; done
"$BASE/venv/bin/python" "$ROOT/analyze_task_progress.py" "$ROOT"
"$BASE/venv/bin/python" "$ROOT/diagnose_task_progress.py" "$ROOT"
"$BASE/venv/bin/python" -m scar_public.experiments.replay_task_progress "$ROOT" --initial-root "$BASE/runtime/initial"
"$BASE/venv/bin/python" -m scar_public.experiments.package_task_progress_results "$ROOT"
