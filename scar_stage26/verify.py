"""Network-disabled exact replay of each original-state oracle branch."""
import argparse
import contextlib
import copy
import io
import tempfile
from .common import *
from .replay import Saved
from scar_stage25.integration import make_agent

def main(start):
    offline();integrity=check_freeze()
    from scar.environment import restore,state_digest
    from scar.io import digest
    from agents.agc.agent import DecisionUnavailable
    cp=RESULTS/'checkpoints'/case_id(start);out=RESULTS/'runs'/case_id(start)/'Oracle'
    rr=rows(out/'trajectory.jsonl.gz');qq=rows(out/'requests.jsonl.gz');s=read(out/'summary.json')
    source=[q for q in rows(SOURCE/'requests.jsonl.gz') if q['step']==start]
    assert s['status'] in ['step_limit','native_done','agent_decision_exhausted']
    assert s['steps']==len(rr) and (s['status']!='step_limit' or s['last_step']==300)
    assert [r['step'] for r in rr]==list(range(start,start+len(rr)))
    provider=Saved(source+qq)
    with tempfile.TemporaryDirectory(prefix='scar26-verify-') as tmp:
        with contextlib.redirect_stdout(io.StringIO()):
            agent=make_agent('remnant',42,provider,Path(tmp)/'memory');agent.load_memory(cp)
        env=restore(gzip.decompress((cp/'physical.pkl.gz').read_bytes()),tmp,agent)
        for r in rr:
            n=r['step'];provider.begin_step(n);before=copy.deepcopy(env.obs[AGENT_ID])
            assert before==r['observation'] and state_digest(env)==r['state_hash_before'] and agent.short_term_memory==r['memory_before']
            with contextlib.redirect_stdout(io.StringIO()):proposal,tin,tout,response=agent.act(before)
            assert proposal==r['proposed_action'] and (tin,tout)==(r['input_tokens'],r['output_tokens']) and response==r['response']
            assert digest(agent.decision)==digest(r['decision']) and digest(agent.short_term_memory)==r['memory_after_act_hash']
            assert digest(agent.control.to_dict())==r['goal_after_act_hash']
            action=CASES[start]['action'] if n==start else proposal
            assert action==r['action'] and r['oracle_replacement']==(n==start)
            with contextlib.redirect_stdout(io.StringIO()):obs,reward,done,info=env.step({AGENT_ID:action});env.update_scores(reward)
            assert obs[AGENT_ID]==r['feedback'] and vars(reward[AGENT_ID])==r['reward'] and bool(done)==r['done'] and info==r['info']
            assert state_digest(env)==r['state_hash'],(start,n,'native state')
            agent.observe_transition(before,action,obs[AGENT_ID])
            assert digest(agent.control.to_dict())==digest(r['control_after']) and agent.transition==r['transition']
            agent.control.events.clear()
        exhausted=False
        if s['status']=='agent_decision_exhausted':
            provider.begin_step(env.steps+1)
            try:agent.act(env.obs[AGENT_ID])
            except DecisionUnavailable:exhausted=True
            assert exhausted and agent.decision==read(out/'decision_exhausted.json')['decision']
        assert len(provider.calls)==len(provider.responses)
        assert read(out/'final_memory/agc_v2.json')['control']==agent.control.to_dict()
        assert read(out/'final_memory/memory.json')['short_term_memory']==agent.short_term_memory
        assert read(out/'config.json')['scores'][AGENT_ID]==env.scores[AGENT_ID]==s['scores']
    receipt=dict(case=case_id(start),passed=True,exact_native_steps=len(rr),exact_model_contexts=len(provider.calls),
        original_requests_reused=len(source),new_paid_responses_replayed=sum(q['status']=='ok' for q in qq),
        terminal_rejection_replayed=exhausted,exactly_one_action_replacement=True,memory_and_goal_unedited_at_intervention=True,
        final_memory_exact=True,new_model_calls=0,freeze_integrity=integrity)
    write(RESULTS/'verification'/f'{case_id(start)}.json',receipt);print(json.dumps(receipt))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--start',type=int,choices=CASES,required=True);a=p.parse_args();main(a.start)
