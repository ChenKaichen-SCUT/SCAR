"""Exercise all five policy factories and checkpoint runner with NO API provider."""
import argparse
import json
from pathlib import Path

from scar.io import atomic_json, digest
from scar_v3.run import episode, make_tasks


class ScriptedProvider:
    """Test-only deterministic provider; makes no network requests."""
    def __init__(self, config, audit_path, ledger_path, key_path, workers):
        self.action = config["scripted_action"]
        self.tokens_in = self.tokens_out = self.calls = 0

    def generate(self, user_prompt, system_prompt=None):
        self.calls += 1
        self.tokens_in += 10; self.tokens_out += 5
        parsed = {"action": self.action, "reasoning": "offline plumbing check", "plan": [self.action]}
        return {"response": json.dumps(parsed), "parsed": parsed, "num_input_tokens": 10, "num_output_tokens": 5}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cases", required=True)
    p.add_argument("--runtime", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    config = json.loads(Path("configs/protocol_v3.json").read_text())
    cases = json.loads(Path(args.cases).read_text())
    selected = [next(c for c in cases if c["split"] == "dev" and c["game"] == game) for game in config["games"]]
    results = []
    for case in selected:
        for algorithm in config["algorithms"]:
            row = {k: case[k] for k in ["id", "family", "game", "seed", "initial_snapshot", "history", "target_action", "public_goal", "goal", "state_hash", "recoverable"]}
            row.update(task_id=f"offline-{case['id']}-{algorithm}", diagnostic=True, max_steps=2, algorithm=algorithm)
            cfg = dict(config, scripted_action=case["witness"][0])
            result = episode(row, cfg, args.runtime, None, 1, provider_factory=ScriptedProvider)
            assert result["status"] == "completed", (algorithm, result["error"])
            assert result["api_calls"] == 0 and result["cost_usd"] == 0
            rerun = episode(row, cfg, args.runtime, None, 1, provider_factory=ScriptedProvider)
            assert digest(result) == digest(rerun), "Completed episode must be idempotent"
            results.append({k: result[k] for k in ["game", "algorithm", "status", "steps", "api_calls", "cost_usd"]})
    assert len(make_tasks(config, args.runtime, cases, "hard")) == 445
    assert len(make_tasks(config, args.runtime, cases, "long")) == 15
    assert len(make_tasks(config, args.runtime, cases, "dev")) == 3
    atomic_json(args.output, {"scope": "Real engine and all five policy factories, scripted provider only; no model-performance claims", "runs": results,
                              "completed": len(results), "idempotent_resume": True, "api_calls": 0, "api_cost_usd": 0})
    print(json.dumps({"completed": len(results), "api_calls": 0}), flush=True)


if __name__ == "__main__":
    main()
