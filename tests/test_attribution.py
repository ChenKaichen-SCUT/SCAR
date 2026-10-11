"""Scientific semantics and pre-action isolation for the offline diagnostic."""
from scar_attribution.branches import multistep_choice
from scar_attribution.oracle import progress


def value(action,confidence=1,p=0):
    return dict(action=action,allowed=True,probability_of_success=1-p,evidence_confidence=confidence,extra_call_cost=0)


def test_unknown_search_is_not_a_switching_certificate():
    a={"C0_values":[value("base"),value("alternative")]}
    r=multistep_choice(a,{"base":{"distance":None},"alternative":{"distance":None}},10)
    assert r["action"]=="base"
    assert all(v["q_verified_lower_bound"]==0 for v in r["values"])


def test_value_and_knowledge_crossed_without_changing_candidates():
    a={"C0_values":[value("base",0,.5),value("repair",0,.5)],"C1_values":[value("base"),value("repair")]}
    b={"base":{"distance":None},"repair":{"distance":2}}
    assert multistep_choice(a,b,10)["action"]=="base"
    assert multistep_choice(a,b,10,True)["action"]=="repair"
    assert [v["action"] for v in multistep_choice(a,b,10)["values"]]==[v["action"] for v in multistep_choice(a,b,10,True)["values"]]


def test_horizon_counts_first_action_and_preserves_original_risk():
    a={"C0_values":[value("base"),value("repair")]}
    b={"base":{"distance":None},"repair":{"distance":6}}
    assert multistep_choice(a,b,5)["action"]=="base"
    assert multistep_choice(a,b,10)["action"]=="repair"


def test_condition_progress_does_not_confuse_loss_and_gain():
    before={"facts":{"x":{"met":False},"y":{"met":True}},"violated":["x"],"rejected":True}
    after={"facts":{"x":{"met":True},"y":{"met":False}},"violated":["y"],"rejected":True}
    r=progress(before,after)
    assert r["repaired"]==["x"] and r["regressed"]==["y"]
    assert r["net_blocker_reduction"]==0 and not r["target_released"]
