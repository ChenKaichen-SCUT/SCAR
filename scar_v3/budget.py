"""Empirical planning estimate; fixed historical prices, never an invoice."""
from pathlib import Path
import json


def estimate(root, cases=89, spent=16.025308818, cap=20):
    root = Path(root)
    historical = json.loads((root/"results/all_summaries.json").read_text())
    historical += json.loads((root/"results/v2/all_summaries.json").read_text())
    methods = ["ShortTermMemoryAgent", "SimpleFailureRecovery", "SCARAgent", "SCARV2Agent"]
    rates = {}
    for method in methods:
        rows = [r for r in historical if r["algorithm"] == method and r.get("stage") == "long"
                and r["status"] == "completed" and r.get("protocol_cohort") == "formal_hash0"]
        rates[method] = sum(r["conservative_cost_usd"] for r in rows)/sum(r["steps"] for r in rows)
    rates["SCARV3Agent"] = max(rates.values())*1.2
    by_method = {k: {"per_step_usd": rate, "hard_at_full_40_steps_usd": cases*40*rate,
                     "long_3_by_200_usd": 600*rate} for k, rate in rates.items()}
    diagnostic = sum(r["hard_at_full_40_steps_usd"] for r in by_method.values())
    long = sum(r["long_3_by_200_usd"] for r in by_method.values())
    dev = .2
    total = (diagnostic+long+dev)*1.2
    return {"spent_conservative_usd": spent, "authorized_project_cap_usd": cap,
            "remaining_authorized_usd": cap-spent, "hard_test_families": cases,
            "hard_episodes": cases*5, "hard_step_cap": 40, "long_episodes": 15, "long_step_cap": 200,
            "by_method": by_method, "diagnostic_full_length_estimate_usd": diagnostic,
            "long_estimate_usd": long, "development_allowance_usd": dev,
            "contingency_multiplier": 1.2, "incremental_planning_estimate_usd": total,
            "estimated_project_total_usd": spent+total, "authorization_shortfall_usd": max(0, total-(cap-spent)),
            "can_complete_under_current_authorization": total <= cap-spent,
            "basis": "Completed hash0 long episodes at frozen accounting prices; V3 rate uses highest prior rate times 1.2. All hard cases budgeted at full 40 steps, then 20% contingency plus development allowance. Early recovery can reduce cost. Prompt length/provider variation can increase it. Not a guaranteed upper bound or account invoice."}
