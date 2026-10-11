import json
from pathlib import Path

from scar_v3.learning import PreconditionLearner
from scar_v3.state import PublicState, Truth
from scar_v3.agent import make_agent
from test_v3_state import observation
from test_v2 import Provider


def learn_two_conditions():
    learner = PreconditionLearner()
    experiences = [
        ("no objects", "1 stone", "I picked up stone."),
        ("1 key, 1 pen", "1 stone", "Cannot pick up stone, not enough space in hand."),
        ("no objects", "no objects", "Cannot pick up stone, not found in current area."),
    ]
    for step, (hands, ground, feedback) in enumerate(experiences):
        before = PublicState.observe(observation(step, hands=hands, ground=ground))
        after = PublicState.observe(observation(step+1, hands=hands, ground=ground, extra=feedback), before)
        learner.observe("pick up stone", before, after)
    return learner


def test_online_contrasts_learn_two_necessary_conditions():
    learner = learn_two_conditions()
    generic = learner.models["verb:pick up"]
    assert generic["hypotheses"] == [{"hands.space": Truth.TRUE, "target.ground": Truth.TRUE}]
    assert generic["version"] > 0
    assert any(e["event"] == "contrastive_rule_update" for e in learner.events)
    assert all(s["source"] == "public_transition" for s in generic["samples"])


def test_role_schema_transfers_to_an_unseen_object():
    learner = learn_two_conditions()
    missing = PublicState.observe(observation(9, ground="1 stone"))
    assert learner.predict("pick up key", missing).status == "REJECT"
    present = PublicState.observe(observation(9, ground="1 key"))
    assert learner.predict("pick up key", present).status == "SUPPORTED"


def test_unknown_never_satisfies_an_old_failure_condition():
    learner = learn_two_conditions()
    dark = PublicState.observe({"step": 100, "text": "Current Location: Hall\nIt is too dark to see anything here."})
    prediction = learner.predict("pick up stone", dark)
    assert prediction.status == "UNKNOWN" and "hands.space" in prediction.unknown
    assert prediction.permission == "attempt_permitted"


def test_positive_counterexample_revises_old_rule_and_version_space():
    learner = learn_two_conditions()
    before = PublicState.observe(observation(10, hands="1 key, 1 pen", ground="1 stone"))
    # Contradiction test deliberately supplies a counterexample; it is a unit test,
    # never included as a fabricated game result in the research data.
    after = PublicState.observe(observation(11, extra="I picked up stone."), before)
    learner.observe("pick up stone", before, after)
    assert any(r["status"] == "contradicted" for r in learner.feedback_rules.values())
    assert all("hands.space" not in h for h in learner.models["verb:pick up"]["hypotheses"])


def test_roundtrip_preserves_learned_predictions():
    learner = learn_two_conditions()
    clone = PreconditionLearner.from_dict(json.loads(json.dumps(learner.to_dict())))
    s = PublicState.observe(observation(5, ground="no objects"))
    assert learner.predict("pick up stone", s).to_dict() == clone.predict("pick up stone", s).to_dict()


def test_satisfied_necessary_conditions_retain_unexplained_failure_risk():
    learner = learn_two_conditions()
    before = PublicState.observe(observation(10, ground="1 stone"))
    after = PublicState.observe(observation(11, extra="Cannot pick up stone, another condition blocks it."), before)
    learner.observe("pick up stone", before, after)
    prediction = learner.predict("pick up stone", before)
    assert prediction.status == "SUPPORTED"
    assert prediction.failure_probability >= .5


def make(tmp_path, answers):
    config = json.loads((Path(__file__).parents[1]/"configs/protocol.json").read_text())
    return make_agent("SCARV3Agent", "remnant", Provider(answers), config, tmp_path)


def test_evidence_supports_active_recovery_without_extra_llm(tmp_path):
    agent = make(tmp_path, ["pick up stone"])
    before = observation(hands="1 key, 1 pen", ground="1 stone")
    after = observation(1, hands="1 key, 1 pen", ground="1 stone", extra="Cannot pick up stone, not enough space in hand.")
    agent.observe_transition(before, "pick up stone", after)
    action = agent.act(after)[0]
    assert action.startswith("drop ")
    assert agent.decision["reason"] == "evidence_supported_net_benefit"
    assert agent.decision["executed_value"]["value"] > agent.decision["base_value"]["value"]
    assert agent.llm.calls == 1


def test_valid_goal_candidate_not_overridden_by_old_plan(tmp_path):
    agent = make(tmp_path, ["pick up stone"])
    agent.goal_action = "pick up stone"
    agent.plan = {"actions": ["drop key"], "goal": "pick up stone", "created": 0, "location": "Hall"}
    assert agent.act(observation(hands="1 key", ground="1 stone"))[0] == "pick up stone"
    assert not agent.decision["intercepted"]


def test_old_missing_hands_error_does_not_recur(tmp_path):
    agent = make(tmp_path, ["take out torch small_bag_0"])
    dark = {"step": 10, "text": "Current Location: Hall\nIt is too dark to see anything here."}
    failed = {"step": 11, "text": "Current Location: Hall\nCannot take out torch, not enough space in hand.\nIt is too dark to see anything here."}
    agent.observe_transition(dark, "take out torch small_bag_0", failed)
    assert agent.act(failed)[0] == "take out torch small_bag_0"
    assert not agent.decision["intercepted"]


def test_explicit_goal_change_discards_obsolete_plan(tmp_path):
    agent = make(tmp_path, [])
    agent.goal_action = "pick up stone"
    agent.plan["actions"] = ["drop key"]
    old = observation(extra="Required action: `pick up stone`")
    new = observation(1, extra="I picked up stone.\nRequired action: `enter Gate`")
    agent.observe_transition(old, "pick up stone", new)
    assert agent.goal_action == "enter Gate" and not agent.plan["actions"]


def test_full_agent_checkpoint(tmp_path):
    agent = make(tmp_path, ["pick up stone"])
    agent.learner = learn_two_conditions()
    agent.act(observation(9, ground="1 stone"))
    path = tmp_path/"saved"; path.mkdir()
    agent.save_memory(path)
    clone = make(tmp_path, [])
    clone.load_memory(path)
    assert clone.learner.to_dict() == json.loads(json.dumps(agent.learner.to_dict()))
    assert clone.plan == agent.plan


def test_completed_incidental_goal_does_not_capture_future_failures(tmp_path):
    agent = make(tmp_path, [])
    agent.goal_action = "pick up stone"
    agent.observe_transition(observation(), "pick up stone", observation(1, extra="I picked up stone."))
    assert agent.goal_action == ""
    agent.observe_transition(observation(1), "enter Gate", observation(2, extra="Cannot enter Gate, door locked."))
    assert agent.goal_action == "enter Gate"


def test_diagnostic_objective_takes_priority_over_background_tutorial(tmp_path):
    agent = make(tmp_path, [])
    agent.set_recovery_objective("craft 1 stone_slab", "Obtain a stone_slab")
    agent.observe_transition(observation(extra="Required action: `wait`"), "craft 1 stone_slab",
                             observation(1, extra="I successfully crafted stone_slab.\nRequired action: `enter Gate`"))
    assert agent.goal_action == "pick up stone_slab"
