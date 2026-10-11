"""One minimal real request; the response contains no game-performance evidence."""
import argparse
import json
from pathlib import Path

from scar.providers.deepseek import DeepSeekProvider
from scar.io import atomic_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--key-file", required=True)
    parser.add_argument("--runtime", required=True)
    args = parser.parse_args()
    config = json.loads(Path("configs/protocol.json").read_text())
    config.update(max_tokens=32, total_budget_usd=3)
    root = Path(args.runtime)
    provider = DeepSeekProvider(config, root / "api_probe.jsonl", root / "budget.sqlite", args.key_file)
    response = provider.generate('Return JSON: {"action":"wait","reasoning":"connectivity test"}', "Return JSON only.")
    summary = {"parsed": response["parsed"], "usage": response["usage"], "model": response["raw"]["model"],
               "thinking": "disabled", **provider.totals()}
    atomic_json("results/api_probe.json", summary)
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
