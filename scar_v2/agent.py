"""Candidate-gated repair using public observations and action signatures only.

Failure detection, conditional memory, online revision and checkpoint format are
inherited unchanged from SCAR v1. Releasing a rule permits, but never forces, a
retry. A local plan is consulted only for the currently blocked candidate.
"""
import json
from functools import lru_cache

from agents.fixed_size.short_term_memory_agent import ShortTermMemoryAgent
from scar.agents.scar.agent import SCARAgent
from scar.agents.scar.repair import valid_syntax
from scar.agents.scar.state import VisibleState, action_key
from scar.providers.deepseek import ModelResponseError


class SCARV2Agent(SCARAgent):
    def _next_repair(self, proposal, state):
        plan = self.plan
        if (plan.status != "repairing" or action_key(plan.goal_action) != action_key(proposal)
                or state.step - plan.origin_step > 20
                or state.fields.get("location", "") != plan.context_location):
            plan.pending.clear()
            return None
        while plan.pending:
            action = plan.pending.pop(0)
            if (valid_syntax(action, self.available_actions)
                    and self.failure_memory.assess(action, state)[0] != "block"):
                plan.last_action = action
                return action
        return None

    def _install_repair(self, goal, candidates, state):
        plan = self.plan
        plan.goal_action, plan.origin_step = goal, state.step
        plan.context_location = state.fields.get("location", "")
        plan.pending, plan.last_action = [], ""
        seen = set()
        for candidate in candidates:
            if not isinstance(candidate, str):
                continue
            candidate = candidate.strip()
            key = action_key(candidate)
            if (key not in seen and valid_syntax(candidate, self.available_actions)
                    and self.failure_memory.assess(candidate, state)[0] != "block"):
                plan.pending.append(candidate)
                seen.add(key)
            if len(plan.pending) >= self.max_plan_steps:
                break
        plan.status = "repairing" if plan.pending else "needs_information"

    def _act(self, obs):
        if self.pending_transition:
            self.observe_transition(*self.pending_transition, obs)
        state = VisibleState.observe(obs, self.visible_state)
        self.visible_state = state
        start_tokens = self.llm.tokens_in, self.llm.tokens_out
        # Exactly the official STM candidate prompt, shared with the first round.
        proposed, _, _, base_response = ShortTermMemoryAgent._act(self, obs)
        actual, reason, proposals = proposed, "base", [proposed]
        assessment, rule = self.failure_memory.assess(proposed, state)
        syntax_ok = valid_syntax(proposed, self.available_actions)
        if rule:
            self.events.append({"event": "memory_hit", "step": state.step,
                                "action": proposed, "rule": rule.id, "assessment": assessment})
        if assessment == "probe" and syntax_ok:
            rule.probes += 1
            self.events.append({"event": "cooldown_retry", "step": state.step, "rule": rule.id})
        trigger = "known_failure" if assessment == "block" else "syntax" if not syntax_ok else None
        if trigger:
            actual = self._next_repair(proposed, state)
            reason = "repair_step"
            if actual is None:
                evidence = [r.__dict__ for r in self.failure_memory.retrieve(proposed, state)[:3]]
                prompt = (
                    f"Current observation:\n{obs['text']}\nRecent memory:\n"
                    + "\n".join(self.short_term_memory[-5:])
                    + f"\nBlocked candidate: {proposed}\nRepair trigger: {trigger}\n"
                    + f"Conditional failure evidence: {json.dumps(evidence)}\n"
                    + f"Public action space:\n{self.cfg.action_prompt}\n"
                    "Propose a short local recovery plan to remove the blocker or advance the same goal via another route. "
                    "Use only observed entities and the public action space. An unknown prerequisite is a hypothesis. "
                    "Prefer useful information gathering when uncertain. Correct invalid action syntax if necessary. "
                    "Return JSON with reasoning, action (first step), and plan (at most 3 action strings)."
                )
                parsed = self.llm.generate(prompt, self.cfg.system_prompt)["parsed"]
                candidates = [parsed["action"]] + (parsed.get("plan", []) if isinstance(parsed.get("plan"), list) else [])
                proposals.extend(a for a in candidates if isinstance(a, str))
                self._install_repair(proposed, candidates, state)
                actual, reason = self._next_repair(proposed, state), "repair"
                if actual is None:
                    if not syntax_ok:
                        raise ModelResponseError("No syntactically valid action after bounded repair; no game action executed")
                    # Audited verification attempt, rather than an invented successful repair.
                    actual, reason = proposed, "verification_fallback"
                self.events.append({"event": "plan_repair", "step": state.step, "trigger": trigger,
                                    "plan": self.plan.to_dict(), "executed": actual, "reason": reason})
            proposals.append(actual)
        # Public-signature validation also covers queued actions and fallbacks.
        if not valid_syntax(actual, self.available_actions):
            raise ModelResponseError("Final action failed public signature validation")
        self.decision = {
            "proposed_action": proposed, "executed_action": actual, "all_proposals": proposals,
            "intercepted": action_key(actual) != action_key(proposed) or (not syntax_ok and actual != proposed), "reason": reason,
            "repair_trigger": trigger, "candidate_assessment": assessment, "candidate_syntax_valid": syntax_ok,
            "rule_predictions": [
                {"rule_id": r.id, "action": r.action, "predict_invalid":
                 self.failure_memory.assess(r.action, state)[0] == "block"}
                for r in self.failure_memory.rules if r.status != "contradicted"],
        }
        if self.decision["intercepted"]:
            self.events.append({"event": "action_intercepted", "step": state.step,
                                "proposed": proposed, "executed": actual})
        self.short_term_memory[-1] = f"{obs['text']}\nProposed: {proposed}\nExecuted action: {actual}"
        self.pending_transition = obs, actual
        return actual, self.llm.tokens_in - start_tokens[0], self.llm.tokens_out - start_tokens[1], base_response


@lru_cache(maxsize=None)
def create_scar_v2_agent(Agent):
    return type(f"SCARV2Agent__{Agent.__module__}.{Agent.__name__}", (SCARV2Agent, Agent), {"__module__": Agent.__module__})


def make_agent(algorithm, game, provider, settings, memory_dir):
    if algorithm != "SCARV2Agent":
        raise ValueError("This regression runner accepts only SCARV2Agent; reuse archived baselines")
    from scar.integration import DeepSeekMemoryConfig
    from utils import dynamic_load_game_class
    cfg = DeepSeekMemoryConfig(
        llm_name=settings["model"], llm_provider="deepseek", embed_name=settings["embedding_model"],
        max_new_tokens=settings["max_tokens"], temperature=settings["temperature"],
        short_term_memory_size=5, torch_seed=settings.get("seed", 42), full_mem_path=str(memory_dir))
    cfg.scar_provider, cfg.scar_settings = provider, settings["scar"]
    return create_scar_v2_agent(dynamic_load_game_class(game, "agent", "Agent"))(
        id="agent_adam_davis", name="adam_davis", cfg=cfg)
