"""Rebuild the parent, preselected checkpoints and one-step native probes."""
import contextlib
import copy
import io
import tempfile
from .common import *
from .replay import Saved
from scar_stage25.integration import make_agent

def main():
    offline()
    from scar.environment import restore,snapshot,state_digest
    from scar.io import digest
    from agents.agc.state import extract
    rr=rows(SOURCE/'trajectory.jsonl.gz');qq=rows(SOURCE/'requests.jsonl.gz');provider=Saved(qq);manifest=[]
    assert not (RESULTS/'freeze.json').exists()
    with tempfile.TemporaryDirectory(prefix='scar26-parent-') as tmp:
        with contextlib.redirect_stdout(io.StringIO()):agent=make_agent('remnant',42,provider,Path(tmp)/'memory')
        env=restore(gzip.decompress((INITIAL/'physical.pkl.gz').read_bytes()),tmp,agent);agent.initialize_official(env.obs[AGENT_ID])
        for r in rr:
            n=r['step'];before=copy.deepcopy(env.obs[AGENT_ID]);provider.begin_step(n)
            assert before==r['observation'] and state_digest(env)==r['state_hash_before'] and agent.short_term_memory==r['memory_before']
            if n in CASES:
                cp=RESULTS/'checkpoints'/case_id(n);cp.mkdir(parents=True,exist_ok=True)
                agent.save_memory(cp);(cp/'physical.pkl.gz').write_bytes(gzip.compress(snapshot(env),mtime=0))
                write(cp/'meta.json',dict(case=case_id(n),start=n,remaining_actions=301-n,state_hash=r['state_hash_before'],
                    observation=before,original_action=r['action'],correction=CASES[n],source_seed=42,parent_episodes=1))
            with contextlib.redirect_stdout(io.StringIO()):action,tin,tout,response=agent.act(before)
            assert action==r['action'] and (tin,tout)==(r['input_tokens'],r['output_tokens']) and digest(agent.decision)==digest(r['decision'])
            if n in CASES:
                write(cp/'post_decision.json',dict(decision=agent.decision,control=agent.control.to_dict(),memory=agent.short_term_memory))
                manifest.append(dict(case=case_id(n),start=n,physical_sha256=sha(cp/'physical.pkl.gz'),
                    memory_sha256={name:sha(cp/name) for name in ['agc_v2.json','memory.json']},state_hash=r['state_hash_before']))
            with contextlib.redirect_stdout(io.StringIO()):obs,reward,done,info=env.step({AGENT_ID:action});env.update_scores(reward)
            assert obs[AGENT_ID]==r['feedback'] and vars(reward[AGENT_ID])==r['reward'] and bool(done)==r['done'] and info==r['info']
            assert state_digest(env)==r['state_hash']
            agent.observe_transition(before,action,obs[AGENT_ID])
            assert digest(agent.control.to_dict())==digest(r['control_after']) and agent.transition==r['transition']
            agent.control.events.clear()
        assert len(provider.calls)==len(qq)==324 and len(manifest)==10
    probes=[]
    for n,case in CASES.items():
        cp=RESULTS/'checkpoints'/case_id(n);raw=gzip.decompress((cp/'physical.pkl.gz').read_bytes())
        with tempfile.TemporaryDirectory(prefix='scar26-probe-') as tmp:
            env=restore(raw,tmp);assert state_digest(env)==rr[n-1]['state_hash_before']
            with contextlib.redirect_stdout(io.StringIO()):obs,reward,done,info=env.step({AGENT_ID:case['action']});env.update_scores(reward)
            feedback=obs[AGENT_ID];accepted=not extract(feedback)['failed'] and not info.get('step_invalid_action',{}).get(AGENT_ID,False)
            alive=vars(reward[AGENT_ID])['death']==0
            probe=dict(case=case_id(n),step=n,original_action=rr[n-1]['action'],oracle_action=case['action'],
                accepted=accepted,no_immediate_death=alive,feedback=feedback,reward=vars(reward[AGENT_ID]),scores=env.scores[AGENT_ID],
                done=bool(done),info=info,state_hash=state_digest(env),public_basis=case['basis'])
            write(cp/'oracle_probe.json',probe);probes.append(probe)
    write(RESULTS/'checkpoint_manifest.json',dict(passed=all(p['accepted'] and p['no_immediate_death'] for p in probes),checkpoints=manifest,
        original_native_actions_verified=300,original_model_contexts_verified=324,new_model_calls=0,independent_parent_episodes=1,
        oracle_candidates_preselected_before_probes=True,probe_actions=len(probes)))
    print(json.dumps([(p['step'],p['oracle_action'],p['accepted'],p['no_immediate_death']) for p in probes]),flush=True)
    assert all(p['accepted'] and p['no_immediate_death'] for p in probes),'Preselected oracle fails validity gate; do not launch.'

if __name__=='__main__':main()
