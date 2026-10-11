"""Background revision batch; never schedules an archived baseline."""
import argparse
import fcntl
import os
from pathlib import Path
import subprocess
import sys
import time

from scar.io import atomic_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--historical-runtime", required=True)
    parser.add_argument("--key-file", required=True)
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[1]
    runtime = Path(args.runtime).resolve()
    runtime.mkdir(parents=True, exist_ok=True)
    lock = (runtime / "followup.lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    env = dict(os.environ, PYTHONHASHSEED="0", OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1",
               HF_HUB_OFFLINE="1", AGENTODYSSEY_ROOT=str(project.parent / "dependencies/agentodyssey"))
    common = ["--runtime", str(runtime), "--historical-runtime", args.historical_runtime]
    py, output = sys.executable, "results/v2"
    commands = [(stage, [py, "-m", "scar_v2.run", "--stage", stage, "--workers", "16", *common, "--key-file", args.key_file])
                for stage in ["smoke", "diagnostic", "long", "cost"]]
    commands += [
        ("replay_audit", [py, "scripts/audit_artifacts.py", "--runtime", str(runtime), "--output", output]),
        ("recovery_costs", [py, "scripts/recovery_costs.py", "--runtime", str(runtime), "--output", output]),
        ("posthoc_checks", [py, "scripts/posthoc_checks.py", "--runtime", str(runtime), "--output", output]),
        ("analysis", [py, "-m", "scar_v2.analyze", *common, "--output", output]),
    ]
    completed = []
    for stage, command in commands:
        atomic_json(runtime / "followup_status.json", dict(state="running", stage=stage, completed=completed, pid=os.getpid(), updated=time.time()))
        with (runtime / (stage + ".log")).open("a") as log:
            result = subprocess.run(command, cwd=project, env=env, stdout=log, stderr=subprocess.STDOUT)
        if result.returncode:
            atomic_json(runtime / "followup_status.json", dict(state="failed", stage=stage, completed=completed, returncode=result.returncode, updated=time.time()))
            raise SystemExit(result.returncode)
        completed.append(stage)
    atomic_json(runtime / "followup_status.json", dict(state="finished", completed=completed, updated=time.time(),
                note="Results and report draft generated. Scientific review and GitHub results publication remain pending."))


if __name__ == "__main__":
    main()
