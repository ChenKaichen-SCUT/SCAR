"""Frozen, within-process paired full games; evaluator never enters the actor.

Fresh initial draws after freezing. Resume reconstructs from cached exact API
requests, and refuses any changed completed action. Independent repeats have
separate caches. Same-step identical calls inside a block share a draw.
"""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import sys
import time

from scar.environment import AGENT_ID, create_environment, restore, save_snapshot, snapshot, state_digest
from scar.io import atomic_json, append_jsonl
from scar_public.provider import Provider, usage_summary
from scar_public.core_planner import CorePlannerAgent
from scar_public.sentry_adapter import SentryAdapter, SENTRY_REVISION


class TrialProvider(Provider):
    def generate(self, user_prompt, system_prompt):
        result = super().generate(user_prompt, system_prompt)
        append_jsonl(self.directory.parent/'calls.jsonl', dict(step=self.step, arm=self.arm,
            prompt_sha256=hashlib.sha256((system_prompt+'\0'+user_prompt).encode()).hexdigest(),
            response_sha256=hashlib.sha256(result['response'].encode()).hexdigest(),
            input_tokens=result['num_input_tokens'], output_tokens=result['num_output_tokens']))
        return result


def build_system(env, model):
    from agents.llm_agent_config import LLMAgentConfig
    cfg = LLMAgentConfig(torch_seed=None, llm_name=model, llm_provider='audited-deepseek',
        max_new_tokens=1536, temperature=.7, top_p=.8, presence_penalty=0,
        short_term_memory_size=5, enable_reflection=False, enable_summarization=False)
    cfg.available_actions = env.agents[0].available_actions
    cfg.__post_init__()
    return cfg.system_prompt


def build_trial_agent(arm, provider, system, repair_quota=None, max_steps=300):
    if arm == 'objective':
        from scar_public.objective_repair import ObjectiveRepairAgent
        return ObjectiveRepairAgent(provider, system)
    if arm == 'hypothesis':
        from scar_public.hypothesis_repair import HypothesisRepairAgent
        return HypothesisRepairAgent(provider, system)
    if arm == 'obstacle':
        from scar_public.obstacle_repair import ObstacleRepairAgent
        return ObstacleRepairAgent(provider, system)
    if arm=='continuation_scheduled':
        from scar_public.experiments.scheduled_continuation import ScheduledContinuationAgent
        if repair_quota is None:
            raise ValueError('Scheduled control requires a declared repair quota')
        return ScheduledContinuationAgent(provider,system,repair_quota,max_steps)
    if arm in ('continuation', 'continuation_advice', 'continuation_generic'):
        from scar_public.continuation import ContinuationAgent
        if arm=='continuation_generic':
            from scar_public.continuation_control import GenericContinuationAgent
            return GenericContinuationAgent(provider,system,'repair')
        return ContinuationAgent(provider,system,'advice' if arm=='continuation_advice' else 'repair')
    if arm in ('prompt','checked','sentry'):
        return CorePlannerAgent(provider,system,'checked' if arm=='checked' else 'prompt')
    if arm=='v16':
        from scar_public.task_progress import TaskProgressAgent
        agent=TaskProgressAgent(provider,system)
        agent.resource_controller.mode='structured';agent.resource_controller.context_scope='attributes'
        agent.resource_controller.action_mode='execute';agent.notebook.progress_mode='observe'
        return agent
    raise ValueError('Unknown study arm: '+arm)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--game',required=True,choices=['remnant','mark','metropolis'])
    p.add_argument('--repeat',type=int,required=True)
    p.add_argument('--steps',type=int,default=300)
    p.add_argument('--key',required=True)
    p.add_argument('--model',default='deepseek-flash')
    p.add_argument('--initial',type=Path)
    p.add_argument('--arms',nargs='+',default=['prompt','checked','sentry','v16'])
    p.add_argument('--repair-quota',type=int)
    p.add_argument('--initial-kind',choices=['existing-development-snapshot','paired-independent-snapshot'],
                   default='existing-development-snapshot')
    a=p.parse_args(); a.root.mkdir(parents=True,exist_ok=True)
    import fcntl
    lock=(a.root/'worker.lock').open('w'); fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    manifest=dict(game=a.game,repeat=a.repeat,max_steps=a.steps,arms=a.arms,
        source_sha256=hashlib.sha256(Path('source_manifest.json').read_bytes()).hexdigest(),
        sentry_revision=SENTRY_REVISION,model=a.model,hash_seed=os.environ.get('PYTHONHASHSEED'),
        world_seed_requested=None,actor_temperature=.7,actor_top_p=.8,
        actor_max_tokens=1536,sentry_temperature=0,sentry_max_tokens=4096,
        initial_source=a.initial_kind if a.initial else 'fresh-post-freeze-draw',
        qualification='Independent stochastic draws of three familiar game families; not unseen-domain validation')
    if a.repair_quota is not None:manifest['scheduled_repair_quota']=a.repair_quota
    if (a.root/'manifest.json').exists():
        assert json.loads((a.root/'manifest.json').read_text())==manifest
    atomic_json(a.root/'manifest.json',manifest)
    initial=a.root/'initial.pkl'
    if not initial.exists():
        if a.initial:
            initial.write_bytes(a.initial.read_bytes())
        else:
            with contextlib.redirect_stdout(sys.stderr):
                env,_=create_environment(a.game,None,a.root/'initial_environment')
            save_snapshot(initial,env)
    env=restore(initial)
    atomic_json(a.root/'initial_receipt.json',dict(seed=env.seed,
        sha256=hashlib.sha256(initial.read_bytes()).hexdigest(),state_digest=state_digest(env)))
    provider=TrialProvider(a.root/'api',a.key,a.model)
    system=build_system(env,a.model)
    agents={arm:build_trial_agent(arm,provider,system,a.repair_quota,a.steps) for arm in a.arms}
    for agent in agents.values(): agent.max_steps=a.steps
    external={arm:SentryAdapter(agents[arm],provider,system,a.root/f'{arm}_events.jsonl')
              for arm in a.arms if arm=='sentry'}
    states={arm:initial.read_bytes() for arm in a.arms}
    lineage={arm:hashlib.sha256(initial.read_bytes()).hexdigest() for arm in a.arms}
    matched_prefix=True; continuation_matched_prefix=True
    stopped=set(); transition_cache={}; coupling=[]; results={}; total_tokens={arm:[0,0] for arm in a.arms}
    order=a.arms[a.repeat%len(a.arms):]+a.arms[:a.repeat%len(a.arms)]
    for step in range(a.steps):
        round_rows={}
        for arm in order:
            if arm in stopped: continue
            out=a.root/arm; out.mkdir(exist_ok=True)
            env=restore(states[arm],out)
            observation=dict(text=env.obs[AGENT_ID]['text'],step=env.obs[AGENT_ID]['step'])
            before=state_digest(env)
            provider.arm=arm; provider.step=step
            started=time.perf_counter()
            with contextlib.redirect_stdout(sys.stderr):
                action,inp,outp,response=agents[arm].act(observation)
            actor_seconds=time.perf_counter()-started
            total_tokens[arm][0]+=inp;total_tokens[arm][1]+=outp
            # Agent/Sentry computation cannot perturb the environment RNG.
            env=restore(states[arm],out)
            with contextlib.redirect_stdout(sys.stderr):
                obs,reward,done,info=env.step({AGENT_ID:action}); env.update_scores(reward)
            after=state_digest(env); text=obs[AGENT_ID]['text']
            passed = 'completed the main quest and passed the game' in text
            states[arm]=snapshot(env)
            # Complete shared action-prefix identity, not a possibly incomplete
            # state abstraction, defines a counterfactual coupling check.
            key=(lineage[arm],action)
            if key in transition_cache:
                expected=transition_cache[key]
                assert (before,after,text)==expected, f'PAIRING FAILURE at {a.game}/{step}/{arm}'
                coupling.append(dict(step=step,arm=arm,matched=True))
            else: transition_cache[key]=(before,after,text)
            lineage[arm]=hashlib.sha256((lineage[arm]+'\0'+action).encode()).hexdigest()
            terminal=bool(done or step+1>=a.steps)
            parsed=json.loads(response)
            intervention=external[arm].observe(step,parsed,text,terminal) if arm in external else False
            if terminal:
                agents[arm].observe_terminal(obs[AGENT_ID]);stopped.add(arm)
            row=dict(step=step+1,observation=observation['text'],action=action,response=response,
                next_observation=text,scores=env.scores[AGENT_ID],done=bool(done),
                main_quest_passed=passed,
                before_digest=before,after_digest=after,actor_seconds=actor_seconds,
                input_tokens=inp,output_tokens=outp,sentry_intervention=intervention)
            path=out/'trace'/f'{step+1:04d}.json'
            round_rows[arm]=(row,parsed)
            if path.exists():
                old=json.loads(path.read_text())
                assert all(old[k]==row[k] for k in ('action','before_digest','after_digest','observation')), 'Nonexact resume'
            else: atomic_json(path,row)
            status=dict(steps=step+1,complete=terminal,scores=env.scores[AGENT_ID],done=bool(done),
                        main_quest_passed=passed or results.get(arm,{}).get('main_quest_passed',False),
                        actor_tokens=total_tokens[arm],gate_overrides=sum(e['changed'] for e in getattr(agents[arm],'events',[])))
            if hasattr(agents[arm],'continuation_events'):
                status['continuation_overrides']=sum(e['changed'] for e in agents[arm].continuation_events)
            results[arm]=status;atomic_json(out/'current.json',status)
            if terminal or (step+1)%25==0:
                cp=out/'checkpoints'/f'{step+1:04d}';cp.mkdir(parents=True,exist_ok=True)
                (cp/'environment.pkl').write_bytes(states[arm])
                atomic_json(cp/'agent.json',agents[arm].notebook.state())
                atomic_json(cp/'core_events.json',getattr(agents[arm],'events',[]))
                if hasattr(agents[arm],'continuation'):
                    atomic_json(cp/'continuation.json',agents[arm].continuation.state())
        if matched_prefix and 'prompt' in round_rows and 'checked' in round_rows:
            left,x=round_rows['prompt'];right,y=round_rows['checked']
            assert left['before_digest']==right['before_digest'] and left['observation']==right['observation']
            assert x['core_packet']==y['core_packet'], 'Same-history packet divergence'
            assert x['core_initial_proposal']==y['core_initial_proposal'], 'Same-history proposal divergence'
            assert x['core_gate']['proposed']==y['core_gate']['proposed'], 'Same-history revision divergence'
            if left['action']==right['action']:
                assert agents['prompt'].notebook.state()==agents['checked'].notebook.state(), 'Non-action intervention changed memory'
            else:
                assert y['core_gate']['changed'], 'Action divergence outside the gate'
                matched_prefix=False
        if continuation_matched_prefix and 'continuation_generic' in round_rows and 'checked' in round_rows:
            left,x=round_rows['checked'];right,y=round_rows['continuation_generic']
            assert left['before_digest']==right['before_digest']
            assert x['core_initial_proposal']==y['core_initial_proposal']
            assert x['core_packet']==y['core_packet']
            if left['action']==right['action']:
                assert agents['checked'].notebook.state()==agents['continuation_generic'].notebook.state()
            else:
                assert y['continuation']['changed'], 'Unexplained compact divergence'
                continuation_matched_prefix=False
        if (step+1)%10==0 or len(stopped)==len(a.arms):
            atomic_json(a.root/'usage.json',usage_summary(provider.directory))
            atomic_json(a.root/'coupling.json',coupling)
            print(json.dumps(dict(step=step+1,results=results)),flush=True)
        if len(stopped)==len(a.arms):break
    atomic_json(a.root/'result.json',dict(results=results,paired_transition_checks=len(coupling),
        usage=usage_summary(provider.directory)))


if __name__=='__main__':main()
