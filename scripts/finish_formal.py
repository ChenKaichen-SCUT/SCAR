"""Run remaining authorized stages sequentially without an interactive monitor."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from scar.io import atomic_json, digest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--key-file", required=True)
    args = parser.parse_args()
    runtime = Path(args.runtime).resolve()
    project = Path(__file__).resolve().parents[1]
    runtime.mkdir(parents=True, exist_ok=True)
    lock = (runtime / "formal_followup.lock").open("a")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit("A follow-up batch is already running")
    state_path = runtime / "formal_followup_status.json"
    env = dict(os.environ, PYTHONHASHSEED="0", OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1",
               MKL_NUM_THREADS="1", HF_HUB_OFFLINE="1",
               AGENTODYSSEY_ROOT=str(project.parent / "dependencies" / "agentodyssey"))
    freeze = json.loads((project / "results/formal_freeze.json").read_text())
    implementation = digest({str(p.relative_to(project / "scar")): p.read_text()
                             for p in sorted((project / "scar").rglob("*.py"))})
    if implementation != freeze["implementation_sha256"]:
        raise SystemExit("Frozen implementation mismatch; refusing to mix versions")
    config = json.loads((project / "configs/protocol.json").read_text())
    if config != freeze["config"]:
        raise SystemExit("Frozen configuration mismatch")
    py = sys.executable
    cases = str(runtime / "ao_fr_frozen/cases.json")
    commands = []
    for stage in ["long", "cost"]:
        commands.append((stage, [py, "-m", "scar.experiments.run", "--stage", stage, "--workers", "16",
                                "--runtime", str(runtime), "--key-file", args.key_file]))
    commands.extend([
        ("analysis", [py, "-m", "scar.experiments.analyze", "--runtime", str(runtime), "--output", "results"]),
        ("replay_audit", [py, "scripts/audit_artifacts.py", "--runtime", str(runtime), "--output", "results"]),
        ("recovery_costs", [py, "scripts/recovery_costs.py", "--runtime", str(runtime), "--output", "results"]),
        ("cluster_sensitivity", [py, "scripts/diagnostic_uncertainty.py", "--runtime", str(runtime), "--output", "results"]),
        ("frozen_cra", [py, "-m", "scar.diagnostics.rule_accuracy", "--runtime", str(runtime), "--cases", cases,
                         "--output", "results/rule_accuracy_frozen.json"]),
        ("supplementary", [py, "scripts/report_details.py", "--runtime", str(runtime), "--output", "results"]),
        ("initial_goal_audit", [py, "scripts/audit_initial_goals.py", "--cases", cases,
                               "--output", "results/initial_goal_audit.json"]),
    ])
    completed = []
    for stage, command in commands:
        atomic_json(state_path, {"state": "running", "stage": stage, "completed": completed,
                                 "pid": os.getpid(), "updated": time.time()})
        with (runtime / (stage + ".log")).open("a") as log:
            result = subprocess.run(command, cwd=project, env=env, stdout=log, stderr=subprocess.STDOUT)
        if result.returncode:
            atomic_json(state_path, {"state": "failed", "stage": stage, "completed": completed,
                                     "returncode": result.returncode, "updated": time.time()})
            raise SystemExit(result.returncode)
        completed.append(stage)
    atomic_json(state_path, {"state": "finished", "completed": completed, "updated": time.time(),
                             "note": "Inspect run statuses and audits before drawing conclusions; report/upload remain pending."})


if __name__ == "__main__":
    main()
