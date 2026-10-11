import pytest
from scar.experiments.analyze import paired_bootstrap
from scar.diagnostics.scoring import recovery_score


def test_paired_ci_preserves_direction_and_clusters():
    result = paired_bootstrap([1, 1, 3, 3], ["a", "a", "b", "b"], n=1000)
    assert result["pairs"] == 4 and result["independent_groups"] == 2
    assert result["mean_difference"] == 2
    assert result["ci95_low"] == 1 and result["ci95_high"] == 3


def test_alternative_progress_requires_ground_truth_goal():
    rows = [{"executed_action": "craft key 1", "semantic_rejection": False, "diagnostic_goal_reached": True}]
    result = recovery_score(rows, "pick up key", True)
    assert result["recovery_at_10"] and result["alternative_recovery"]
    rows[0]["diagnostic_goal_reached"] = False
    assert not recovery_score(rows, "pick up key", True)["recovery_at_20"]
