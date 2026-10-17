"""Resumable V16 full runs and predeclared selected-state mechanism comparisons."""
import argparse, contextlib, hashlib, json, sys, time
from pathlib import Path
from scar.io import atomic_json
from scar_public.provider import usage_summary
from scar_public.run import build_agent
from scar_public.experiments.paired_action_repair import PairedProvider


def main():
    from scar.environment import AGENT_ID, restore, save_snapshot, state_digest
    import fcntl
    p=argparse.ArgumentParser(); p.add_argument('--root',type=Path,required=True)
    p.add_argument('--initial',type=Path,required=True); p.add_argument('--checkpoint',type=Path)
    p.add_argument('--game',required=True); p.add_argument('--key',required=True)
    p.add_argument('--steps',type=int,default=300); p.add_argument('--arms',nargs='+',choices=('execute','observe'),default=['execute'])
    p.add_argument('--reuse-api',type=Path); a=p.parse_args(); a.root.mkdir(parents=True,exist_ok=True)
    lock=(a.root/'worker.lock').open('w'); fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    start=int(a.checkpoint.name) if a.checkpoint else 0
    initial=a.checkpoint/'environment.pkl' if a.checkpoint else a.initial
    manifest=dict(game=a.game,method='task_progress_v16',arms=a.arms,start_step=start,max_steps=a.steps,
        initial_sha256=hashlib.sha256(a.initial.read_bytes()).hexdigest(),
        fork_sha256=hashlib.sha256(initial.read_bytes()).hexdigest(),checkpoint=str(a.checkpoint) if a.checkpoint else None,
        source_manifest_sha256=hashlib.sha256(Path('source_manifest.json').read_bytes()).hexdigest(),
        primary_endpoint='Public main quest passed report within 300 total actions',
        qualification='Selected development continuation' if a.checkpoint else 'Familiar single development world')
    if (a.root/'manifest.json').exists(): assert json.loads((a.root/'manifest.json').read_text())==manifest
    atomic_json(a.root/'manifest.json',manifest)
    provider=PairedProvider(a.root/'api',a.key); provider.reuse_api=a.reuse_api; states={}; agents={}
    for arm in a.arms:
        out=a.root/arm; out.mkdir(exist_ok=True)
        if (out/'current.json').exists():
            status=json.loads((out/'current.json').read_text()); cp=out/'checkpoints'/status['checkpoint']; snapshot=cp/'environment.pkl'
        else:
            status=dict(steps=start,complete=False); cp=a.checkpoint; snapshot=initial
        env=restore(snapshot,out); agent=build_agent('task_progress_v16',env,provider)
        if cp: agent.notebook.load(json.loads((cp/'agent.json').read_text()))
        agent.notebook.progress_mode=arm; agent.resource_controller.context_scope='attributes'; agent.resource_controller.max_steps=a.steps
        states[arm]=(status,snapshot); agents[arm]=agent
    for step in range(min(s[0]['steps'] for s in states.values()),a.steps):
        for arm in a.arms:
            status,snapshot=states[arm]
            if status['complete'] or status['steps']!=step: continue
            out=a.root/arm; env=restore(snapshot,out); agent=agents[arm]
            provider.arm=arm; provider.step=step; provider.calls=[]
            obs=dict(text=env.obs[AGENT_ID]['text'],step=env.obs[AGENT_ID]['step']); started=time.perf_counter()
            with contextlib.redirect_stdout(sys.stderr): action,_,_,response=agent.act(obs)
            elapsed=time.perf_counter()-started; before=state_digest(env)
            after,reward,done,info=env.step({AGENT_ID:action}); env.update_scores(reward)
            text=after[AGENT_ID]['text']; passed='completed the main quest and passed the game' in text
            complete=bool(done or step+1>=a.steps)
            if complete: agent.observe_terminal(after[AGENT_ID])
            cp=out/'checkpoints'/f'{step+1:04d}'; cp.mkdir(parents=True,exist_ok=True)
            save_snapshot(cp/'environment.pkl',env); atomic_json(cp/'agent.json',agent.notebook.state())
            row=dict(step=step+1,observation=obs['text'],action=action,response=response,next_observation=text,
                scores=env.scores[AGENT_ID],done=done,main_quest_passed=passed,before_digest=before,
                after_digest=state_digest(env),actor_seconds=elapsed,provider_calls=provider.calls)
            atomic_json(out/'trace'/f'{step+1:04d}.json',row); env.update_config()
            status=dict(steps=step+1,checkpoint=cp.name,complete=complete,scores=env.scores[AGENT_ID],main_quest_passed=passed,
                        termination='environment' if done else 'step_limit' if complete else None)
            atomic_json(out/'current.json',status); states[arm]=(status,cp/'environment.pkl')
            print(json.dumps(dict(arm=arm,action=action,**status)),flush=True)
        atomic_json(a.root/'usage.json',usage_summary(provider.directory))
        if all(s[0]['complete'] for s in states.values()): break


if __name__=='__main__':main()
