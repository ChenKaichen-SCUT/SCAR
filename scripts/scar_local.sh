#!/usr/bin/env bash
set -euo pipefail
SCAR_PROJECT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
SCAR_DEPS="${SCAR_DEPENDENCIES:-$(dirname -- "$(dirname -- "$SCAR_PROJECT")")/scar_dependencies}"
SCAR_PYTHON="${SCAR_PYTHON:-$SCAR_DEPS/venv/bin/python}"
export AGENTODYSSEY_ROOT="${AGENTODYSSEY_ROOT:-$SCAR_DEPS/agentodyssey}"
export PYTHONPATH="$SCAR_PROJECT:$AGENTODYSSEY_ROOT${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONHASHSEED=0 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export PYTHONDONTWRITEBYTECODE=1
if [[ ! -x "$SCAR_PYTHON" ]]; then
  printf 'Python environment missing: %s\n' "$SCAR_PYTHON" >&2
  exit 1
fi
cd -- "$SCAR_PROJECT"
exec "$SCAR_PYTHON" -m scar_local "$@"
