"""Report specification diagnostics separately from full 300-step evaluation."""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from scar.environment import restore, state_digest, AGENT_ID
from scar_public.provider import usage_summary
from scar_public.summarize import summarize


def read_run(run, expected_actions):
    run = Path(run)
    manifest = json.loads((run / "manifest.json").read_text())
    state = json.loads((run / "current.json").read_text())
    rows = [json.loads(p.read_text()) for p in sorted((run / "trace").glob("*.json"))]
    assert state["complete"] and len(rows) == expected_actions
    fork = manifest.get("diagnostic_fork")
    source = Path(fork["path"]) / "environment.pkl" if fork else run.parents[2] / "initial" / manifest["game"] / "initial.pkl"
    initial = restore(source, run / "validation_start")
    final = restore(run / "checkpoints" / state["checkpoint"] / "environment.pkl", run / "validation_final")
    assert state_digest(initial) == rows[0]["before_digest"]
    assert state_digest(final) == rows[-1]["after_digest"]
    assert final.scores[AGENT_ID] == state["scores"] == rows[-1]["scores"]
    assert manifest["enable_obs_valid_actions"] is False
    memory = json.loads((run / "checkpoints" / state["checkpoint"] / "agent.json").read_text())
    parsed = [json.loads(row["response"]) for row in rows]
    first_step = rows[0]["step"]
    spec_records = [r for r in memory.get("spec_records", []) if r["step"] >= first_step - 1]
    cycle_steps = sum(i >= 2 and rows[i]["action"].startswith("enter ") and
                      rows[i]["action"] == rows[i-2]["action"] and
                      rows[i-1]["action"].startswith("enter ") and
                      rows[i]["scores"]["quest"] == rows[i-2]["scores"]["quest"]
                      for i in range(len(rows)))
    # Mechanistic examples selected after observing this development run, not a
    # representative sample or an estimate of causal prevalence.
    example_steps = {"mark":[138],"metropolis":[134],"remnant":[106]}.get(manifest["game"], [])
    examples = [{"step":r["step"],"observation":r["observation"],"action":r["action"],
                 "response":p,"next_observation":r["next_observation"],"scores":r["scores"]}
                for r,p in zip(rows,parsed) if r["step"] in example_steps] if not fork else []
    initial_main = initial.scores.get(AGENT_ID, {}).get("quest", 0)
    return {"manifest":manifest, "new_actions":len(rows), "main_before":initial_main,
            "main_after":final.scores[AGENT_ID]["quest"],
            "main_delta":final.scores[AGENT_ID]["quest"]-initial_main,
            "numeric_decisions":sum(p.get("decision_source")=="local_arrangement_search" for p in parsed),
            "specification_requests":len(spec_records), "specifications":spec_records,
            "semantic_experiments":memory.get("experiments", []),
            "posthoc_examples":examples,"stagnant_two_move_cycle_steps":cycle_steps,
            "condition_values":dict(collections.Counter(str(c["value"]) for p in parsed for c in p.get("condition_values", []))),
            "top_actions":collections.Counter(row["action"] for row in rows).most_common(10),
            "action_trace":[{"step":row["step"],"action":row["action"],"main":row["scores"]["quest"],
                             "source":p.get("decision_source","llm")} for row,p in zip(rows,parsed)],
            "usage":usage_summary(run/"api")}


def analyze(root):
    root = Path(root)
    diagnostics = []
    for prefix in ("specdiag_cp", "specdiag_b_cp"):
        for checkpoint in (62,178,206):
            record = read_run(root / (prefix+str(checkpoint)) / "spec_v5/metropolis", 30)
            control = root / (f"diagnostic_cp{checkpoint}/viability_v3/metropolis" if checkpoint != 206 else
                              "round2/evidence_v2/metropolis")
            control_rows = [json.loads((control/"trace"/f"{i:04d}.json").read_text())
                            for i in range(checkpoint+1,checkpoint+31)]
            first = json.loads((root / (prefix+str(checkpoint)) / "spec_v5/metropolis/trace" / f"{checkpoint+1:04d}.json").read_text())
            assert first["before_digest"] == control_rows[0]["before_digest"]
            record["frozen_control"] = {"path":str(control), "main_after":control_rows[-1]["scores"]["quest"],
                "main_delta":control_rows[-1]["scores"]["quest"]-record["main_before"],
                "note":"Reused continuation; equal environment budget, not equal inference budget or a fresh replicate."}
            diagnostics.append(record)
    full = {game:read_run(root/"round6/spec_v5"/game,300) for game in ("remnant","mark","metropolis")}
    all_full = summarize(root)
    # The legacy summarizer retains the first stage label when the same method is
    # rerun. Select this evaluation explicitly, including its usage, not round5.
    v5_group = all_full["groups"]["spec_v5"]
    assert all(g["manifest"]["stage"] == "round6" for g in v5_group["games"].values())
    v5_group["stage"] = "round6"
    v5_group["usage"] = usage_summary(root/"round6/spec_v5")
    command = [sys.executable, str(root.parent/"source/AgentOdyssey/challenge_eval.py"), "--json"]
    for game in full:
        command += ["--"+game, str(root/"round6/spec_v5"/game)]
    official = json.loads(subprocess.check_output(command))
    assert official["aggregate"]["main_quest_mean"] == all_full["groups"]["spec_v5"]["main_mean"]
    frozen = json.loads((root/"frozen-baselines.json").read_text())
    for name, files in frozen.items():
        for filename, sha in files.items():
            assert hashlib.sha256((root/"round1"/name/filename).read_bytes()).hexdigest() == sha
    interrupted = []
    for run in sorted((root/"round5/spec_v5").iterdir()):
        state = json.loads((run/"current.json").read_text())
        stop = json.loads((run/"manual_stop.json").read_text())
        interrupted.append({"game":run.name,"state":state,"manual_stop":stop,"usage":usage_summary(run/"api")})
    finished_usage = [r["usage"] for r in diagnostics]+[r["usage"] for r in full.values()]
    assert all(r["unknown_charge_attempts"] == 0 for r in finished_usage)
    usage = finished_usage + [r["usage"] for r in interrupted]
    current_usage = {key:sum(r[key] for r in usage) for key in ("requests","successful_responses","peak_usd_estimate",
        "unknown_charge_attempts","prompt_tokens","completion_tokens","cache_hit_tokens")}
    return {"diagnostics":diagnostics,"full_runs":full,"official_v5":official,
            "interrupted_runs":interrupted,
            "all_full_groups":all_full["groups"],"new_phase_usage":current_usage,
            "all_phases_usage":usage_summary(root),"frozen_baselines_verified":len(frozen),
            "limits":"Development single runs, selected failure states, extra inference, and coupled changes; no significance or novelty claim."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    result = analyze(args.root)
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps({"official":result["official_v5"]["aggregate"],"new_usage":result["new_phase_usage"],
                      "total_usage":result["all_phases_usage"]}, indent=2))
