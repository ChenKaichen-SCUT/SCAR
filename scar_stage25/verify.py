"""Network-disabled exact native and model-context replay for a frozen case."""
import argparse
import contextlib
import copy
import io
import tempfile
from .common import *
from .integration import make_agent

def main(game,seed):
    offline();integrity=check_freeze()
    from scar.environment import restore,state_digest
    from scar.io import digest
    from agents.agc.agent import DecisionUnavailable
    ident=case_id(game,seed);out=RESULTS/'runs'/ident
    rr=rows(out/'trajectory.jsonl.gz');qq=rows(out/'requests.jsonl.gz');s=read(out/'summary.json')
    assert s['status'] in ['step_limit','native_done','agent_decision_exhausted']
    assert len(rr)==s['steps'] and (s['status']!='step_limit' or len(rr)==300)
    responses={(q['step'],q['ordinal']):q for q in qq if q['status']=='ok'}
    class Saved:
        def __init__(self):self.calls=[]
        def begin_step(self,n):self.step=n;self.ordinal=0
        def generate(self,user_prompt,system_prompt=None,**kw):
            self.ordinal+=1;q=responses[self.step,self.ordinal]
            assert q['messages']==[dict(role='system',content=system_prompt),dict(role='user',content=user_prompt)],(ident,self.step,self.ordinal,'model_context')
            self.calls.append((self.step,self.ordinal))
            return dict(response=q['raw_response']['choices'][0]['message']['content'],num_input_tokens=q['usage']['prompt_tokens'],num_output_tokens=q['usage']['completion_tokens'])
    provider=Saved()
    with tempfile.TemporaryDirectory(prefix='scar25-verify-') as tmp:
        with contextlib.redirect_stdout(io.StringIO()):agent=make_agent(game,seed,provider,Path(tmp)/'memory')
        env=restore(gzip.decompress((RESULTS/'initial'/ident/'physical.pkl.gz').read_bytes()),tmp,agent)
        agent.initialize_official(env.obs[AGENT_ID]);assert state_digest(env)==s['initial_state_hash']
        for r in rr:
            n=r['step'];before=copy.deepcopy(env.obs[AGENT_ID]);provider.begin_step(n)
            assert before==r['observation'] and state_digest(env)==r['state_hash_before']
            assert agent.short_term_memory==r['memory_before']
            action,tin,tout,response=agent.act(before)
            assert action==r['action'] and (tin,tout)==(r['input_tokens'],r['output_tokens']) and response==r['response']
            assert digest(agent.decision)==digest(r['decision']),(ident,n,'decision')
            with contextlib.redirect_stdout(io.StringIO()):obs,reward,done,info=env.step({AGENT_ID:action});env.update_scores(reward)
            assert obs[AGENT_ID]==r['feedback'] and vars(reward[AGENT_ID])==r['reward'] and bool(done)==r['done'] and info==r['info'],(ident,n,'feedback')
            assert state_digest(env)==r['state_hash'],(ident,n,'native_hash')
            agent.observe_transition(before,action,obs[AGENT_ID])
            assert digest(agent.control.to_dict())==digest(r['control_after']) and agent.transition==r['transition'],(ident,n,'control')
            agent.control.events.clear()
        exhausted=False
        if s['status']=='agent_decision_exhausted':
            provider.begin_step(env.steps+1)
            try:agent.act(env.obs[AGENT_ID])
            except DecisionUnavailable:exhausted=True
            assert exhausted and agent.decision==read(out/'decision_exhausted.json')['decision']
        assert len(provider.calls)==len(responses)
        assert read(out/'final_memory/agc_v2.json')['control']==agent.control.to_dict()
        assert read(out/'final_memory/memory.json')['short_term_memory']==agent.short_term_memory
        assert read(out/'config.json')['scores'][AGENT_ID]==env.scores[AGENT_ID]==s['scores']
    receipt=dict(case=ident,passed=True,exact_native_steps=len(rr),exact_model_contexts=len(provider.calls),
        terminal_rejection_replayed=exhausted,exact_decisions=True,final_memory_exact=True,new_model_calls=0,freeze_integrity=integrity)
    write(RESULTS/'verification'/f'{ident}.json',receipt);print(json.dumps(receipt))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--game',choices=GAMES,required=True);p.add_argument('--seed',type=int,choices=SEEDS,required=True)
    args=p.parse_args();main(args.game,args.seed)
