"""Revalidate the frozen data without rebuilding or changing the test selection."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import multiprocessing as mp
from pathlib import Path

from scar.io import atomic_json, digest
from scar_v3.freeze_data import validate


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cases", required=True)
    p.add_argument("--manifest", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--workers", type=int, default=8)
    args = p.parse_args()
    cases = json.loads(Path(args.cases).read_text())
    manifest = json.loads(Path(args.manifest).read_text())
    assert digest(cases) == manifest["sha256"]
    with ProcessPoolExecutor(max_workers=args.workers, mp_context=mp.get_context("spawn")) as pool:
        rows = list(pool.map(validate, cases))
    failures = [r for r in rows if not all(r[k] for k in ["exact_twice", "initial_goal_false", "initial_target_rejected", "state_hash_matches", "history_matches_initial_observation"])]
    atomic_json(args.output, {"dataset_sha256": digest(cases), "checks": rows, "failed": failures})
    if failures:
        raise SystemExit("Frozen replay validation failed")
    print(json.dumps({"validated": len(rows), "failed": 0}))


if __name__ == "__main__":
    main()
