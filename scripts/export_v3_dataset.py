"""Export our generated records and initial edits, excluding engine/model files."""
import argparse
import json
from pathlib import Path

from scar.io import atomic_json, digest


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cases", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    cases = json.loads(Path(args.cases).read_text())
    output = Path(args.output); output.mkdir(parents=True, exist_ok=True)
    edits = {}
    for case in cases:
        initial = Path(case["initial_snapshot"])
        if case["source"].startswith("synthetic"):
            edits[case["id"]] = json.loads((initial.parent/"initialization.json").read_text())
    atomic_json(output/"cases.json", cases)
    atomic_json(output/"synthetic_initial_edits.json", edits)
    atomic_json(output/"export_manifest.json", {"canonical_cases_sha256": digest(cases), "cases": len(cases),
                "synthetic_edit_records": len(edits), "snapshots_included": False,
                "scope": "Our generated cases, public execution histories, witnesses, counterfactual records and initial edits. No downloaded engine/world/model files, pickle snapshots or request credentials."})
    print(json.dumps({"cases": len(cases), "edits": len(edits)}))


if __name__ == "__main__":
    main()
