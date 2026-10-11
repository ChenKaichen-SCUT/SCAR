"""Recompute final reporting tables from exported trajectories, without API calls."""
import argparse
from collections import Counter, defaultdict
import csv
import gzip
import json
from pathlib import Path
import statistics

from scar.io import atomic_json, digest
from scripts.audit_v3_learning import metrics
from scripts.v3_outcomes import FORMAT_FAILURES


def csv_write(path, rows):
    keys = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys, lineterminator="\n")
        w.writeheader(); w.writerows(rows)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--results", default="results/v3/formal")
    args = p.parse_args()
    root = Path(args.results)
    result = json.loads((root/"formal_status.json").read_text())
    summaries = json.loads((root/"all_summaries.json").read_text())
    audit = json.loads((root/"replay_audit.json").read_text())
    account = json.loads((root/"request_accounting.json").read_text())
    assert len(summaries) == 463
    assert result["hard_evaluated"] == 445 and result["long_evaluated"] == 15
    assert result["hard_method_terminations"] == 2 and result["long_method_terminations"] == 1
    assert audit["failures"] == 0 and audit["exact"] == audit["checked"] == 1388
    assert len(audit["initial_checks"]) == 463 and all(x["matches_frozen_source"] for x in audit["initial_checks"])
    formal_pairs = [x for x in audit["pair_checks"] if x["stage"] in {"hard","long"}]
    assert len(formal_pairs) == 92 and all(x["algorithms"] == 5 and x["equal_initial_states"] for x in formal_pairs)
    for s in summaries:
        if s["status"] != "completed":
            assert s["status"] == "failed" and s["error"] in FORMAT_FAILURES
    assert abs(sum(s["conservative_cost_usd"] for s in summaries)-account["conservative_cost_usd"]) < 1e-9
    by_id = {s["task_id"]:s for s in summaries}
    stages, events, predictions = defaultdict(Counter), defaultdict(Counter), defaultdict(list)
    traces, examples = Counter(), defaultdict(list)
    for path in sorted(root.glob("trajectories_*.jsonl.gz")):
        with gzip.open(path,"rt",encoding="utf-8") as f:
            for line in f:
                entry = json.loads(line); task, row = entry["task"], entry["transition"]
                traces[task["task_id"]] += 1
                stage, method = task["stage"], task["algorithm"]
                group = stages[(stage,method)]
                group["steps"] += 1
                group["semantic_rejections"] += row["semantic_rejection"]
                for e in row.get("events",[]):
                    events[(stage,method)][e["event"]] += 1
                    if e["event"] == "contrastive_rule_update" and any(len(h)>1 for h in e.get("hypotheses",[])):
                        group["multi_condition_rule_updates"] += 1
                        if len(examples["multi_condition_updates"]) < 8:
                            examples["multi_condition_updates"].append({"task":task,"index":row["index"],"event":e})
                for t in row.get("rule_tests",[]):
                    if "failure_probability" in t:
                        predictions[stage].append({"truth":t["semantic_rejection"],"prediction":{"status":t["prediction_status"],"failure_probability":t["failure_probability"]}})
                truth = row.get("proposed_truth")
                if truth is not None:
                    group["interceptions"] += 1
                    group["false_blocks"] += not truth["semantic_rejection"]
                    group["legal_to_rejected"] += not truth["semantic_rejection"] and row["semantic_rejection"]
                    group["rejected_to_legal"] += truth["semantic_rejection"] and not row["semantic_rejection"]
                    group["immediate_physical_goal"] += row.get("diagnostic_goal_reached",False)
                    group["immediate_target_release"] += row.get("target_condition_release",False)
                    group["immediate_quest_reward"] += row["reward"].get("quest",0)>0
                    # Efficacy for the candidate action is separated from actual
                    # additional goal/reward over the counterfactual base choice.
                    cf = row.get("proposed_effect") or {}
                    group["additional_immediate_goal_vs_base"] += row.get("diagnostic_goal_reached",False) and not cf.get("physical_goal",False)
                    group["additional_immediate_quest_vs_base"] += row["reward"].get("quest",0)>cf.get("quest_reward",0)
    assert len(traces) == 463 and all(traces[s["task_id"]] == s["steps"] for s in summaries)
    details=[]
    for (stage,method), count in sorted(stages.items()):
        values=[s for s in summaries if s["stage"]==stage and s["algorithm"]==method]
        intercept=count["interceptions"]
        row={"stage":stage,"algorithm":method,"episodes":len(values),"normal_completions":sum(s["status"]=="completed" for s in values),
             "method_terminations":sum(s["status"]!="completed" for s in values),**count,
             "semantic_failure_rate":count["semantic_rejections"]/count["steps"],
             "fbr":count["false_blocks"]/intercept if intercept else None,
             "legal_to_rejected_per_interception":count["legal_to_rejected"]/intercept if intercept else None,
             "rejected_to_legal_per_interception":count["rejected_to_legal"]/intercept if intercept else None,
             "api_calls":sum(s["api_calls"] for s in values),"input_tokens":sum(s["input_tokens"] for s in values),
             "output_tokens":sum(s["output_tokens"] for s in values),"cost_usd":sum(s["conservative_cost_usd"] for s in values),
             "decision_wall_seconds_sum":sum(s["decision_wall_seconds"] for s in values),
             "main_quest_reward_mean":statistics.mean(s["main_quest_reward"] for s in values)}
        if stage=="hard":
            recovered=[s["recovery_steps"] for s in values if s["recovery_steps"] is not None]
            row.update({f"recovery_at_{h}":sum(s[f"recovery_at_{h}"] for s in values)/len(values) for h in [10,20,40]})
            row.update(recovered=len(recovered),median_steps_among_recovered=statistics.median(recovered),
                       actual_alternative_recoveries=sum(s["alternative_recovery"] for s in values),
                       actual_alternative_recoveries_in_alt_type=sum(s["alternative_recovery"] and "alternative_path" in s["types"] for s in values),
                       release_opportunities=sum(s["release_opportunities"] for s in values),
                       successful_released_retries=sum(s["successful_released_retries"] for s in values),
                       repeated_semantic_count=sum(s["repeated_semantic_count"] for s in values))
        details.append(row)
    tables=root/"tables";tables.mkdir(exist_ok=True)
    csv_write(tables/"stage_method_metrics.csv",details)
    csv_write(tables/"diagnostic_by_type.csv",result["by_type"])
    keys=["task_id","stage","algorithm","game","seed","family","status","steps","main_quest_reward","semantic_failure_rate","interceptions","false_blocks","fbr","legal_to_rejected","rejected_to_legal","recovery_at_10","recovery_at_20","recovery_at_40","recovery_steps","api_calls","input_tokens","output_tokens","conservative_cost_usd","decision_wall_seconds","error"]
    csv_write(tables/"all_runs.csv",[{k:s.get(k) for k in keys} for s in summaries])
    atomic_json(root/"stage_method_metrics.json",details)
    atomic_json(root/"online_learning_by_stage.json",{s:metrics(rs) for s,rs in predictions.items()})
    atomic_json(root/"events_by_stage_method.json",[{"stage":s,"algorithm":a,**v} for (s,a),v in events.items()])
    atomic_json(root/"learning_examples.json",dict(examples))
    review={"judgment":"NO-GO for the current V3 overall-superiority claim; engineering mechanisms implemented but generalization/task benefit insufficient",
            "hard_families":89,"hard_evaluated":445,"long_evaluated":15,"method_terminations":3,
            "v3_recovery_40":result["hard_by_method"]["SCARV3Agent"]["recovery_at_40"],
            "stm_recovery_40":result["hard_by_method"]["ShortTermMemoryAgent"]["recovery_at_40"],
            "v3_long_mean_observed_reward":statistics.mean(s["main_quest_reward"] for s in summaries if s["stage"]=="long" and s["algorithm"]=="SCARV3Agent"),
            "cost_usd":account["conservative_cost_usd"],"project_cumulative_usd":16.025308818+account["conservative_cost_usd"],
            "replays_exact":1388,"initial_states_match":463,"fully_paired_formal_groups":92,"exported_trajectories_verified":len(traces),
            "result_digest":digest(result),"summaries_digest":digest(summaries),"audit_digest":digest(audit),
            "limitations":["One long seed per game; no population stability/significance claim.","Most hard mothers synthetic; true goal-switch cases absent.","Post-hoc method-abort classification disclosed; raw statuses/steps/costs retained, no extra attempts.","Module learning and reduced legal-to-rejected interventions do not establish an independent causal contribution.","Remnant V3 terminated at 133 steps; its observed reward is not imputed to a completed 200-step run."]}
    assert review["v3_recovery_40"] <= review["stm_recovery_40"]
    atomic_json(root/"scientific_review.json",review)
    print(json.dumps({"reviewed_trajectories":len(traces),"verified_steps":sum(traces.values()),"cost_usd":review["cost_usd"],"judgment":review["judgment"]}))


if __name__ == "__main__":
    main()
