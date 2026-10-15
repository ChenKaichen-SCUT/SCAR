import json
import tempfile
from pathlib import Path

from scar_public.agent import Notebook
from scar_public.provider import peak_cost, Provider, usage_summary


def test_public_evidence_and_method_replacement():
    book = Notebook()
    text = "The workshop requires two metal plates. Your metal plates were consumed."
    book.prompt(text)
    response = {"reasoning": "Try another route", "action": "wait",
                "frame": {"goal": "obtain device", "method": "purchase", "missing": "seller", "expected": "seller located"},
                "upsert": [{"key": "workshop", "kind": "rule", "claim": "Crafting here costs plates",
                            "quote": "The workshop requires two metal plates."},
                           {"key": "imaginary", "kind": "rule", "claim": "Cannot buy device",
                            "quote": "There are no other methods available."}]}
    book.update(response, text, 0)
    assert list(book.facts) == ["workshop"]
    assert book.frame["method"] == "purchase"
    assert "consumed" not in str(book.facts)
    # Literal evidence checking is provenance only; semantic entailment is not claimed.
    book.prompt("The workshop rule has changed.")
    response.update(upsert=[], forget=["workshop"])
    book.update(response, "The workshop rule has changed.", 1)
    assert not book.facts


def test_cache_is_step_specific_and_accounting(tmp_path):
    class Response:
        status_code = 200
        def json(self):
            return {"model": "mock", "choices": [{"message": {"content": '{"reasoning":"ok","action":"wait"}'},
                "finish_reason": "stop"}], "usage": {"prompt_tokens": 100, "prompt_cache_hit_tokens": 40,
                "completion_tokens": 10}}
    class Session:
        calls = 0
        def post(self, *args, **kwargs):
            self.calls += 1
            return Response()
    key = tmp_path / "test.key"
    key.write_text("sk-TESTONLY")
    provider = Provider(tmp_path / "api", key)
    provider.session = Session()
    a = provider.generate("test", "test")
    b = provider.generate("test", "test")
    assert a == b and provider.session.calls == 1
    provider.step = 1
    provider.generate("test", "test")
    assert provider.session.calls == 2
    summary = usage_summary(tmp_path / "api")
    assert summary["requests"] == 2 and summary["unknown_charge_attempts"] == 0
    assert abs(summary["peak_usd_estimate"] - 2 * (40*.006+60*.30+10*1.20)/1e6) < 1e-12


def test_evidence_has_no_promoted_inference_and_delta_is_reversible():
    import difflib
    from scar_public.evidence import EvidenceMemory, observation_delta
    old = "Goal: deliver the package.\nHolding package.\nAn archivist knows the pattern is wrong."
    new = "Goal: deliver the package.\nHolding nothing.\nThe package was delivered."
    delta = observation_delta(old, new)
    assert "".join(difflib.restore(delta, 1)) == old
    assert "".join(difflib.restore(delta, 2)) == new
    memory = EvidenceMemory()
    memory.prompt(old)
    memory.update({"reasoning": "Imagined requirement: rewrite the package", "action": "drop package",
        "frame": {"goal_quote": "Goal: deliver the package.", "method": "deliver", "assessment": "untested",
                  "expected": "delivery confirmed"}}, old, 0)
    prompt = memory.prompt(new)
    assert "Imagined requirement" not in prompt
    assert "- Holding package." in prompt and "+ Holding nothing." in prompt
    assert memory.frame["goal_quote"] in old
    memory.update({"action": "wait", "frame": {"goal_quote": "You must rewrite the package.",
        "method": "reassess", "assessment": "unknown", "expected": "new feedback"}}, new, 1)
    assert memory.frame["goal_quote"] == "Goal: deliver the package."


def test_real_environments_and_baselines(tmp_path):
    from scar.environment import create_environment, snapshot, restore, state_digest, AGENT_ID
    from scar_public.run import build_agent, agent_state, load_agent_state, GAMES, METHODS
    class Fake:
        model = "mock"
        step = 0
        def generate(self, user_prompt, system_prompt):
            assert "Action space:" in system_prompt and "My Current Observation:" in user_prompt
            self.prompt = user_prompt
            return {"num_input_tokens": 0, "num_output_tokens": 0,
                    "response": json.dumps({"reasoning": "smoke", "action": "wait", "upsert": [], "forget": [],
                        "frame": {"goal": "unknown", "method": "observe", "missing": "evidence", "expected": "time passes"}})}
    for game in GAMES:
        env, obs = create_environment(game, None, tmp_path / game)
        snap = snapshot(env)
        for method in METHODS:
            clone = restore(snap, tmp_path / (game + method))
            assert state_digest(clone) == state_digest(env)
            fake = Fake()
            agent = build_agent(method, clone, fake)
            before = state_digest(clone)
            action = agent.act(obs[AGENT_ID])[0]
            assert action == "wait" and state_digest(clone) == before
            saved = json.loads(json.dumps(agent_state(agent, method)))
            another = build_agent(method, clone, fake)
            load_agent_state(another, method, saved)
            assert agent_state(another, method) == agent_state(agent, method)
        one = restore(snap, tmp_path / (game + "one"))
        next1, reward1, done1, info1 = one.step({AGENT_ID: "wait"})
        one.update_scores(reward1)
        two = restore(snap, tmp_path / (game + "two"))
        next2, reward2, done2, info2 = two.step({AGENT_ID: "wait"})
        two.update_scores(reward2)
        assert next1 == next2 and info1 == info2 and done1 == done2
        assert state_digest(one) == state_digest(two)
