import os
from pathlib import Path

import pytest

from scar.environment import AGENT_ID, create_environment, snapshot, restore, state_digest, isolated_copy


@pytest.mark.parametrize("game", ["remnant", "mark", "metropolis"])
def test_real_environment_snapshot_exact_replay(game, tmp_path):
    env, obs = create_environment(game, 7, tmp_path / "original")
    data = snapshot(env)
    assert b"DEEPSEEK_API_KEY" not in data
    left = restore(data, tmp_path / "left")
    right = restore(data, tmp_path / "right")
    for action in ["wait", "look around", "wait", 'enter "nonexistent"']:
        a = left.step({AGENT_ID: action})
        b = right.step({AGENT_ID: action})
        assert a[0] == b[0]
        assert a[2:] == b[2:]
        assert a[1][AGENT_ID].__dict__ == b[1][AGENT_ID].__dict__
        assert state_digest(left) == state_digest(right)
    assert state_digest(env) != state_digest(left)
    assert env.steps == 0


@pytest.mark.parametrize("game", ["remnant", "mark", "metropolis"])
def test_offline_scoring_does_not_mutate_environment(game, tmp_path):
    from scar.diagnostics.scoring import score_candidate
    env, obs = create_environment(game, 7, tmp_path / game)
    before = state_digest(env)
    result = score_candidate(env, 'enter "nonexistent"')
    assert result["semantic_rejection"]
    assert state_digest(env) == before


def test_official_registration_and_agent_memory_roundtrip(tmp_path):
    from scar.integration import make_agent, register_with_eval
    import json
    settings = json.loads((Path(__file__).parents[1] / "configs/protocol.json").read_text())
    provider = object()
    agent = make_agent("SCARAgent", "remnant", provider, settings, tmp_path)
    agent.memorize("A real previously observed failure")
    agent.save_memory(tmp_path / "memory")
    clone = make_agent("SCARAgent", "remnant", provider, settings, tmp_path)
    clone.load_memory(tmp_path / "memory")
    assert clone.short_term_memory == agent.short_term_memory
    clone.short_term_memory.append("private")
    assert clone.short_term_memory != agent.short_term_memory
    import eval as official
    original = register_with_eval(provider, settings)
    try:
        from utils import dynamic_load_game_class
        cfg = official.build_agent_config("SCARAgent", {"llm_name": "deepseek-flash", "llm_provider": "deepseek"})
        obj = official.instantiate_agent("SCARAgent", {"id": "a", "name": "A", "cfg": cfg}, dynamic_load_game_class("mark", "agent", "Agent"))
        assert obj.failure_memory is not None
    finally:
        official.instantiate_agent, official.build_agent_config = original


@pytest.mark.parametrize("algorithm", ["ShortTermMemoryAgent", "LongContextAgent", "SCARAgent", "SimpleFailureRecovery"])
def test_actual_agent_act_and_checkpoint(algorithm, tmp_path):
    from scar.integration import make_agent
    import json
    class TestProvider:
        tokens_in = tokens_out = 0
        def generate(self, user_prompt, system_prompt=None):
            self.tokens_in += 10
            self.tokens_out += 5
            return {"response": '{"reasoning":"test","action":"wait"}', "num_input_tokens": 10,
                    "num_output_tokens": 5, "parsed": {"reasoning": "test", "action": "wait"}}
    settings = json.loads((Path(__file__).parents[1] / "configs/protocol.json").read_text())
    agent = make_agent(algorithm, "remnant", TestProvider(), settings, tmp_path)
    env, observations = create_environment("remnant", 7, tmp_path / "env", agent)
    for _ in range(2):
        action, *_ = agent.act(observations[AGENT_ID])
        assert action == "wait"
        following, *_ = env.step({AGENT_ID: action})
        if hasattr(agent, "observe_transition"):
            agent.observe_transition(observations[AGENT_ID], action, following[AGENT_ID])
        observations = following
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    agent.save_memory(memory_dir)
    agent.load_memory(memory_dir)


def test_scar_four_modules_execute_together(tmp_path):
    import json
    from scar.integration import make_agent
    from test_core import obs
    class PlannedProvider:
        tokens_in = tokens_out = 0
        answers = [
            {"action": 'enter "Gate"', "reasoning": "attempt"},
            {"action": 'enter "Gate"', "reasoning": "candidate"},
            {"action": 'pick up "key"', "reasoning": "recover", "plan": ['pick up "key"']},
            {"action": "wait", "reasoning": "base candidate"},
        ]
        def generate(self, user_prompt, system_prompt=None):
            self.tokens_in += 10
            self.tokens_out += 5
            value = self.answers.pop(0)
            return {"response": json.dumps(value), "parsed": value,
                    "num_input_tokens": 10, "num_output_tokens": 5}
    config = json.loads((Path(__file__).parents[1] / "configs/protocol.json").read_text())
    agent = make_agent("SCARAgent", "remnant", PlannedProvider(), config, tmp_path)
    first = obs(0)
    action, *_ = agent.act(first)
    failed = obs(1, feedback="Cannot enter Gate, the door is locked.")
    agent.observe_transition(first, action, failed)
    repaired, *_ = agent.act(failed)
    assert repaired == 'pick up "key"'
    released = obs(2, hands="key", feedback="I picked up key.")
    agent.observe_transition(failed, repaired, released)
    retry, *_ = agent.act(released)
    assert retry == 'enter "Gate"'
    succeeded = obs(3, location="Gate", hands="key", feedback="I entered Gate.")
    agent.observe_transition(released, retry, succeeded)
    types = {e["event"] for e in agent.events}
    assert {"failure_learned", "memory_hit", "plan_repair", "safe_retry_success"} <= types
    assert agent.plan.status == "complete"
