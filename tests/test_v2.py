"""Regression checks for intervention safety and the real four-module agent."""
import json
from pathlib import Path

import pytest

from scar.agents.scar.state import VisibleState
from scar.providers.deepseek import ModelResponseError
from scar_v2.agent import make_agent
from test_core import obs


class Provider:
    def __init__(self, answers):
        self.answers = list(answers)
        self.tokens_in = self.tokens_out = self.calls = 0

    def generate(self, user_prompt, system_prompt=None):
        self.calls += 1
        self.tokens_in += 10
        self.tokens_out += 5
        value = self.answers.pop(0)
        value = {"action": value, "reasoning": "test"} if isinstance(value, str) else value
        return {"response": json.dumps(value), "parsed": value, "num_input_tokens": 10, "num_output_tokens": 5}


def agent_at_failure(tmp_path, answers):
    cfg = json.loads((Path(__file__).parents[1] / "configs/protocol.json").read_text())
    agent = make_agent("SCARV2Agent", "remnant", Provider(answers), cfg, tmp_path)
    agent.observe_transition(obs(), 'enter "Gate"', obs(1, feedback="Cannot enter Gate, the door is locked."))
    return agent


@pytest.mark.parametrize("proposal", ['pick up "key"', 'inspect "key"'])
def test_recent_failure_never_overrides_unblocked_candidate(tmp_path, proposal):
    agent = agent_at_failure(tmp_path, [proposal])
    assert agent.act(obs(1))[0] == proposal
    assert agent.llm.calls == 1 and not agent.decision["intercepted"]


@pytest.mark.parametrize("stale_goal", ['enter "Gate"', 'write invalid extra unquoted arguments'])
def test_released_or_invalid_old_goal_never_forces_retry(tmp_path, stale_goal):
    agent = agent_at_failure(tmp_path, ['inspect "key"'])
    agent.plan.install(stale_goal, ['pick up "key"'], agent.visible_state, agent.failure_memory)
    assert agent.act(obs(2, hands="key"))[0] == 'inspect "key"'
    assert agent.llm.calls == 1


def test_blocked_candidate_uses_validated_queue_and_checkpoint(tmp_path):
    agent = agent_at_failure(tmp_path, ['enter "Gate"', {
        "action": 'inspect "key"', "reasoning": "recover", "plan": ['pick up "key"']}, 'enter "Gate"'])
    assert agent.act(obs(1))[0] == 'inspect "key"'
    agent.observe_transition(obs(1), 'inspect "key"', obs(2, feedback="A small key."))
    path = tmp_path / "memory"
    path.mkdir()
    agent.save_memory(path)
    clone = agent_at_failure(tmp_path, ['enter "Gate"'])
    clone.load_memory(path)
    assert agent.act(obs(2))[0] == clone.act(obs(2))[0] == 'pick up "key"'
    assert agent.llm.calls == 3 and clone.llm.calls == 1
    assert clone.decision["reason"] == "repair_step"


def test_bad_queued_actions_cannot_execute(tmp_path):
    agent = agent_at_failure(tmp_path, ['enter "Gate"', 'inspect "key"'])
    agent.plan.install('enter "Gate"', ['write bad'], agent.visible_state, agent.failure_memory)
    assert agent.act(obs(1))[0] == 'inspect "key"'
    assert agent.llm.calls == 2


def test_four_modules_and_voluntary_retry(tmp_path):
    agent = agent_at_failure(tmp_path, ['enter "Gate"', 'pick up "key"', 'enter "Gate"'])
    assert agent.act(obs(1))[0] == 'pick up "key"'
    released = obs(2, hands="key", feedback="I picked up key.")
    agent.observe_transition(obs(1), 'pick up "key"', released)
    assert agent.act(released)[0] == 'enter "Gate"'
    agent.observe_transition(released, 'enter "Gate"', obs(3, hands="key", location="Gate", feedback="I entered Gate."))
    assert {"failure_learned", "memory_hit", "plan_repair", "safe_retry_success"} <= {e["event"] for e in agent.events}
    assert agent.plan.status == "complete" and agent.llm.calls == 3


def test_cooldown_probe_is_not_blocked(tmp_path):
    agent = agent_at_failure(tmp_path, ['enter "Gate"'])
    assert agent.act(obs(9))[0] == 'enter "Gate"'
    assert agent.decision["candidate_assessment"] == "probe"
    assert agent.llm.calls == 1


def test_invalid_base_action_gets_one_format_repair(tmp_path):
    agent = agent_at_failure(tmp_path, ['write invalid', 'inspect "key"'])
    assert agent.act(obs(1))[0] == 'inspect "key"'
    assert agent.decision["repair_trigger"] == "syntax"


def test_quoting_correction_is_counted_as_interception(tmp_path):
    agent = agent_at_failure(tmp_path, ['write hello world paper', 'write "hello world" paper'])
    assert agent.act(obs(1))[0] == 'write "hello world" paper'
    assert agent.decision["intercepted"]


def test_format_failure_does_not_become_wait(tmp_path):
    agent = agent_at_failure(tmp_path, ['write invalid', 'write still invalid extra'])
    with pytest.raises(ModelResponseError, match="bounded repair"):
        agent.act(obs(1))
    assert agent.llm.calls == 2


def test_bounded_verification_fallback_is_explicit(tmp_path):
    agent = agent_at_failure(tmp_path, ['enter "Gate"', 'enter "Gate"'])
    assert agent.act(obs(1))[0] == 'enter "Gate"'
    assert agent.decision["reason"] == "verification_fallback"


def test_runner_rejects_baseline_rerun(tmp_path):
    with pytest.raises(ValueError, match="only SCARV2Agent"):
        make_agent("ShortTermMemoryAgent", "mark", None, {}, tmp_path)
