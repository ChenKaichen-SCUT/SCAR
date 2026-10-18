"""Paired persistent-repair arms, reusing frozen original Sentry trajectories.

The first12 actions after the first failed verification form an initial probe.
Continue the SAME runs afterwards using exact response caches, no new samples.
Original baselines are never rerun with paid calls. Prefix UUIDs are aligned
only after checking identical public playbook content, before prompt rendering.
"""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import sys

from scar.environment import AGENT_ID,restore,snapshot,state_digest
from scar.io import atomic_json,append_jsonl
from scar_public.provider import usage_summary
from scar_public.sentry_evidence import LongContextActor,SentryEvidenceHost
from scar_public.sentry_persistent import PersistentRepair,apply_choice
from scar_public.sentry_selective import SelectiveRepair
from scar_public.experiments.sentry_foundation_trial import SharedProvider,system_prompt


class TrialProvider(SharedProvider):
    cache_only=False
    def request(self,messages,repair=0,options=None):
        if self.cache_only:
            payload=dict(model=self.model,messages=messages,temperature=.7,top_p=.8,presence_penalty=0,
                max_tokens=1536,thinking={'type':'disabled'},response_format={'type':'json_object'})
            if options:payload.update(options)
            h=hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
            if not (self.shared/f'{self.step:04d}-{repair}-{h[:16]}.response.json').exists():
                raise RuntimeError(f'Missing exact prefix request at {self.step}/{repair}; paid fallback forbidden')
        return super().request(messages,repair,options)


def event_cycles(path):
    result={};current=-1
    for line in path.read_text().splitlines():
        e=json.loads(line)
        if e['type']=='agent_step':current=e['step_id']
        result.setdefault(current,[]).append(e)
    return result


def align_playbook_identity(host,provider,prefix,old_events):
    original=host.runner.guard.updater.summarize
    def summarize(event,result):
        insight=original(event,result)
        if insight is None:return None
        body=insight.to_json();body.pop('insight_id');body.pop('insertion_step')
        if prefix[0]:
            old=[e['entry'] for e in old_events.get(provider.step,[]) if e['type']=='playbook_update']
            assert len(old)==1,'Prefix playbook update count differs'
            expected=dict(old[0]);expected.pop('insight_id');expected.pop('insertion_step')
            assert body==expected,'Prefix playbook semantic content differs'
            insight.insight_id=old[0]['insight_id']
        else:
            text=json.dumps(body,sort_keys=True)+str(provider.step)
            insight.insight_id='sentry-'+hashlib.sha256(text.encode()).hexdigest()[:10]
        return insight
    host.runner.guard.updater.summarize=summarize


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--old',type=Path,required=True);p.add_argument('--mode',choices=['advice','execute','selective'],required=True)
    p.add_argument('--key',required=True);p.add_argument('--stop-after-repair',type=int,default=0)
    a=p.parse_args();out=a.root/a.mode;out.mkdir(parents=True,exist_ok=True)
    import fcntl
    lock=(out/'worker.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    initial=(a.old/'initial.pkl').read_bytes();receipt=json.loads((a.old/'initial_receipt.json').read_text())
    assert receipt['hash_seed']==os.environ['PYTHONHASHSEED']
    manifest=dict(mode=a.mode,initial_receipt=receipt,source_manifest_sha256=hashlib.sha256(Path('source_manifest.json').read_bytes()).hexdigest(),
        steps=300,max_repair_calls=30,burst_actions=6,qualification='Known development worlds; existing baselines reused. First12 post-trigger actions are an interim probe, then SAME cached continuation to300.')
    if (out/'manifest.json').exists():assert json.loads((out/'manifest.json').read_text())==manifest
    else:atomic_json(out/'manifest.json',manifest)
    provider=TrialProvider(out/'api',a.key,shared=a.root/'shared_api');provider.arm=a.mode
    env=restore(initial);system=system_prompt(env,provider.model)
    actor=LongContextActor(provider,system);host=SentryEvidenceHost(provider,system)
    control=SelectiveRepair(provider,system) if a.mode=='selective' else PersistentRepair(provider,system,a.mode)
    control.seed(env.obs[AGENT_ID]['text'])
    original_events=event_cycles(a.old/'sentry/sentry_events.jsonl');prefix=[True];identity_prefix=[True]
    align_playbook_identity(host,provider,identity_prefix,original_events)
    state=initial;first_trigger=None;matched=0;replays=0;first_choice=False
    scores0=env.scores.get(AGENT_ID,{}).get('quest',0);failures=0;last_gain=0;old_score=scores0
    for step in range(300):
        provider.step=step;provider.cache_only=control.calls==0;identity_prefix[0]=control.calls==0
        env=restore(state,out/'environment');text=env.obs[AGENT_ID]['text'];before=state_digest(env)
        proposed,_=actor.act(text);chosen=apply_choice(actor,step,text,proposed,control)
        old=json.loads((a.old/'sentry/trace'/f'{step+1:04d}.json').read_text())
        if prefix[0]:
            assert before==old['before_digest'] and text==old['observation']
            if chosen['action']!=old['action']:prefix[0]=False
            else:matched+=1
        with contextlib.redirect_stdout(sys.stderr):
            env=restore(state,out/'environment');obs,reward,done,_=env.step({AGENT_ID:chosen['action']});env.update_scores(reward)
            following=obs[AGENT_ID]['text'];after=state_digest(env);next_state=snapshot(env)
            replay=restore(state,out/'replay');ro,rr,rd,_=replay.step({AGENT_ID:chosen['action']});replay.update_scores(rr)
            assert state_digest(replay)==after and ro[AGENT_ID]['text']==following and rd==done
            if prefix[0]:assert after==old['after_digest'] and following==old['next_observation']
        replays+=1;terminal=bool(done or step==299)
        guidance,events=host.observe(step,chosen,following,terminal)
        eligible=control.events[-1]['eligible']
        pending=control.pending
        provider.cache_only=False
        extra=control.observe(step,chosen,following,events,terminal)
        if first_trigger is None and control.calls:first_trigger=step
        actor.guidance=guidance+extra
        row=dict(step=step+1,observation=text,response=chosen,proposed=proposed,action=chosen['action'],
            next_observation=following,scores=env.scores[AGENT_ID],before_digest=before,after_digest=after,
            done=bool(done),persistent_events=control.events,sentry_events=events)
        path=out/'trace'/f'{step+1:04d}.json'
        if path.exists():
            previous=json.loads(path.read_text())
            assert all(previous[k]==row[k] for k in ('before_digest','after_digest','action','response','proposed')),'Non-exact cached continuation'
        else:atomic_json(path,row)
        if eligible and not first_choice:
            atomic_json(out/'first_choice.json',dict(step=step+1,before_digest=before,observation=text,card=pending['card'],
                proposed=proposed,chosen=chosen,following=following,after_digest=after))
            first_choice=True
        control.events=[];state=next_state
        from scar_public.continuation import feedback_lines
        failures+=bool(feedback_lines(following));score=env.scores[AGENT_ID]['quest']
        if score>old_score:last_gain=step+1
        old_score=score
        current=dict(steps=step+1,scores=env.scores[AGENT_ID],passed='completed the main quest and passed the game' in following,
            done=bool(done),repair_calls=control.calls,comparison_calls=getattr(control,'comparisons',0),first_trigger_cycle=first_trigger,prefix_matches=matched,
            replays=replays,failures=failures,last_gain_step=last_gain)
        atomic_json(out/'current.json',current)
        if a.stop_after_repair and first_trigger is not None and step-first_trigger>=a.stop_after_repair:
            atomic_json(out/'probe_result.json',dict(**current,usage=usage_summary(out/'api')));return
        if terminal:break
    atomic_json(out/'result.json',dict(**current,usage=usage_summary(out/'api')))
    (out/'last_environment.pkl').write_bytes(state)
    print(json.dumps(current),flush=True)


if __name__=='__main__':main()
