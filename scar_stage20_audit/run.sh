#!/usr/bin/env bash
set -euo pipefail
SCAR_AUDIT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
SCAR_DEPS="${SCAR_DEPENDENCIES:-$(dirname -- "$(dirname -- "$SCAR_AUDIT_ROOT")")/scar_dependencies}"
export AGENTODYSSEY_ROOT="$SCAR_DEPS/agentodyssey"
export PYTHONPATH="$SCAR_AUDIT_ROOT:$AGENTODYSSEY_ROOT"
export PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1
cd -- "$SCAR_AUDIT_ROOT"
SCAR_AUDIT_PHASE="${1:?Usage: run.sh extract|branches|analyze|test|report|verify}"
case "$SCAR_AUDIT_PHASE" in
  extract|branches|analyze|test|report|verify) ;;
  *) echo "Unknown audit phase: $SCAR_AUDIT_PHASE" >&2; exit 2 ;;
esac
exec "$SCAR_DEPS/venv/bin/python" -m "scar_stage20_audit.$SCAR_AUDIT_PHASE"
