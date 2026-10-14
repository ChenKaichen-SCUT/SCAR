"""Restore cancelled baseline prefixes without resampling any paid response."""
import contextlib
import io
import tempfile
from scar_stage26.replay import Saved
from .common import *
from .integration import make_agent

def main():
    offline()
    from scar.environment import restore,snapshot,state_digest
    from scar.io import digest
    receipt=[]
    for seed in SEEDS:
        saved=baseline(seed);old_summary=read(saved/'summary.json')
        rr=rows(saved/'trajectory.jsonl.gz');qq=rows(saved/'requests.jsonl.gz')
        if seed==42:
            assert old_summary['status']=='step_limit' and len(rr)==300
            out=RESULTS/'runs'/case_id(seed,'AGC-v2')
            write(out/'summary.json',dict(old_summary,new_requests=0,new_cost_usd=0,reused=True,
                source=str(saved.relative_to(ROOT)),historical_requests=len(qq),historical_cost_usd=old_summary['cost_usd']))
            receipt.append(dict(seed=seed,reuse_complete=True,actions=300,historical_requests=len(qq),new_calls=0));continue
        assert old_summary['steps']==47 and all(q['step']<=47 and q['status']=='ok' for q in qq)
        provider=Saved(qq);cp=RESULTS/'checkpoints'/case_id(seed,'AGC-v2');assert not cp.exists()
        with tempfile.TemporaryDirectory(prefix='scar31-prepare-') as tmp:
            with contextlib.redirect_stdout(io.StringIO()):agent=make_agent(seed,'AGC-v2',provider,Path(tmp)/'memory')
            env=restore(gzip.decompress((initial(seed)/'physical.pkl.gz').read_bytes()),tmp,agent)
            assert state_digest(env)==read(initial(seed)/'initial_public.json')['initial_state_hash']
            agent.initialize_official(env.obs[AGENT_ID])
            for r in rr:
                provider.begin_step(r['step']);assert env.obs[AGENT_ID]==r['observation'] and state_digest(env)==r['state_hash_before']
                assert agent.short_term_memory==r['memory_before']
                with contextlib.redirect_stdout(io.StringIO()):action,ti,to,response=agent.act(r['observation'])
                assert action==r['action'] and digest(agent.decision)==digest(r['decision'])
                with contextlib.redirect_stdout(io.StringIO()):obs,reward,done,info=env.step({AGENT_ID:action});env.update_scores(reward)
                assert state_digest(env)==r['state_hash'] and obs[AGENT_ID]==r['feedback']
                agent.observe_transition(r['observation'],action,obs[AGENT_ID]);assert digest(agent.control.to_dict())==digest(r['control_after']);agent.control.events.clear()
            agent.save_memory(cp);(cp/'physical.pkl.gz').write_bytes(gzip.compress(snapshot(env),mtime=0))
            write(cp/'meta.json',dict(seed=seed,start=48,state_hash=state_digest(env),prefix_actions=len(rr),prefix_requests=len(qq),
                source=str(saved.relative_to(ROOT)),original_cancellation_preserved=True,new_calls=0))
            for name in ['memory.json','agc_v2.json']:assert read(cp/name)==read(saved/'final_memory'/name)
        receipt.append(dict(seed=seed,passed=True,replayed_prefix_actions=len(rr),exact_saved_contexts=len(provider.calls),new_calls=0))
    write(RESULTS/'preparation.json',dict(passed=True,seeds=SEEDS,receipts=receipt,new_model_calls=0,
        new_maximum_actions=3*300+2*(300-47),new_online_jobs=5,complete_baseline_reused=1,partial_baselines_resumed=2))
    print(json.dumps(read(RESULTS/'preparation.json')),flush=True)

if __name__=='__main__':main()
