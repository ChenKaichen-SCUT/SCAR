#!/usr/bin/env bash
# One background job, no model-driven monitoring loop. Remote batch waits for
# its own workers, then exports; local reconstruction and publication follow.
set -euo pipefail
cd /mnt/Space0/AINative/scar_agentodyssey
export PYTHONHASHSEED=0 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONPATH=.
export AGENTODYSSEY_ROOT=/mnt/Space0/scar_dependencies/agentodyssey
ssh -S /tmp/scar-ssh-%C -o ServerAliveInterval=30 -o ServerAliveCountMax=20 root@124.71.11.165 'cd /root/scar_workspace/project && AGENTODYSSEY_ROOT=/root/scar_workspace/dependencies/agentodyssey PYTHONHASHSEED=0 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONPATH=. /root/scar_workspace/venv/bin/python -m scar_stage17.batch --runtime /root/scar_workspace/stage17_runtime --workers 10 > /root/scar_workspace/stage17_batch.log 2>&1 && tar -czf /root/scar_workspace/stage17_completed.tgz results/stage17 reports/stage17'
scp -o ControlPath=/tmp/scar-ssh-%C root@124.71.11.165:/root/scar_workspace/stage17_completed.tgz /mnt/Space0/scar_dependencies/stage17_completed.tgz
tar -xzf /mnt/Space0/scar_dependencies/stage17_completed.tgz
/mnt/Space0/scar_dependencies/venv/bin/python -m scar_stage17.replay --site local --runtime /mnt/Space0/scar_dependencies/stage17_local_replay > /mnt/Space0/scar_dependencies/stage17_local_replay.log 2>&1
/mnt/Space0/scar_dependencies/venv/bin/python -m scar_stage17.publish
