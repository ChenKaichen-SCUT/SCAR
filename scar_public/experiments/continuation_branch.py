"""Same-state development branches with exact cached baseline and public replay.

The old trajectory is used only for prefix reconstruction and evaluator checks.
At/after the fork, each actor sees solely its own observations. All arms use the
same frozen code except the continuation authority. No baseline API reruns.
"""
import argparse
import contextlib
import copy
import hashlib
import json
import os
from pathlib import Path
import sys

from scar.environment import AGENT_ID, restore, snapshot, state_digest
from scar.io import atomic_json, append_jsonl
from scar_public.provider import Provider, usage_summary
from scar_public.continuation import ContinuationAgent
from scar_public.experiments.core_trial import build_system


class ReusingProvider(Provider):
    def __init__(self, *args, historical, additional_historical=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.historical = historical
        self.additional_historical = tuple(additional_historical)
        self.cache_only = False

    def request(self, messages, repair=0, options=None):
        payload = dict(model=self.model, messages=messages, temperature=.7, top_p=.8,
                       presence_penalty=0, max_tokens=1536, thinking={'type':'disabled'},
                       response_format={'type':'json_object'})
        if options: payload.update(options)
        h = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        for directory in (self.historical, *self.additional_historical):
            cache = directory/f'{self.step:04d}-{repair}-{h[:16]}.response.json'
            if cache.exists():
                append_jsonl(self.directory/'historical_reuse.jsonl', dict(step=self.step, arm=getattr(self,'arm',None), hash=h, source=str(directory)))
                return json.loads(cache.read_text())
        if self.cache_only:
            raise RuntimeError(f'Historical prefix/baseline request missing at step {self.step}, hash {h}; no paid fallback')
        return super().request(messages, repair, options)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--block', type=Path, required=True)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--start', type=int, required=True)
    p.add_argument('--horizon', type=int, default=40)
    p.add_argument('--key', required=True)
    p.add_argument('--arms', nargs='+', default=['off','advice','repair'])
    p.add_argument('--generic-evidence', action='store_true')
    a = p.parse_args(); a.root.mkdir(parents=True,exist_ok=True)
    import fcntl
    lock=(a.root/'worker.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    manifest=json.loads((a.block/'manifest.json').read_text())
    assert os.environ['PYTHONHASHSEED']==manifest['hash_seed']
    protocol=dict(source_manifest=hashlib.sha256(Path('source_manifest.json').read_bytes()).hexdigest(),
                  block=a.block.name, start=a.start, horizon=a.horizon, arms=a.arms,
                  hash_seed=manifest['hash_seed'], qualification='Selected development states; not independent whole-game evaluation')
    if a.generic_evidence:protocol['evidence_exposure']='generic_reconsideration_with_original_ledger'
    if (a.root/'manifest.json').exists():assert json.loads((a.root/'manifest.json').read_text())==protocol
    atomic_json(a.root/'manifest.json',protocol)
    provider=ReusingProvider(a.root/'api',a.key,historical=a.block/'api')
    provider.cache_only=True;provider.arm='prefix'
    state=(a.block/'initial.pkl').read_bytes()
    env=restore(state)
    agent_class=ContinuationAgent
    if a.generic_evidence:
        from scar_public.continuation_control import GenericContinuationAgent
        agent_class=GenericContinuationAgent
    agent=agent_class(provider,build_system(env,provider.model),'off')
    replay_dir=a.root/'private_replay';replay_dir.mkdir(exist_ok=True)
    for step in range(a.start):
        row=json.loads((a.block/'checked/trace'/f'{step+1:04d}.json').read_text())
        provider.step=step
        with contextlib.redirect_stdout(sys.stderr):
            action,*_=agent.act(dict(text=row['observation'],step=step))
            assert action==row['action'], (step,'actor')
            env=restore(state,replay_dir)
            assert state_digest(env)==row['before_digest'], (step,'before')
            obs,reward,done,_=env.step({AGENT_ID:action});env.update_scores(reward)
            assert state_digest(env)==row['after_digest'], (step,'after')
            state=snapshot(env)
    agent.llm=None
    agents={arm:copy.deepcopy(agent) for arm in a.arms}
    for arm, actor in agents.items():actor.llm=provider;actor.repair_mode=arm
    states={arm:state for arm in a.arms};stopped=set();results={}
    initial_scores=copy.deepcopy(restore(state).scores[AGENT_ID])
    (a.root/'fork_environment.pkl').write_bytes(state)
    atomic_json(a.root/'fork_public_memory.json',agent.notebook.state())
    comparisons=[]
    for step in range(a.start,min(300,a.start+a.horizon)):
        rows={}
        for arm in a.arms:
            if arm in stopped:continue
            out=a.root/arm;out.mkdir(exist_ok=True)
            provider.step=step;provider.arm=arm;provider.cache_only=arm=='off'
            env=restore(states[arm],out);text=env.obs[AGENT_ID]['text'];before=state_digest(env)
            with contextlib.redirect_stdout(sys.stderr):
                action,inp,outp,response=agents[arm].act(dict(text=text,step=step))
                env=restore(states[arm],out)
                obs,reward,done,_=env.step({AGENT_ID:action});env.update_scores(reward)
                after=state_digest(env);states[arm]=snapshot(env)
            if arm=='off':
                old=json.loads((a.block/'checked/trace'/f'{step+1:04d}.json').read_text())
                assert action==old['action'] and after==old['after_digest'], (step,'baseline')
            parsed=json.loads(response)
            row=dict(step=step,observation=text,action=action,response=parsed,
                     next_observation=obs[AGENT_ID]['text'],scores=env.scores[AGENT_ID],done=bool(done),
                     before_digest=before,after_digest=after,input_tokens=inp,output_tokens=outp)
            path=out/'trace'/f'{step:04d}.json'
            if path.exists():
                old=json.loads(path.read_text());assert all(row[k]==old[k] for k in ('action','before_digest','after_digest'))
            else:atomic_json(path,row)
            rows[arm]=row
            changed=sum(e['changed'] for e in agents[arm].continuation_events)
            triggers=sum(bool(e['trigger']) for e in agents[arm].continuation_events)
            results[arm]=dict(steps=step-a.start+1,score_delta={k:v-initial_scores[k] for k,v in env.scores[AGENT_ID].items()},
                             scores=env.scores[AGENT_ID],changes=changed,triggers=triggers,done=bool(done))
            atomic_json(out/'current.json',results[arm])
            if done:stopped.add(arm)
        if step==a.start:
            assert len({r['before_digest'] for r in rows.values()})==1
            assert len({r['response']['continuation']['original'] for r in rows.values()})==1
            if 'advice' in rows and 'repair' in rows:
                x=rows['advice']['response']['continuation'];y=rows['repair']['response']['continuation']
                assert x.get('packet')==y.get('packet') and x.get('proposal')==y.get('proposal')
        if 'advice' in rows and 'repair' in rows and rows['advice']['before_digest']==rows['repair']['before_digest']:
            comparisons.append(dict(step=step,same_state=True,same_action=rows['advice']['action']==rows['repair']['action']))
        if (step-a.start+1)%10==0:
            atomic_json(a.root/'usage.json',usage_summary(a.root/'api'))
            print(json.dumps(dict(step=step,results=results)),flush=True)
        if len(stopped)==len(a.arms):break
    atomic_json(a.root/'result.json',dict(initial_scores=initial_scores,results=results,
                paired= comparisons, usage=usage_summary(a.root/'api'), protocol=protocol))
    print(json.dumps(results),flush=True)


if __name__=='__main__':main()
