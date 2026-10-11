#!/usr/bin/env bash
set -euo pipefail
TASK_ROOT="${SCAR_WORKSPACE:-/root/scar_workspace}"
UPSTREAM_COMMIT=248430692a9d4a61d38c6c03ab2126287faaf450
mkdir -p "$TASK_ROOT/dependencies" "$TASK_ROOT/runtime"
if [ ! -d "$TASK_ROOT/dependencies/agentodyssey/.git" ]; then
  git clone https://github.com/agentodyssey/agentodyssey.git "$TASK_ROOT/dependencies/agentodyssey"
fi
git -C "$TASK_ROOT/dependencies/agentodyssey" checkout "$UPSTREAM_COMMIT"
uv venv --python 3.12 "$TASK_ROOT/venv"
uv pip install --python "$TASK_ROOT/venv/bin/python" torch --index-url https://download.pytorch.org/whl/cpu
uv pip install --python "$TASK_ROOT/venv/bin/python" gymnasium termcolor psutil openai numpy pytest sentence-transformers
uv pip install --python "$TASK_ROOT/venv/bin/python" --no-deps -e "$TASK_ROOT/dependencies/agentodyssey"
uv pip install --python "$TASK_ROOT/venv/bin/python" --no-deps -e "$TASK_ROOT/project"
uv pip freeze --python "$TASK_ROOT/venv/bin/python" > "$TASK_ROOT/project/results/environment-lock.txt"
