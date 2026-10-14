"""Network-denied exact replay of AGC requests, decisions and native state."""
import argparse
import contextlib
import copy
import io
import tempfile
from .common import *
from .integration import make_agent


def main(game,phase='first_pass'):
    offline();integrity=check_freeze()
    from scar.environment import restore,state_digest
    from scar.io import digest
    from agents.agc.agent import DecisionUnavailable
    from agents.agc.control import Control
    from .repair import original_assess
    normal=Control.assess;strict=original_assess()
    out=(RESULTS/'resumed' if phase=='resumed' else RESULTS)/'runs'/f'{game}__AGC'
    rr=rows(out/'trajectory.jsonl.gz');qq=rows(out/'requests.jsonl.gz');summary=read(out/'summary.json')
    cut=read(RESULTS/'repair_launch'/f'{game}.json')['immutable_prefix_steps'] if phase=='resumed' else 300
    if phase=='resumed':assert rr[:cut]==rows(RESULTS/'runs'/f'{game}__AGC'/'trajectory.jsonl.gz')
    assert summary['status'] in ['step_limit','native_done','agent_decision_exhausted'],summary
    assert len(rr)==summary['steps'] and (summary['status']!='step_limit' or len(rr)==300)
    successful={(q['step'],q['ordinal']):q for q in qq if q['status']=='ok'}
    class Saved:
        def __init__(self):self.calls=[]
        def begin_step(self,n):self.step=n;self.ordinal=0
        def generate(self,user_prompt,system_prompt=None,**kw):
            self.ordinal+=1;q=successful[self.step,self.ordinal]
            assert q['messages']==[dict(role='system',content=system_prompt),dict(role='user',content=user_prompt)],(game,self.step,self.ordinal,'messages')
            self.calls.append((self.step,self.ordinal))
            return dict(response=q['raw_response']['choices'][0]['message']['content'],num_input_tokens=q['usage']['prompt_tokens'],num_output_tokens=q['usage']['completion_tokens'])
    provider=Saved();checked=0
    with tempfile.TemporaryDirectory(prefix='scar24-verify-') as tmp:
        with contextlib.redirect_stdout(io.StringIO()):agent=make_agent(game,provider,Path(tmp)/'memory')
        env=restore(gzip.decompress((RESULTS/'initial'/game/'physical.pkl.gz').read_bytes()),tmp,agent)
        agent.initialize_official(env.obs[AGENT_ID]);assert state_digest(env)==summary['initial_state_hash']
        for r in rr:
            n=r['step'];before=copy.deepcopy(env.obs[AGENT_ID]);provider.begin_step(n)
            Control.assess=strict if n<=cut else normal
            assert before==r['observation'] and state_digest(env)==r['state_hash_before']
            assert agent.short_term_memory==r['memory_before']
            action,tin,tout,response=agent.act(before)
            assert action==r['action'] and (tin,tout)==(r['input_tokens'],r['output_tokens']) and response==r['response']
            assert digest(agent.decision)==digest(r['decision']),(game,n,'decision')
            with contextlib.redirect_stdout(io.StringIO()):obs,reward,done,info=env.step({AGENT_ID:action});env.update_scores(reward)
            assert obs[AGENT_ID]==r['feedback'] and vars(reward[AGENT_ID])==r['reward'] and bool(done)==r['done'],(game,n,'feedback')
            assert state_digest(env)==r['state_hash'],(game,n,'native_hash')
            agent.observe_transition(before,action,obs[AGENT_ID])
            assert digest(agent.control.to_dict())==digest(r['control_after']) and agent.transition==r['transition']
            agent.control.events.clear();checked+=1
        exhausted=False
        if summary['status']=='agent_decision_exhausted':
            provider.begin_step(env.steps+1)
            Control.assess=strict if phase=='first_pass' else normal
            try:agent.act(env.obs[AGENT_ID])
            except DecisionUnavailable:exhausted=True
            assert exhausted and agent.decision==read(out/'decision_exhausted.json')['decision']
        unused=set(successful)-set(provider.calls)
        allowed={(cut+1,2)} if phase=='resumed' else set()
        assert unused==allowed,(game,phase,unused,allowed)
        assert read(out/'final_memory/agc.json')['control']==agent.control.to_dict()
        assert read(out/'final_memory/memory.json')['short_term_memory']==agent.short_term_memory
        config=read(out/'config.json');assert config['scores'][AGENT_ID]==env.scores[AGENT_ID]==summary['scores']
        assert config['step']==len(rr)
    Control.assess=normal
    receipt=dict(game=game,phase=phase,passed=True,exact_native_steps=checked,exact_model_contexts=len(provider.calls),
        immutable_prefix_steps=cut if phase=='resumed' else len(rr),unused_paid_response_keys=sorted(unused),
        exact_decisions=True,terminal_decision_exhaustion_replayed=exhausted,final_memory_exact=True,new_model_calls=0,freeze_integrity=integrity)
    write(RESULTS/'verification'/f'{game}__{phase}.json',receipt);print(json.dumps(receipt))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--game',choices=GAMES,required=True);p.add_argument('--phase',choices=['first_pass','resumed'],default='first_pass')
    args=p.parse_args();main(args.game,args.phase)
