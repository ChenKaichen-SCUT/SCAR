import pytest

from scar_v3.state import Truth, Evidence, PublicState, match_conditions


def observation(step=0, hands="no objects", ground="1 key", npcs="no one", extra="", location="Hall"):
    return {"step": step, "text": f"Current Location: {location}\n{extra}\nI am holding {hands}.\nI have equipped no objects.\nI see {ground} near me.\nI see {npcs} nearby.\nNeighboring areas: Gate.\n"}


def test_missing_is_unknown_not_equal_or_false():
    assert match_conditions({"hands.space": None}, {}) == Truth.UNKNOWN
    assert match_conditions({"hands.space": Truth.FALSE}, {}) == Truth.UNKNOWN
    assert match_conditions({"hands.space": Truth.FALSE}, {"hands.space": Evidence(Truth.FALSE)}) == Truth.TRUE
    assert match_conditions({"hands.space": Truth.FALSE}, {"hands.space": Evidence(Truth.TRUE)}) == Truth.FALSE


def test_darkness_drops_obsolete_hand_observation():
    visible = PublicState.observe(observation(hands="1 bag, 1 key"))
    dark = PublicState.observe({"step": 1, "text": "Current Location: Hall\nIt is too dark to see anything here.\nNeighboring areas: Gate."}, visible)
    assert visible.features("pick up torch")["hands.space"].truth == Truth.FALSE
    assert dark.features("pick up torch")["hands.space"].truth == Truth.UNKNOWN
    assert match_conditions({"hands.space": Truth.FALSE}, dark.features("pick up torch")) == Truth.UNKNOWN


def test_irrelevant_objects_and_npcs_do_not_release_hand_rule():
    states = [PublicState.observe(observation(hands="1 bag, 1 key", ground=g, npcs=n))
              for g, n in [("1 torch", "bob"), ("1 torch, 2 coin", "alice")]]
    assert all(match_conditions({"hands.space": Truth.FALSE}, s.features("pick up torch")) == Truth.TRUE for s in states)


def test_relevant_change_releases_and_clock_does_not():
    a = PublicState.observe(observation(hands="1 bag, 1 key"))
    later = PublicState.observe(observation(100, hands="1 bag, 1 key"), a)
    released = PublicState.observe(observation(101, hands="1 bag"), later)
    assert later.features("pick up key")["hands.space"].truth == Truth.FALSE
    assert released.features("pick up key")["hands.space"].truth == Truth.TRUE


def test_missing_resources_never_become_known_absent():
    s = PublicState.observe({"step": 0, "text": "Current Location: Hall\nDarkness."})
    assert s.features("craft 1 key", ["resource:iron>=1"])["resource:iron>=1"].truth == Truth.UNKNOWN
    s = PublicState.observe(observation(hands="1 small_bag_0"))
    assert s.features("craft 1 key", ["resource:iron>=1"])["resource:iron>=1"].truth == Truth.UNKNOWN


def test_container_inspection_then_mutation_invalidates_counts():
    s = PublicState.observe(observation(hands="1 small_bag_0", extra="I inspected small_bag_0.\nIt contains: 2 iron (capacity: 2/10)."), action="inspect small_bag_0")
    assert s.features("craft 1 key", ["resource:iron>=2"])["resource:iron>=2"].truth == Truth.TRUE
    changed = PublicState.observe(observation(1, hands="1 small_bag_0"), s, "take out iron small_bag_0")
    assert changed.features("craft 1 key", ["resource:iron>=2"])["resource:iron>=2"].truth == Truth.UNKNOWN


def test_combat_requires_evidence_not_timeout_or_one_dead_enemy():
    s = PublicState.observe(observation(npcs="goblin, orc", extra="Cannot enter Gate. goblin has blocked the way out."))
    later = PublicState.observe(observation(100, npcs="goblin, orc"), s)
    assert later.features("enter Gate")["combat.clear"].truth == Truth.FALSE
    unclear = PublicState.observe(observation(101, npcs="orc", extra="I defeated goblin."), later)
    assert unclear.features("enter Gate")["combat.clear"].truth == Truth.UNKNOWN
    clear = PublicState.observe(observation(102), unclear)
    assert clear.features("enter Gate")["combat.clear"].truth == Truth.TRUE


def test_recipe_knowledge_comes_only_from_public_inspection():
    s = PublicState.observe(observation(extra="It can be used to craft: key (made of iron, wood), torch (made of wood, coal)."), action="inspect wood")
    assert s.recipes == {"key": ["iron", "wood"], "torch": ["wood", "coal"]}
    facts = s.features("craft 1 key")
    assert "resource:iron>=1" in facts and "resource:coal>=1" not in facts
    assert PublicState.from_dict(s.to_dict()) == s
