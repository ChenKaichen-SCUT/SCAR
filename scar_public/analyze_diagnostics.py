"""Validate the bounded continuation study; never merge it into full-run means."""
import argparse
import collections
import hashlib
import json
from pathlib import Path

from scar.environment import AGENT_ID, restore, state_digest
from scar_public.provider import usage_summary


def analyze(root):
    root = Path(root)
    cases = []
    for current in sorted(root.glob("diagnostic_cp*/*/*/current.json")):
        run = current.parent
        state = json.loads(current.read_text())
        manifest = json.loads((run / "manifest.json").read_text())
        fork = manifest["diagnostic_fork"]
        cp = Path(fork["path"])
        rows = [json.loads(p.read_text()) for p in sorted((run / "trace").glob("*.json"))]
        start = restore(cp / "environment.pkl", run / "validation_start")
        final = restore(run / "checkpoints" / state["checkpoint"] / "environment.pkl", run / "validation_final")
        assert state["complete"] and len(rows) == 30
        assert rows[0]["step"] == fork["start_step"] + 1
        assert rows[0]["before_digest"] == state_digest(start)
        assert rows[-1]["after_digest"] == state_digest(final)
        assert final.scores[AGENT_ID] == state["scores"] == rows[-1]["scores"]
        assert hashlib.sha256((cp / "environment.pkl").read_bytes()).hexdigest() == fork["environment_sha256"]
        assert hashlib.sha256((cp / "agent.json").read_bytes()).hexdigest() == fork["agent_sha256"]
        before = start.scores[AGENT_ID]["quest"]
        after = state["scores"]["quest"]
        memory = json.loads((run / "checkpoints" / state["checkpoint"] / "agent.json").read_text())
        cases.append({"method": manifest["method"], "source_checkpoint": fork["start_step"],
                      "new_actions": len(rows), "main_before": before, "main_after": after,
                      "main_delta": after - before, "manifest": manifest,
                      "source_digest": rows[0]["before_digest"], "usage": usage_summary(run / "api"),
                      "top_actions": collections.Counter(r["action"] for r in rows).most_common(8),
                      "action_trace": [{"step": r["step"], "action": r["action"],
                                        "main": r["scores"]["quest"]} for r in rows],
                      "final_frame": memory.get("frame"),
                      "new_frame_audit": memory.get("audit", [])[-30:]})
    assert len(cases) == 4
    for checkpoint in (62, 178):
        pair = [c for c in cases if c["source_checkpoint"] == checkpoint]
        assert len(pair) == 2 and pair[0]["source_digest"] == pair[1]["source_digest"]
    frozen = json.loads((root / "frozen-baselines.json").read_text())
    for relative, files in frozen.items():
        for filename, sha in files.items():
            assert hashlib.sha256((root / "round1" / relative / filename).read_bytes()).hexdigest() == sha
    usage = [c["usage"] for c in cases]
    total = {k: sum(u[k] for u in usage) for k in ("requests", "successful_responses", "peak_usd_estimate",
             "unknown_charge_attempts", "prompt_tokens", "completion_tokens", "cache_hit_tokens")}
    assert total["unknown_charge_attempts"] == 0
    return {"cases": cases, "diagnostic_usage": total, "all_usage_including_previous_phase": usage_summary(root),
            "frozen_baselines_verified": len(frozen), "full_v4_runs_launched": False,
            "conclusion": "Neither candidate continuation repaired the intended bottleneck; do not promote v4.",
            "limitation": "One stochastic continuation per method/checkpoint; local negative result, not proof of universal failure."}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--root", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    result = analyze(args.root)
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k != "cases"}, indent=2))
