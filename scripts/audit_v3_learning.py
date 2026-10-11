"""Offline component audit. Engine truth never enters the policy/learner interface.

Development demonstrations train a separate audit model, never the formal online
agents. Test prefixes are a witness-conditioned diagnostic distribution, not new
independent cases or an estimate of agent recovery performance.
"""
import argparse
from collections import Counter
import copy
import json
from pathlib import Path
import shlex

from scar.environment import restore, isolated_copy, AGENT_ID
from scar.diagnostics.scoring import score_candidate
from scar.io import atomic_json, digest
from scar_v3.learning import PreconditionLearner
from scar_v3.state import PublicState


def metrics(rows):
    known = [r for r in rows if r["prediction"]["status"] != "UNKNOWN"]
    tp = sum(r["truth"] and r["prediction"]["status"] == "REJECT" for r in rows)
    fp = sum(not r["truth"] and r["prediction"]["status"] == "REJECT" for r in rows)
    negatives = sum(r["truth"] for r in rows)
    div = lambda a, b: a/b if b else None
    ece = 0
    bins = []
    for i in range(10):
        selected = [r for r in rows if min(9, int(10*r["prediction"]["failure_probability"])) == i]
        if selected:
            risk = sum(r["prediction"]["failure_probability"] for r in selected)/len(selected)
            actual = sum(r["truth"] for r in selected)/len(selected)
            ece += len(selected)/len(rows)*abs(risk-actual)
            bins.append({"bin": i, "n": len(selected), "risk": risk, "observed_rejection": actual})
    return {"n": len(rows), "covered": len(known), "coverage": div(len(known), len(rows)),
            "reject_precision": div(tp, tp+fp), "reject_recall_all_rejections": div(tp, negatives),
            "false_block_rate_among_reject_predictions": div(fp, tp+fp),
            "false_positive_rate_among_legal": div(fp, len(rows)-negatives),
            "true_positive": tp, "false_positive": fp, "actual_rejections": negatives,
            "unknown": len(rows)-len(known),
            "brier_all_predictions": div(sum((r["prediction"]["failure_probability"]-int(r["truth"]))**2 for r in rows), len(rows)),
            "ece_10_equal_width_bins": ece if rows else None, "calibration_bins": bins}


def prefixes(case):
    env = restore(case["initial_snapshot"])
    state = None
    for transition in case["history"]:
        before = PublicState.observe(transition["before"], state)
        state = PublicState.observe(transition["after"], before, transition["action"])
    for index in range(len(case["witness"])+1):
        yield env, state, index
        if index < len(case["witness"]):
            action = case["witness"][index]
            observation, reward, _, _ = env.step({AGENT_ID: action})
            env.update_scores(reward)
            state = PublicState.observe(observation[AGENT_ID], state, action)


def branch(env, state, action):
    with isolated_copy(env) as clone:
        after, _, _, _ = clone.step({AGENT_ID: action})
        return PublicState.observe(after[AGENT_ID], state, action)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cases", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--include-test", action="store_true")
    args = p.parse_args()
    cases = json.loads(Path(args.cases).read_text())
    output = Path(args.output); output.mkdir(parents=True, exist_ok=True)
    learner = PreconditionLearner()
    updates, samples = [], []
    for case in sorted((r for r in cases if r["split"] == "dev"), key=lambda r: r["id"]):
        for env, state, index in prefixes(case):
            actions = [case["target_action"]]
            if index < len(case["witness"]):
                actions.append(case["witness"][index])
            # Publicly named object only; these are real executed branch probes,
            # not labels reverse-engineered from the test set or artificial feedback.
            if case["goal"]["kind"] == "possess":
                actions.append("pick up " + shlex.quote(case["goal"]["name"]))
            for action in dict.fromkeys(actions):
                after = branch(env, state, action)
                observed = learner.observe(action, state, after)
                if observed:
                    samples.append({"family": case["family"], "prefix": index, "action": action,
                                    "before": state.to_dict(), "after_feedback": after.feedback, **observed})
                updates += [{"family": case["family"], "prefix": index, **e} for e in learner.events]
                learner.events.clear()
    frozen = digest(learner.to_dict())
    contrastive = PreconditionLearner.from_dict(copy.deepcopy(learner.to_dict()))
    contrastive.feedback_rules = {}
    direct_feedback = PreconditionLearner.from_dict(copy.deepcopy(learner.to_dict()))
    direct_feedback.models = {}
    rows = []
    splits = ["dev", "test"] if args.include_test else ["dev"]
    for case in sorted((r for r in cases if r["split"] in splits), key=lambda r: r["id"]):
        for env, state, index in prefixes(case):
            prediction = learner.predict(case["target_action"], state).to_dict()
            truth = score_candidate(env, case["target_action"])
            rows.append({"family": case["family"], "source_cluster": case["source_cluster"],
                         "mechanism_cluster": case["mechanism_cluster"], "split": case["split"],
                         "prefix": index, "action": case["target_action"], "prediction": prediction,
                         "contrastive_prediction": contrastive.predict(case["target_action"], state).to_dict(),
                         "feedback_prediction": direct_feedback.predict(case["target_action"], state).to_dict(),
                         "truth": truth["semantic_rejection"], "action_rule_feedback": truth["feedback"]})
    assert digest(learner.to_dict()) == frozen
    summary = {"dataset_sha256": digest(cases), "train_split": "dev", "train_families": 31,
               "train_public_samples": len(samples), "learner_sha256": frozen, "test_updates": 0,
               "contrastive_updates": sum(e["event"] == "contrastive_rule_update" for e in updates),
               "multi_condition_update_count": sum(any(len(h)>1 for h in e.get("hypotheses", [])) for e in updates),
               "metrics": {s: metrics([r for r in rows if r["split"] == s]) for s in splits},
               "module_predictions": {view: {s: metrics([dict(r, prediction=r[view]) for r in rows if r["split"] == s]) for s in splits}
                                      for view in ["contrastive_prediction", "feedback_prediction"]},
               "initial_state_metrics": {s: metrics([r for r in rows if r["split"] == s and r["prefix"] == 0]) for s in splits},
               "scope": "Separate dev-demonstration-trained component, not loaded into online agents. Correlated witness-prefix states; dev is resubstitution, test is held-out. Module views disable either prediction route after identical training; they are not task-level causal ablations. No claim of task recovery or independent causal contribution."}
    atomic_json(output/"summary.json", summary)
    atomic_json(output/"predictions.json", rows)
    atomic_json(output/"public_training_samples.json", samples)
    atomic_json(output/"rule_updates.json", updates)
    atomic_json(output/"audit_model.json", learner.to_dict())
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
