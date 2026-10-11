import json
import multiprocessing as mp
from pathlib import Path
from types import SimpleNamespace

import pytest

from scar.agents.scar.state import VisibleState, action_key
from scar.agents.scar.detection import diagnose
from scar.agents.scar.memory import FailureMemory
from scar.agents.scar.repair import RepairPlan
from scar.diagnostics.scoring import aggregate_trajectory, recovery_score
from scar.providers.deepseek import BudgetLedger, BudgetExceeded, estimate_cost, read_key


def obs(step=0, hands="nothing", feedback="", location="Hall", objects="key", npcs="nobody"):
    return {"step": step, "text": f"\nCurrent Time: 2026-01-01 10:{step:02}:00\nCurrent Location: {location}\n\n{feedback}\nI am holding {hands}.\nI have equipped nothing.\nI see {objects} near me.\nI see {npcs} nearby.\nMy level is 1.\nNeighboring areas: Gate.\n"}


def learn_failure(feedback="Cannot enter Gate, the door is locked."):
    before = VisibleState.observe(obs())
    after = VisibleState.observe(obs(1, feedback=feedback), before)
    event = diagnose('enter "Gate"', before, after)
    memory = FailureMemory()
    memory.learn(event)
    return memory, before, after, event


def test_failure_links_previous_action():
    memory, before, after, event = learn_failure()
    assert event.action == 'enter "Gate"'
    assert event.step == 0 and event.location == "Hall"
    assert event.before == before.fields
    assert "locked" in event.feedback


def test_same_condition_blocks_and_time_alone_does_not_change_state():
    memory, before, after, event = learn_failure()
    assert before.fingerprint == after.fingerprint
    assert memory.assess('enter "Gate"', after)[0] == "block"


def test_conditions_changed_and_cooldown_both_allow_retry():
    memory, before, after, event = learn_failure()
    with_key = VisibleState.observe(obs(2, hands="key"), after)
    assert memory.assess('enter "Gate"', with_key)[0] == "allow"
    later = VisibleState.observe(obs(9), after)
    assert memory.assess('enter "Gate"', later)[0] == "probe"


def test_ambiguous_failure_never_immediately_becomes_a_hard_rule():
    memory, before, after, event = learn_failure("Nothing happens.")
    assert event.cause == "unknown"
    assert memory.assess(event.action, after)[0] == "uncertain"


def test_duplicate_merge_and_bound():
    memory, before, after, event = learn_failure()
    for _ in range(20):
        memory.learn(event)
    assert len(memory.rules) == 1 and memory.rules[0].failures == 21


def test_success_contradicts_same_condition_rule():
    memory, before, after, event = learn_failure()
    succeeded = VisibleState.observe(obs(2, feedback="I entered Gate.", location="Gate"), after)
    updates = memory.revise(event.action, after, succeeded, False)
    assert updates[0]["event"] == "rule_contradicted"
    assert memory.assess(event.action, after)[0] == "allow"


def test_memory_roundtrip_and_plan_completion():
    memory, before, after, event = learn_failure()
    clone = FailureMemory.from_dict(json.loads(json.dumps(memory.to_dict())))
    assert clone.assess(event.action, after)[0] == memory.assess(event.action, after)[0]
    plan = RepairPlan()
    plan.install(event.action, ['pick up "key"'], after, memory)
    assert plan.choose("wait", after, memory)[0] == 'pick up "key"'
    changed = VisibleState.observe(obs(2, hands="key"), after)
    assert plan.choose("wait", changed, memory)[0] == event.action
    plan.observe(event.action, False, True)
    assert plan.status == "complete" and not plan.pending


def test_plan_excludes_known_failure_and_revises_after_failed_repair():
    memory, before, after, event = learn_failure()
    plan = RepairPlan()
    plan.install(event.action, [event.action, 'pick up "key"'], after, memory)
    assert plan.pending == ['pick up "key"']
    plan.choose("wait", after, memory)
    plan.observe('pick up "key"', True, False)
    assert not plan.pending and plan.status == "needs_information"


def test_hidden_fields_are_ignored():
    a = obs()
    b = dict(a, invalid_action=True, valid_actions={"cheat": ["hidden"]}, world={"secret": 1})
    assert VisibleState.observe(a) == VisibleState.observe(b)


def test_unrecoverable_not_in_denominator():
    assert recovery_score([], "enter Gate", False)["eligible"] is False
    assert recovery_score([], "enter Gate", False)["recovery_at_20"] is None
    assert recovery_score([], "enter Gate", True)["recovery_at_20"] is False


def test_scoring_uses_execution_and_truth_not_absence_of_retry():
    row = {"executed_action": "wait", "proposed_action": "enter Gate", "visible_state_hash": "s",
           "engine_invalid": False, "semantic_rejection": False, "intercepted": True,
           "proposed_truth": {"semantic_rejection": False}, "reward": {"quest": 0}, "done": False}
    summary = aggregate_trajectory([row])
    assert summary["iar"] == 0 and summary["fbr"] == 1
    assert summary["main_quest_reward"] == 0
    assert recovery_score([row], "enter Gate", True)["recovery_at_20"] is False


def _reservation_worker(path, queue):
    ledger = BudgetLedger(path, 0.10)
    try:
        import os
        ledger.reserve(str(os.getpid()), 0.06)
        queue.put(True)
    except BudgetExceeded:
        queue.put(False)


def test_multiprocess_budget_no_overspend(tmp_path):
    path = str(tmp_path / "ledger.sqlite")
    BudgetLedger(path, 0.10)
    ctx = mp.get_context("spawn")
    queue = ctx.Queue()
    children = [ctx.Process(target=_reservation_worker, args=(path, queue)) for _ in range(4)]
    for p in children:
        p.start()
    results = [queue.get(timeout=30) for _ in children]
    for p in children:
        p.join(30)
        assert p.exitcode == 0
    assert sum(results) == 1


def test_usage_and_unknown_billing(tmp_path):
    prices = {"cache_hit": 0.006, "cache_miss": 0.3, "output": 1.2}
    assert estimate_cost({"prompt_tokens": 1000, "prompt_cache_hit_tokens": 500, "completion_tokens": 100}, prices) == pytest.approx(0.000273)
    ledger = BudgetLedger(tmp_path / "budget.sqlite", 0.1)
    ledger.reserve("request", 0.06)
    assert ledger.total() == 0.06
    ledger.settle("request", 0.02, "invalid_response")
    assert ledger.total() == 0.02


def test_read_key_permissions_and_reject_format(tmp_path, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    path = tmp_path / "key"
    path.write_text("not a secret")
    with pytest.raises(ValueError):
        read_key(path)
    assert path.stat().st_mode & 0o777 == 0o600


def test_action_equivalence():
    assert action_key('enter "Gate"') == action_key("enter Gate")
