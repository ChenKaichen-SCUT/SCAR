"""Run the authorized fixed cohort once, then analyze/audit without extra API work."""
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
    p = argparse.ArgumentParser()
    p.add_argument("--runtime", required=True)
    p.add_argument("--cumulative-ledger", required=True)
    p.add_argument("--cases", required=True)
    p.add_argument("--key-file", required=True)
    p.add_argument("--workers", type=int, default=16)
    args = p.parse_args()
    project = Path(__file__).resolve().parents[1]
    runtime = Path(args.runtime).resolve(); runtime.mkdir(parents=True, exist_ok=True)
    lock = (runtime/"pipeline.lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    env = dict(os.environ, PYTHONHASHSEED="0", OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1", HF_HUB_OFFLINE="1",
               AGENTODYSSEY_ROOT=str(project.parent/"dependencies/agentodyssey"))
    paths = [project/"configs/protocol_v3.json"] + [p for directory in ["scar", "scar_v2", "scar_v3"] for p in sorted((project/directory).rglob("*.py"))]
    fingerprint = lambda: digest({str(p.relative_to(project)):p.read_text() for p in paths})
    frozen = fingerprint()
    marker = runtime/"execution_freeze.json"
    if marker.exists():
        if json.loads(marker.read_text())["sha256"] != frozen:
            raise SystemExit("Execution cohort changed since launch; refuse mixed-version resume")
    else:
        atomic_json(marker,{"sha256":frozen,"created":time.time(),"scope":"Required V3 cohort; no optional RAG, extra seeds or 500-step runs"})
    common = ["--runtime",str(runtime),"--cumulative-ledger",args.cumulative_ledger,"--cases",args.cases,"--key-file",args.key_file,"--workers",str(args.workers),"--execute"]
    commands = [(s,[sys.executable,"-m","scar_v3.run","--stage",s,*common]) for s in ["dev","hard","long"]]
    output = "results/v3/formal"
    commands += [("analysis",[sys.executable,"-m","scar_v3.analyze","--runtime",str(runtime),"--cases",args.cases,"--output",output]),
                 ("replay_audit",[sys.executable,"-m","scripts.audit_v3_formal","--runtime",str(runtime),"--output",output])]
    completed = []
    for stage, command in commands:
        if fingerprint() != frozen:
            raise SystemExit("Frozen execution files changed while cohort running")
        atomic_json(runtime/"pipeline_status.json",{"state":"running","stage":stage,"completed":completed,"pid":os.getpid(),"updated":time.time()})
        with (runtime/f"{stage}.log").open("a") as log:
            result = subprocess.run(command,cwd=project,env=env,stdout=log,stderr=subprocess.STDOUT)
        if result.returncode:
            atomic_json(runtime/"pipeline_status.json",{"state":"failed","stage":stage,"completed":completed,"returncode":result.returncode,"updated":time.time()})
            raise SystemExit(result.returncode)
        completed.append(stage)
    atomic_json(runtime/"pipeline_status.json",{"state":"experiments_and_audits_finished","completed":completed,"updated":time.time(),
                "next":"Review paired results, write final scientific report and publish actual experiment outputs to GitHub."})


if __name__ == "__main__":
    main()
