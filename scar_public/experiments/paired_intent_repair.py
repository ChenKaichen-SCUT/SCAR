"""Common-response paired continuations; policy never sees evaluator state.

Identical provider requests at the same step share a draw. Arms execute in
alternation, with each engine's Python/NumPy RNG restored before its step.
The public completion stopping rule is evaluator-only and predeclared.
"""
import argparse,contextlib,hashlib,json,sys,time
from pathlib import Path
from scar.io import atomic_json,append_jsonl
from scar.environment import AGENT_ID,restore,save_snapshot,state_digest
from scar_public.provider import Provider,usage_summary,peak_cost
from scar_public.run import build_agent
from scar_public.intent_repair import IntentMemory,IntentController


def historical_intents(checkpoint):
    """Warm only the new registry from recorded public decisions up to the fork."""
    m=IntentMemory();c=IntentController(m);c.intervention_mode='observe'
    for path in sorted((checkpoint.parent.parent/'trace').glob('*.json')):
        if int(path.stem)>int(checkpoint.name):break
        r=json.loads(path.read_text());parsed=json.loads(r['response']);step=r['step']-1
        m.prompt(r['observation']);c.prepare_decision(r['observation'],step)
        c.assess(parsed,step,'historical_public_intent');m.update(parsed,r['observation'],step)
    return dict(intent_tasks=m.intent_tasks,intent_anchors=m.intent_anchors,
        intent_observed_count=m.intent_observed_count)


class PairedProvider(Provider):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.arm='observe';self.calls=[]

    def generate(self,user_prompt,system_prompt):
        before=usage_summary(self.directory);started=time.perf_counter()
        result=super().generate(user_prompt,system_prompt)
        after=usage_summary(self.directory)
        row=dict(arm=self.arm,step=self.step,
            prompt_sha256=hashlib.sha256((system_prompt+'\0'+user_prompt).encode()).hexdigest(),
            response_sha256=hashlib.sha256(result['response'].encode()).hexdigest(),
            response=result['response'],input_tokens=result['num_input_tokens'],output_tokens=result['num_output_tokens'],
            new_requests=after['requests']-before['requests'],
            paid_usd=after['peak_usd_estimate']-before['peak_usd_estimate'],
            elapsed_s=time.perf_counter()-started)
        append_jsonl(self.directory.parent/'provider_calls.jsonl',row);self.calls.append(row)
        return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--key',required=True)
    p.add_argument('--stop-report',required=True);p.add_argument('--steps',type=int,default=300)
    a=p.parse_args();a.root.mkdir(parents=True,exist_ok=True)
    import fcntl
    lock=(a.root/'worker.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    start=int(a.checkpoint.name);source=json.loads((a.checkpoint.parent.parent/'manifest.json').read_text())
    manifest=dict(game=source['game'],checkpoint=str(a.checkpoint),start_step=start,max_steps=a.steps,
        checkpoint_sha256=hashlib.sha256((a.checkpoint/'environment.pkl').read_bytes()).hexdigest(),
        agent_sha256=hashlib.sha256((a.checkpoint/'agent.json').read_bytes()).hexdigest(),
        source_manifest_sha256=hashlib.sha256(Path('source_manifest.json').read_bytes()).hexdigest(),
        stopping_public_report=a.stop_report,design='Same prompt, parser, planner, step-specific provider draw; only bounded review enforcement differs',
        qualification='Selected development checkpoint; stochastic after intervention, not independent validation')
    if (a.root/'manifest.json').exists():assert json.loads((a.root/'manifest.json').read_text())==manifest
    atomic_json(a.root/'manifest.json',manifest)
    provider=PairedProvider(a.root/'api',a.key);agents={};states={}
    for arm in ('observe','enforce'):
        out=a.root/arm;out.mkdir(exist_ok=True)
        if (out/'current.json').exists():
            state=json.loads((out/'current.json').read_text());cp=out/'checkpoints'/state['checkpoint']
        else:
            state=dict(steps=start,complete=False);cp=a.checkpoint
        env=restore(cp/'environment.pkl',out)
        agent=build_agent('intent_repair_v13',env,provider)
        saved=json.loads((cp/'agent.json').read_text())
        if 'intent_anchors' not in saved:saved.update(historical_intents(a.checkpoint))
        agent.notebook.load(saved)
        agent.resource_controller.intervention_mode=arm
        agent.resource_controller.mode='structured';agent.resource_controller.context_scope='clock'
        agents[arm]=agent;states[arm]=(state,cp)
    for step in range(min(s[0]['steps'] for s in states.values()),a.steps):
        for arm in ('observe','enforce'):
            status,cp=states[arm]
            if status['complete'] or status['steps']!=step:continue
            out=a.root/arm;env=restore(cp/'environment.pkl',out);agent=agents[arm]
            provider.arm=arm;provider.step=step;provider.calls=[]
            observation=dict(text=env.obs[AGENT_ID]['text'],step=env.obs[AGENT_ID]['step'])
            started=time.perf_counter()
            with contextlib.redirect_stdout(sys.stderr):action,_,_,response=agent.act(observation)
            actor_seconds=time.perf_counter()-started;before=state_digest(env)
            obs,reward,done,info=env.step({AGENT_ID:action});env.update_scores(reward)
            public_done=a.stop_report in obs[AGENT_ID]['text']
            complete=bool(done or public_done or step+1>=a.steps)
            cp=out/'checkpoints'/f'{step+1:04d}';cp.mkdir(parents=True,exist_ok=True)
            save_snapshot(cp/'environment.pkl',env);atomic_json(cp/'agent.json',agent.notebook.state())
            row=dict(step=step+1,observation=observation['text'],action=action,response=response,
                next_observation=obs[AGENT_ID]['text'],scores=env.scores[AGENT_ID],done=done,
                target_public_report=public_done,before_digest=before,after_digest=state_digest(env),
                actor_seconds=actor_seconds,provider_calls=provider.calls)
            atomic_json(out/'trace'/f'{step+1:04d}.json',row);env.update_config()
            status=dict(steps=step+1,checkpoint=cp.name,complete=complete,scores=env.scores[AGENT_ID],
                target_public_report=public_done,termination='environment' if done else 'target_public_report' if public_done else 'step_limit' if complete else None)
            atomic_json(out/'current.json',status);states[arm]=(status,cp)
            print(json.dumps(dict(arm=arm,action=action,**status)),flush=True)
        atomic_json(a.root/'usage.json',usage_summary(provider.directory))
        if all(s[0]['complete'] for s in states.values()):break


if __name__=='__main__':main()
