import json

from scar_public.public_model import PublicModel, state_from_text
from scar_public.specification import SpecificationMemory


def public_observation(holding="2 plank", extra=""):
    return ("Current Location: Workshop, forge\nI am holding " + holding + ".\nI have equipped no objects.\n"
            "I see 1 pack_0, 1 wire, 1 bench near me.\nNeighboring areas: yard.\n" + extra)


def test_unknown_is_not_empty_or_a_capacity_limit():
    model = PublicModel()
    model.observe(public_observation())
    assert model.hand_capacity is None
    assert model.check_action("pick up wire")["status"] == "unknown"
    model.observe(public_observation(extra="Cannot pick up wire, not enough space in hand."))
    assert model.hand_capacity == 2
    assert model.check_action("pick up wire")["status"] == "contradicted"
    model.observe("Current Location: Workshop, forge\nIt is too dark to see anything here.")
    assert model.current["holding"] is None and model.current["ground"] is None
    assert model.check_action("pick up wire")["status"] == "unknown"


def test_joint_resource_search_requires_capacity_escape():
    model = PublicModel()
    model.observe(public_observation(extra="Cannot pick up wire, not enough space in hand.\n"
        "It can be used to craft: hammer (2 plank, 1 wire)"))
    conflict = model.arrange("hammer")
    assert conflict["status"] == "unknown" and conflict["hand_only_conflict"]
    model.observe(public_observation(extra="I inspected pack_0: a container.\nIt contains: nothing (capacity: 0/6)."))
    result = model.arrange("hammer")
    assert result["plan"][-1] == "craft 1 hammer"
    assert any(action.startswith("store ") for action in result["plan"])
    assert result["container"] == "pack_0"
    # Check the proposed trace against a separate minimal inventory interpreter.
    hands, ground, bag, worn = ["plank", "plank"], ["pack_0", "wire"], [], False
    for action in result["plan"][:-1]:
        if action.startswith("drop "):
            item = action[5:]; hands.remove(item); ground.append(item)
        elif action.startswith("pick up "):
            item = action[8:]; ground.remove(item); hands.append(item)
        elif action.startswith("equip "):
            hands.remove("pack_0"); worn = True
        elif action.startswith("store "):
            item = action.split()[2]; hands.remove(item); bag.append(item)
        assert len(hands) <= 2
        assert sorted(hands + ground + bag + (["pack_0"] if worn else [])) == ["pack_0", "plank", "plank", "wire"]
    carried = hands + (bag if worn or "pack_0" in hands else [])
    assert carried.count("plank") >= 2 and carried.count("wire") >= 1


def test_proposed_terminal_condition_cannot_confirm_wrong_goal():
    memory = SpecificationMemory()
    observation = "Task: preserve the requested phrase.\nI inspected sheet_0: paper.\nIt writes: a different phrase"
    memory.ingest(observation)
    memory.set_specification({"specification": {"goal_quote": "Task: preserve the requested phrase.",
        "conditions": [{"kind":"text_contains", "item":"sheet_0", "value":"different phrase"}],
        "focus":{"kind":"write","target":"sheet_0"},"hypotheses":[]}}, 0)
    assert memory.model.predicate(memory.specification["conditions"][0]) is True
    assert memory.specification["goal_quote"] not in memory.model.completed
    memory.ingest("I wrote on sheet_0: additional content")
    assert memory.model.predicate(memory.specification["conditions"][0]) is None


def test_experiment_requires_disagreement_and_observed_preconditions():
    memory = SpecificationMemory()
    memory.ingest(public_observation())
    memory.specification = {"hypotheses":[{"id":"H1"},{"id":"H2"}]}
    trial = {"action":"inspect plank", "experiment":{"hypotheses":["H1","H2"],
        "predictions":[True, True], "observe":{"kind":"reported","value":"Unreported goal"},
        "preconditions":[{"kind":"held","item":"plank","count":2}]}}
    memory.register_experiment(trial,0)
    assert memory.pending_experiment is None
    trial["experiment"]["predictions"] = [True,False]
    memory.register_experiment(trial,0)
    assert memory.pending_experiment
    memory.ingest("Nothing relevant is observed.")
    assert memory.experiments[-1]["outcome"] == "unobserved"
    assert not memory.experiments[-1]["inconsistent_under_assumed_preconditions"]


def test_public_memory_migration_and_resume_preserve_evidence_only():
    memory = SpecificationMemory()
    memory.ingest(public_observation(extra="Task: construct the requested device."))
    memory.last_action = "pick up wire"
    memory.ingest(public_observation(extra="Cannot pick up wire, not enough space in hand."))
    saved = json.loads(json.dumps(memory.state()))
    saved["frame"] = {"method":"invented old actor assertion"}
    restored = SpecificationMemory()
    restored.load(saved)
    assert restored.model.view() == memory.model.view()
    assert "invented old actor assertion" not in restored.specification_context("current public text")
    assert restored.model.hand_capacity == 2


def test_navigation_checks_current_location_and_observed_edges():
    model = PublicModel()
    model.observe("Current Location: Home, hall\nNeighboring areas: yard.")
    model.observe("Current Location: Garden, yard\nI entered yard.\nNeighboring areas: hall, gate.", "enter yard")
    model.observe("Current Location: Garden, gate\nI entered gate.\nNeighboring areas: yard.", "enter gate")
    assert model.check_action("enter hall")["status"] == "contradicted"
    # A past forward edge does not establish the reverse edge.
    assert model.route("hall") is None
