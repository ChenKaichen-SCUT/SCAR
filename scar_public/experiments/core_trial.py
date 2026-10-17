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
    a=p.parse_args(); a.root.mkdir(parents=True,exist_ok=True)
    import fcntl
    lock=(a.root/'worker.lock').open('w'); fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    manifest=dict(game=a.game,repeat=a.repeat,max_steps=a.steps,arms=a.arms,
        source_sha256=hashlib.sha256(Path('source_manifest.json').read_bytes()).hexdigest(),
        sentry_revision=SENTRY_REVISION,model=a.model,hash_seed=os.environ.get('PYTHONHASHSEED'),
        world_seed_requested=None,actor_temperature=.7,actor_top_p=.8,
        actor_max_tokens=1536,sentry_temperature=0,sentry_max_tokens=4096,
        initial_source='existing-development-snapshot' if a.initial else 'fresh-post-freeze-draw',
        qualification='Independent stochastic draws of three familiar game families; not unseen-domain validation')
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
    agents={arm:CorePlannerAgent(provider,system,'checked' if arm=='checked' else 'prompt') for arm in a.arms if arm!='v16'}
    if 'v16' in a.arms:
        from scar_public.task_progress import TaskProgressAgent
        agents['v16']=TaskProgressAgent(provider,system)
        agents['v16'].resource_controller.mode='structured'
        agents['v16'].resource_controller.context_scope='attributes'
        agents['v16'].resource_controller.action_mode='execute'
        agents['v16'].notebook.progress_mode='observe'
    for agent in agents.values(): agent.max_steps=a.steps
    external={arm:SentryAdapter(agents[arm],provider,system,a.root/f'{arm}_events.jsonl')
              for arm in a.arms if arm=='sentry'}
    states={arm:initial.read_bytes() for arm in a.arms}
    stopped=set(); transition_cache={}; coupling=[]; results={}; total_tokens={arm:[0,0] for arm in a.arms}
    order=a.arms[a.repeat%len(a.arms):]+a.arms[:a.repeat%len(a.arms)]
    for step in range(a.steps):
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
            key=(before,action)
            if key in transition_cache:
                expected=transition_cache[key]
                assert (after,text)==expected, f'PAIRING FAILURE at {a.game}/{step}/{arm}'
                coupling.append(dict(step=step,arm=arm,matched=True))
            else: transition_cache[key]=(after,text)
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
            if path.exists():
                old=json.loads(path.read_text())
                assert all(old[k]==row[k] for k in ('action','before_digest','after_digest','observation')), 'Nonexact resume'
            else: atomic_json(path,row)
            status=dict(steps=step+1,complete=terminal,scores=env.scores[AGENT_ID],done=bool(done),
                        main_quest_passed=passed or results.get(arm,{}).get('main_quest_passed',False),
                        actor_tokens=total_tokens[arm],gate_overrides=sum(e['changed'] for e in getattr(agents[arm],'events',[])))
            results[arm]=status;atomic_json(out/'current.json',status)
            if terminal or (step+1)%25==0:
                cp=out/'checkpoints'/f'{step+1:04d}';cp.mkdir(parents=True,exist_ok=True)
                (cp/'environment.pkl').write_bytes(states[arm])
                atomic_json(cp/'agent.json',agents[arm].notebook.state())
                atomic_json(cp/'core_events.json',getattr(agents[arm],'events',[]))
        if (step+1)%10==0 or len(stopped)==len(a.arms):
            atomic_json(a.root/'usage.json',usage_summary(provider.directory))
            atomic_json(a.root/'coupling.json',coupling)
            print(json.dumps(dict(step=step+1,results=results)),flush=True)
        if len(stopped)==len(a.arms):break
    atomic_json(a.root/'result.json',dict(results=results,paired_transition_checks=len(coupling),
        usage=usage_summary(provider.directory)))


if __name__=='__main__':main()
