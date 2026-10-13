#!/usr/bin/env bash
set -euo pipefail
SCAR_PROJECT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
SCAR_DEPS="${SCAR_DEPENDENCIES:-$(dirname -- "$(dirname -- "$SCAR_PROJECT")")/scar_dependencies}"
export AGENTODYSSEY_ROOT="${AGENTODYSSEY_ROOT:-$SCAR_DEPS/agentodyssey}"
export PYTHONPATH="$SCAR_PROJECT:$AGENTODYSSEY_ROOT${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONHASHSEED=0 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1
SCAR_COMMAND="${1:-}"
case "$SCAR_COMMAND" in
  preflight|freeze|batch|run|replay|analyze|verify) shift ;;
  *) printf 'Usage: bash scar_stage21/run.sh {preflight|freeze|batch|run|replay|analyze|verify} [args]\n' >&2; exit 2 ;;
esac
cd -- "$SCAR_PROJECT"
exec "${SCAR_PYTHON:-$SCAR_DEPS/venv/bin/python}" -m "scar_stage21.$SCAR_COMMAND" "$@"
