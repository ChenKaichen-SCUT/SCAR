"""Offline scoring. None of these functions are available to the decision policy."""
import re

from scar.environment import AGENT_ID, isolated_copy
from scar.agents.scar.state import action_key, feedback_text


# Separate from the agent detector; applied to actual rule responses on engine copies.
REJECTION = re.compile(
    r"\b(?:cannot|can't|could not|invalid action|failed to parse|not enough|not found|"
    r"do not have|don't have|does not exist|no inventory found|not holding|"
    r"needs to be equipped|nothing happens|unable to|invalid amount)\b", re.I)


def outcome(observation, info):
    engine_invalid = bool(info.get("step_invalid_action", {}).get(AGENT_ID, False))
    feedback = feedback_text(observation[AGENT_ID]["text"])
    semantic_rejection = engine_invalid or bool(REJECTION.search(feedback))
    return {"engine_invalid": engine_invalid, "semantic_rejection": semantic_rejection,
            "feedback": feedback}


def score_candidate(env, action):
    with isolated_copy(env) as clone:
        obs, reward, done, info = clone.step({AGENT_ID: action})
        result = outcome(obs, info)
        result["quest_reward"] = reward[AGENT_ID].__dict__.get("quest", 0)
        return result


def aggregate_trajectory(rows):
    count = len(rows)
    if not count:
        return {"steps": 0, "iar": None, "semantic_failure_rate": None, "riar": None,
                "semantic_riar": None, "fbr": None, "cra": None, "main_quest_reward": 0,
                "completion": False}
    seen_engine, seen_semantic = set(), set()
    repeated_engine = repeated_semantic = 0
    for row in rows:
        # Pre-action, observation-derived equivalence; excludes irrelevant clock changes.
        key = (action_key(row["executed_action"]), row["visible_state_hash"])
        if row["engine_invalid"]:
            repeated_engine += key in seen_engine
            seen_engine.add(key)
        if row["semantic_rejection"]:
            repeated_semantic += key in seen_semantic
            seen_semantic.add(key)
    intercepted = [r for r in rows if r["intercepted"]]
    labelled = [r for r in intercepted if r.get("proposed_truth") is not None]
    false_blocks = sum(not r["proposed_truth"]["semantic_rejection"] for r in labelled)
    rule_tests = [t for r in rows for t in r.get("rule_tests", [])]
    return {"steps": count, "iar": sum(r["engine_invalid"] for r in rows) / count,
            "semantic_failure_rate": sum(r["semantic_rejection"] for r in rows) / count,
            "riar": repeated_engine / count, "semantic_riar": repeated_semantic / count,
            "repeated_invalid_count": repeated_engine, "repeated_semantic_count": repeated_semantic,
            "interceptions": len(intercepted), "false_blocks": false_blocks,
            "fbr": false_blocks / len(labelled) if labelled else None,
            "cra": sum(t["predict_invalid"] == t["semantic_rejection"] for t in rule_tests) / len(rule_tests) if rule_tests else None,
            "cra_n": len(rule_tests), "cra_scope": "online held-out copies; not an independent frozen state set",
            "main_quest_reward": sum(r["reward"].get("quest", 0) for r in rows),
            "completion": any(r["done"] for r in rows),
            "steps_to_first_milestone": next((i + 1 for i, r in enumerate(rows) if r["reward"].get("quest", 0) > 0), None)}


def recovery_score(rows, target_action, recoverable):
    if not recoverable:
        return {"eligible": False, "recovery_at_10": None, "recovery_at_20": None, "recovery_steps": None}
    step = next((i + 1 for i, r in enumerate(rows)
                 if action_key(r["executed_action"]) == action_key(target_action)
                 and not r["semantic_rejection"]), None)
    return {"eligible": True, "recovery_at_10": step is not None and step <= 10,
            "recovery_at_20": step is not None and step <= 20, "recovery_steps": step}
