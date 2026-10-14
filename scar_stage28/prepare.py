"""Reconstruct exact agent memory/control and physical state after each failure."""
import contextlib
import copy
import io
import tempfile
from .common import *
from scar_stage26.replay import Saved
from scar_stage25.integration import make_agent

def main():
    offline()
    from scar.environment import restore,snapshot,state_digest
    from scar.io import digest
    ss=selected();parent=rows(PARENT/'trajectory.jsonl.gz');pq=rows(PARENT/'requests.jsonl.gz');receipts=[];checkpoints=[]
    for name in sorted({s['trajectory'] for s in ss.values()}):
        targets={s['step']:s for s in ss.values() if s['trajectory']==name}
        start=int(name[6:]) if name.startswith('oracle') else None
        source=PARENT if start is None else ROOT/f'results/stage26/runs/remnant_a{start:03d}/Oracle'
        rr=rows(source/'trajectory.jsonl.gz');qq=rows(source/'requests.jsonl.gz')
        if start:qq=[q for q in pq if q['step']==start]+qq
        provider=Saved(qq)
        with tempfile.TemporaryDirectory(prefix='scar28-prepare-') as tmp:
            with contextlib.redirect_stdout(io.StringIO()):agent=make_agent('remnant',42,provider,Path(tmp)/'memory')
            initial=ROOT/f'results/stage26/checkpoints/remnant_a{start:03d}' if start else ROOT/'results/stage25/initial/remnant__s42__AGC-v2'
            if start:
                with contextlib.redirect_stdout(io.StringIO()):agent.load_memory(initial)
            env=restore(gzip.decompress((initial/'physical.pkl.gz').read_bytes()),tmp,agent)
            if not start:agent.initialize_official(env.obs[AGENT_ID])
            for r in rr:
                n=r['step'];provider.begin_step(n)
                assert env.obs[AGENT_ID]==r['observation'] and state_digest(env)==r['state_hash_before']
                assert agent.short_term_memory==r['memory_before']
                with contextlib.redirect_stdout(io.StringIO()):action,tin,tout,response=agent.act(r['observation'])
                assert action==r.get('proposed_action',r['action']) and digest(agent.decision)==digest(r['decision'])
                with contextlib.redirect_stdout(io.StringIO()):obs,reward,done,info=env.step({AGENT_ID:r['action']});env.update_scores(reward)
                assert state_digest(env)==r['state_hash'] and obs[AGENT_ID]==r['feedback']
                agent.observe_transition(r['observation'],r['action'],r['feedback'])
                assert digest(agent.control.to_dict())==digest(r['control_after']);agent.control.events.clear()
                if n not in targets:continue
                s=targets[n];ident=s['id'];cp=RESULTS/'checkpoints'/ident;cp.mkdir(parents=True,exist_ok=True)
                agent.save_memory(cp);(cp/'physical.pkl.gz').write_bytes(gzip.compress(snapshot(env),mtime=0))
                assert state_digest(env)==s['post_state_hash']
                write(cp/'meta.json',dict(id=ident,failure_step=n,start=n+1,remaining=300-n,original_goal=s['current_goal'],
                    original_action=s['candidate_action'],public_failure=s['failure_reason'],state_hash=state_digest(env),
                    objective=CASES[ident],suffix=intervention(ident,s['current_goal']),source_trajectory=s['source_trajectory'],
                    original_first_messages=s['original_messages'],original_first_messages_hash=digest(s['original_messages'])))
                checkpoints.append(dict(id=ident,step=n,remaining=300-n,physical_sha256=sha(cp/'physical.pkl.gz'),
                    memory_sha256={name:sha(cp/name) for name in ['memory.json','agc_v2.json']},state_hash=s['post_state_hash']))
                orig=suffix(s);write(RESULTS/'runs'/ident/'Original'/'summary.json',dict(id=ident,variant='Original',status='reused_original_suffix',
                    source_trajectory=s['source_trajectory'],first_step=n+1,last_step=orig[-1]['step'],steps=len(orig),
                    scores=orig[-1]['scores'],main_quest_progress=orig[-1]['main_quest_progress'],new_requests=0,cost_usd=0))
            receipts.append(dict(trajectory=name,exact_native_actions=len(rr),exact_model_contexts=len(provider.calls)))
        print(json.dumps(receipts[-1]),flush=True)
    assert len(checkpoints)==10 and all(c['remaining']>=20 for c in checkpoints)
    write(RESULTS/'checkpoint_manifest.json',dict(passed=True,checkpoints=checkpoints,replay_receipts=receipts,
        total_remaining_actions=sum(c['remaining'] for c in checkpoints),independent_parent_episodes=1,new_model_calls=0))

if __name__=='__main__':main()
