"""Immutable, resumable one-game runs with isolated evaluator state."""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from scar.io import atomic_json
from scar_public.provider import Provider, usage_summary
from scar_public.agent import PublicAgent

GAMES = ("remnant", "mark", "metropolis")
METHODS = ("stm", "longcontext", "reflact", "public_v1", "evidence_v2", "viability_v3", "contract_v4", "spec_v5", "obligation_v6", "causal_shadow_v7", "resource_competition_v8", "persistent_resource_v9", "evidence_decision_v10")
PUBLIC_METHODS = ("public_v1", "evidence_v2", "viability_v3", "contract_v4", "spec_v5", "obligation_v6", "causal_shadow_v7", "resource_competition_v8", "persistent_resource_v9", "evidence_decision_v10")
METHODS += ("evidence_repair_v11", "method_repair_v12", "intent_repair_v13")
PUBLIC_METHODS += ("evidence_repair_v11", "method_repair_v12", "intent_repair_v13")
REFLACT = "You should first reflect on the agent’s state in relation to the task goal, and then output the action for this turn."


def build_agent(method, env, provider):
    from agents.llm_agent_config import LLMAgentConfig
    from agents.fixed_size.short_term_memory_agent import create_short_term_memory_agent
    from agents.long_context_agent import create_long_context_agent

    class SharedConfig(LLMAgentConfig):
        def get_llm(self, *args, **kwargs):
            return provider

        def response_parser(self, raw):
            value = json.loads(raw)
            return {"reasoning": value["reasoning"], "action": value["action"].strip()}

        def construct_user_prompt_long_context(self, memory, observation):
            return ("My Memories: " + memory if memory else "") + f"My Current Observation: {observation}\n" + self.action_prompt

    cfg = SharedConfig(torch_seed=None, llm_name=provider.model, llm_provider="audited-deepseek",
                       max_new_tokens=1536, temperature=.7, top_p=.8, presence_penalty=0,
                       short_term_memory_size=5, enable_reflection=False, enable_summarization=False)
    if method == "reflact":
        cfg.system_prompt = cfg.system_prompt.replace("A few sentences explaining why you choose the action.",
            "Reflection on the current state in relation to the task goal.")
        cfg.action_prompt = REFLACT + " Put the reflection in reasoning. Return only JSON."
    if method in PUBLIC_METHODS:
        cfg.available_actions = env.agents[0].available_actions
        cfg.__post_init__()
        if method == "evidence_v2":
            from scar_public.evidence import EvidenceAgent
            return EvidenceAgent(provider, cfg.system_prompt)
        if method == "viability_v3":
            from scar_public.viability import ViabilityAgent
            return ViabilityAgent(provider, cfg.system_prompt)
        if method == "contract_v4":
            from scar_public.contract import ContractAgent
            return ContractAgent(provider, cfg.system_prompt)
        if method == "spec_v5":
            from scar_public.specification import SpecificationAgent
            return SpecificationAgent(provider, cfg.system_prompt)
        if method == "obligation_v6":
            from scar_public.obligation_agent import ObligationAgent
            return ObligationAgent(provider, cfg.system_prompt)
        if method == "causal_shadow_v7":
            from scar_public.causal_agent import CausalShadowAgent
            return CausalShadowAgent(provider, cfg.system_prompt)
        if method == "resource_competition_v8":
            from scar_public.resource_agent import ResourceCompetitionAgent
            return ResourceCompetitionAgent(provider, cfg.system_prompt)
        if method == "persistent_resource_v9":
            from scar_public.resource_agent import PersistentResourceAgent
            return PersistentResourceAgent(provider, cfg.system_prompt)
        if method == "evidence_decision_v10":
            from scar_public.resource_agent import EvidenceDecisionAgent
            return EvidenceDecisionAgent(provider, cfg.system_prompt)
        if method == "evidence_repair_v11":
            from scar_public.evidence_repair import EvidenceRepairAgent
            return EvidenceRepairAgent(provider, cfg.system_prompt)
        if method == "method_repair_v12":
            from scar_public.method_repair import MethodRepairAgent
            return MethodRepairAgent(provider, cfg.system_prompt)
        if method == "intent_repair_v13":
            from scar_public.intent_repair import IntentRepairAgent
            return IntentRepairAgent(provider, cfg.system_prompt)
        return PublicAgent(provider, cfg.system_prompt)
    base = type(env.agents[0])
    factory = create_short_term_memory_agent if method == "stm" else create_long_context_agent
    agent = factory(base)(env.agents[0].id, env.agents[0].name, cfg=cfg)
    assert {a.verb for a in cfg.available_actions} == {a.verb for a in env.agents[0].available_actions}
    return agent


def agent_state(agent, method):
    if method in PUBLIC_METHODS:
        return agent.notebook.state()
    if method == "stm":
        return {"history": agent.short_term_memory}
    return {"history": agent.memory.context}


def load_agent_state(agent, method, state):
    if method in PUBLIC_METHODS:
        agent.notebook.load(state)
    elif method == "stm":
        agent.short_term_memory = state["history"]
    else:
        agent.memory.context = state["history"]


def prepare(root):
    from scar.environment import create_environment, save_snapshot, state_digest
    for game in GAMES:
        directory = root / "initial" / game
        directory.mkdir(parents=True, exist_ok=True)
        if (directory / "manifest.json").exists():
            continue
        env, obs = create_environment(game, None, directory / "environment")
        sha = save_snapshot(directory / "initial.pkl", env)
        atomic_json(directory / "manifest.json", {"game": game, "drawn_seed": env.seed,
            "snapshot_sha256": sha, "initial_state_digest": state_digest(env),
            "upstream_commit": "248430692a9d4a61d38c6c03ab2126287faaf450"})
        atomic_json(directory / "public_observation.json", obs)
        print(game, "initial prepared", flush=True)


def run(args):
    from scar.environment import AGENT_ID, restore, save_snapshot, state_digest
    root = Path(args.root)
    directory = root / args.stage / args.method / args.game
    directory.mkdir(parents=True, exist_ok=True)
    # Prevent accidental duplicate paid workers on a run (Linux server).
    import fcntl
    lock = (directory / "worker.lock").open("w")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    initial = root / "initial" / args.game / "initial.pkl"
    if not initial.exists():
        raise RuntimeError("Prepare shared initial snapshots before launching any method")
    manifest = {"method": args.method, "game": args.game, "max_steps": args.steps,
        "stage": args.stage, "requested_model": args.model,
        "source_revision": args.revision, "initial_snapshot_sha256": hashlib.sha256(initial.read_bytes()).hexdigest(),
        "temperature": .7, "top_p": .8, "presence_penalty": 0, "max_tokens": 1536,
        "thinking": "disabled", "enable_obs_valid_actions": False}
    if args.method == "evidence_decision_v10":
        manifest["evidence_reuse"] = not args.disable_evidence_reuse
    elif args.disable_evidence_reuse:
        raise ValueError("Evidence-reuse ablation is supported only for evidence_decision_v10")
    if args.method in ("evidence_repair_v11", "method_repair_v12", "intent_repair_v13"):
        manifest['evidence_mode']=args.evidence_mode
        manifest['evidence_context_scope']=args.evidence_context_scope
    if args.method=='intent_repair_v13':manifest['intent_mode']=args.intent_mode
    fork = Path(args.fork_checkpoint).resolve() if args.fork_checkpoint else None
    if fork:
        source_manifest = json.loads((fork.parent.parent / "manifest.json").read_text())
        if source_manifest["game"] != args.game or not 0 < int(fork.name) < args.steps:
            raise ValueError("Fork must match the game and precede the absolute final step")
        if source_manifest["initial_snapshot_sha256"] != manifest["initial_snapshot_sha256"]:
            raise ValueError("Fork and destination must share the initial world")
        manifest["diagnostic_fork"] = {"path": str(fork), "start_step": int(fork.name),
            "environment_sha256": hashlib.sha256((fork / "environment.pkl").read_bytes()).hexdigest(),
            "agent_sha256": hashlib.sha256((fork / "agent.json").read_bytes()).hexdigest(),
            "source_method": source_manifest["method"]}
    manifest_path = directory / "manifest.json"
    if manifest_path.exists() and json.loads(manifest_path.read_text()) != manifest:
        raise RuntimeError("Run manifest differs; use a new stage instead of overwriting")
    atomic_json(manifest_path, manifest)
    if args.transport_revision:
        from scar.io import append_jsonl
        append_jsonl(directory / "transport_amendments.jsonl", {
            "time": time.time(), "agent_revision": args.revision,
            "transport_revision": args.transport_revision,
            "change": "Preserve first three requests exactly; permit three more JSON-only repairs"})
    current = directory / "current.json"
    previous = json.loads(current.read_text()) if current.exists() else None
    if previous and previous["complete"]:
        print("Already complete", directory)
        return
    if previous:
        cp = directory / "checkpoints" / previous["checkpoint"]
        env = restore(cp / "environment.pkl", directory)
        saved_agent = json.loads((cp / "agent.json").read_text())
        step = previous["steps"]
    elif fork:
        env = restore(fork / "environment.pkl", directory)
        saved_agent = json.loads((fork / "agent.json").read_text())
        step = int(fork.name)
    else:
        env = restore(initial, directory)
        saved_agent = None
        step = 0
    provider = Provider(directory / "api", args.key, model=args.model)
    # Logical agent is intentionally detached from physical evaluator state.
    agent = build_agent(args.method, env, provider)
    if args.method == "evidence_decision_v10":
        agent.resource_controller.reuse_enabled = not args.disable_evidence_reuse
    if args.method in ("evidence_repair_v11", "method_repair_v12", "intent_repair_v13"):
        agent.resource_controller.mode=args.evidence_mode
        agent.resource_controller.context_scope=args.evidence_context_scope
    if args.method=='intent_repair_v13':agent.resource_controller.intervention_mode=args.intent_mode
    if saved_agent is not None:
        load_agent_state(agent, args.method, saved_agent)
    while step < args.steps:
        provider.step = step
        observation = {"text": env.obs[AGENT_ID]["text"], "step": env.obs[AGENT_ID]["step"]}
        with contextlib.redirect_stdout(sys.stderr):
            action, _, _, response = agent.act(observation)
        before = state_digest(env)
        obs, reward, done, info = env.step({AGENT_ID: action})
        env.update_scores(reward)
        step += 1
        if args.method in ("causal_shadow_v7","resource_competition_v8","persistent_resource_v9", "evidence_decision_v10", "evidence_repair_v11", "method_repair_v12", "intent_repair_v13") and (done or step >= args.steps):
            agent.observe_terminal(obs[AGENT_ID])
        cp = directory / "checkpoints" / f"{step:04d}"
        cp.mkdir(parents=True, exist_ok=True)
        save_snapshot(cp / "environment.pkl", env)
        atomic_json(cp / "agent.json", agent_state(agent, args.method))
        # Trace is one atomic record per environment step, safe after interruptions.
        atomic_json(directory / "trace" / f"{step:04d}.json", {"step": step,
            "observation": observation["text"], "action": action, "response": response,
            "next_observation": obs[AGENT_ID]["text"], "reward": vars(reward[AGENT_ID]),
            "scores": env.scores[AGENT_ID], "done": done, "info": info,
            "before_digest": before, "after_digest": state_digest(env)})
        env.update_config()
        status = {"steps": step, "checkpoint": cp.name, "complete": bool(done or step >= args.steps),
                  "termination": "environment" if done else ("step_limit" if step >= args.steps else None),
                  "scores": env.scores[AGENT_ID], "usage": usage_summary(directory / "api"),
                  "updated_utc": time.time()}
        atomic_json(current, status)
        print(json.dumps({"game": args.game, "method": args.method, **status}), flush=True)
        if status["complete"]:
            break


def main():
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=("prepare", "run", "status"))
    p.add_argument("--root", required=True)
    p.add_argument("--stage", default="round1")
    p.add_argument("--method", choices=METHODS)
    p.add_argument("--game", choices=GAMES)
    p.add_argument("--steps", type=int, default=300)
    p.add_argument("--key", default=os.environ.get("DEEPSEEK_KEY_FILE"))
    p.add_argument("--model", default="deepseek-flash")
    p.add_argument("--revision", default="uncommitted")
    p.add_argument("--transport-revision", default=None)
    p.add_argument("--disable-evidence-reuse", action="store_true", help="Matched V10 local-only control")
    p.add_argument('--evidence-mode',choices=('none','prompt','cache','structured'),default='structured')
    p.add_argument('--intent-mode',choices=('observe','enforce'),default='observe')
    p.add_argument('--evidence-context-scope',choices=('clock','attributes'),default='clock')
    p.add_argument("--fork-checkpoint", default=None,
                   help="Diagnostic continuation only; --steps is the absolute final step")
    args = p.parse_args()
    if args.command == "prepare":
        prepare(Path(args.root))
    elif args.command == "status":
        for path in sorted((Path(args.root)/args.stage).glob("*/*/current.json")):
            state = json.loads(path.read_text())
            print(path.parent.parent.name, path.parent.name, state["steps"],
                  state["scores"].get("quest"), state["complete"], state["usage"])
    else:
        if not all((args.method, args.game, args.key)):
            p.error("run requires --method, --game and --key")
        run(args)


if __name__ == "__main__":
    main()
