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
if [ -f "$TASK_ROOT/project/requirements-cpu.lock" ]; then
  SCAR_TORCH_PIN=$("$TASK_ROOT/venv/bin/python" -c 'import sys; print(next(x.strip() for x in open(sys.argv[1]) if x.startswith("torch==")))' "$TASK_ROOT/project/requirements-cpu.lock")
  uv pip install --python "$TASK_ROOT/venv/bin/python" "$SCAR_TORCH_PIN" --index-url https://download.pytorch.org/whl/cpu
  "$TASK_ROOT/venv/bin/python" -c 'import sys; open(sys.argv[2], "w").writelines(x for x in open(sys.argv[1]) if not x.startswith("torch=="))' "$TASK_ROOT/project/requirements-cpu.lock" "$TASK_ROOT/dependencies/requirements-without-torch.txt"
  uv pip install --python "$TASK_ROOT/venv/bin/python" --no-deps -r "$TASK_ROOT/dependencies/requirements-without-torch.txt"
else
  uv pip install --python "$TASK_ROOT/venv/bin/python" torch --index-url https://download.pytorch.org/whl/cpu
  uv pip install --python "$TASK_ROOT/venv/bin/python" gymnasium termcolor psutil openai numpy pytest sentence-transformers
fi
uv pip install --python "$TASK_ROOT/venv/bin/python" --no-deps --no-build-isolation -e "$TASK_ROOT/dependencies/agentodyssey"
uv pip install --python "$TASK_ROOT/venv/bin/python" --no-deps --no-build-isolation -e "$TASK_ROOT/project"
uv pip freeze --python "$TASK_ROOT/venv/bin/python" > "$TASK_ROOT/project/results/environment-lock.txt"
