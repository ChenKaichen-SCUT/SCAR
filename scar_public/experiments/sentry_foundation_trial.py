"""Clean ReAct/LongContext with author Sentry; isolated evidence-access pilot.

One process per arm. A process-safe, per-world exact-request cache couples
identical calls without coupling different worlds. Private engine states never
enter the actor or monitor. Every actual action is replayed from the same state.
"""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import sys

from scar.environment import AGENT_ID,create_environment,restore,snapshot,state_digest
from scar.io import append_jsonl,atomic_json
from scar_public.provider import Provider,usage_summary
from scar_public.sentry_evidence import LongContextActor,SentryEvidenceHost


class SharedProvider(Provider):
    def __init__(self,*args,shared,**kwargs):
        super().__init__(*args,**kwargs);self.shared=Path(shared);self.shared.mkdir(exist_ok=True,parents=True)

    def request(self,messages,repair=0,options=None):
        import fcntl
        payload=dict(model=self.model,messages=messages,temperature=.7,top_p=.8,presence_penalty=0,
            max_tokens=1536,thinking={'type':'disabled'},response_format={'type':'json_object'})
        if options:payload.update(options)
        h=hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
        prefix=self.shared/f'{self.step:04d}-{repair}-{h[:16]}'
        with prefix.with_suffix('.lock').open('w') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            cache=prefix.with_suffix('.response.json')
            if cache.exists():
                append_jsonl(self.directory/'shared_reuse.jsonl',dict(step=self.step,request_hash=h,source=str(cache)))
                return json.loads(cache.read_text())
            result=super().request(messages,repair,options)
            atomic_json(cache,result)
            return result


def system_prompt(env,model):
    from agents.llm_agent_config import LLMAgentConfig
    cfg=LLMAgentConfig(torch_seed=None,llm_name=model,llm_provider='audited-deepseek',
        max_new_tokens=1536,temperature=.7,top_p=.8,presence_penalty=0,
        enable_reflection=False,enable_summarization=False)
    cfg.available_actions=env.agents[0].available_actions;cfg.__post_init__()
    return cfg.system_prompt


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--game',choices=['mark','metropolis','remnant'],required=True)
    p.add_argument('--arm',choices=['prepare','base','sentry','evidence'],required=True)
    p.add_argument('--key');p.add_argument('--steps',type=int,default=300)
    a=p.parse_args();a.root.mkdir(parents=True,exist_ok=True)
    initial=a.root/'initial.pkl'
    if a.arm=='prepare':
        if initial.exists():raise FileExistsError(initial)
        with contextlib.redirect_stdout(sys.stderr):env,_=create_environment(a.game,None,a.root/'initial_environment')
        initial.write_bytes(snapshot(env))
        atomic_json(a.root/'initial_receipt.json',dict(game=a.game,actual_world_seed=env.seed,
            hash_seed=os.environ['PYTHONHASHSEED'],state_digest=state_digest(env),
            sha256=hashlib.sha256(initial.read_bytes()).hexdigest(),requested_world_seed=None))
        return
    import fcntl
    out=a.root/a.arm;out.mkdir(parents=True,exist_ok=True)
    lock=(out/'worker.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    receipt=json.loads((a.root/'initial_receipt.json').read_text())
    assert receipt['hash_seed']==os.environ['PYTHONHASHSEED']
    atomic_json(out/'manifest.json',dict(arm=a.arm,steps=a.steps,initial_receipt=receipt,
        source_sha256=hashlib.sha256(Path('source_manifest.json').read_bytes()).hexdigest(),
        qualification='One fresh draw per familiar game after code freeze. Development pilot, not significance or unseen-domain evidence.'))
    provider=SharedProvider(out/'api',a.key,shared=a.root/'shared_api');provider.arm=a.arm
    state=initial.read_bytes();env=restore(state)
    system=system_prompt(env,provider.model);actor=LongContextActor(provider,system)
    host=SentryEvidenceHost(provider,system,a.arm=='evidence',a.steps) if a.arm!='base' else None
    replay_count=0;errors=0;last_gain=0;old_score=0
    for step in range(a.steps):
        provider.step=step
        env=restore(state,out/'environment');text=env.obs[AGENT_ID]['text'];before=state_digest(env)
        parsed,reply=actor.act(text)
        with contextlib.redirect_stdout(sys.stderr):
            env=restore(state,out/'environment');obs,reward,done,_=env.step({AGENT_ID:parsed['action']});env.update_scores(reward)
            following=obs[AGENT_ID]['text'];after=state_digest(env);next_state=snapshot(env)
            replay=restore(state,out/'replay');ro,rr,rd,_=replay.step({AGENT_ID:parsed['action']});replay.update_scores(rr)
            assert state_digest(replay)==after and ro[AGENT_ID]['text']==following and rd==done
        replay_count+=1;terminal=bool(done or step+1==a.steps)
        if host:
            guidance,events=host.observe(step,parsed,following,terminal)
            actor.guidance=guidance
            for event in events:append_jsonl(out/'sentry_events.jsonl',event)
            for event in host.judge.records:append_jsonl(out/'retrieval.jsonl',event)
            host.judge.records.clear()
        row=dict(step=step+1,observation=text,action=parsed['action'],response=parsed,
            next_observation=following,scores=env.scores[AGENT_ID],done=bool(done),
            before_digest=before,after_digest=after)
        path=out/'trace'/f'{step+1:04d}.json'
        if path.exists():assert json.loads(path.read_text())==row,'Non-exact resume'
        else:atomic_json(path,row)
        score=env.scores[AGENT_ID]['quest']
        if score>old_score:last_gain=step+1
        old_score=score
        from scar_public.continuation import feedback_lines
        errors+=bool(feedback_lines(following))
        result=dict(steps=step+1,scores=env.scores[AGENT_ID],done=bool(done),
            passed='completed the main quest and passed the game' in following,
            failures=errors,last_gain_step=last_gain,replays=replay_count)
        atomic_json(out/'current.json',result)
        state=next_state
        if terminal or (step+1)%25==0:
            (out/'last_environment.pkl').write_bytes(state)
            atomic_json(out/'usage.json',usage_summary(out/'api'))
            print(json.dumps(result),flush=True)
        if done:break
    atomic_json(out/'result.json',dict(**result,usage=usage_summary(out/'api')))


if __name__=='__main__':main()
