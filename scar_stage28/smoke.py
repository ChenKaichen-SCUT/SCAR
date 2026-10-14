import contextlib
import copy
import io
import tempfile
from .common import *
from .provider import ObjectiveProvider
from scar_stage25.integration import make_agent
from scar_stage22.provider import Provider

def main():
    offline()
    from scar.environment import restore,state_digest
    from scar.io import digest
    from agents.agc.state import extract
    receipts=[]
    for ident,s in selected().items():
        source=ROOT/s['source_trajectory'];qq=rows(source.parent/'requests.jsonl.gz')
        responses={(q['step'],q['ordinal']):q for q in qq if q['status']=='ok'};cp=RESULTS/'checkpoints'/ident;meta=read(cp/'meta.json');rr=suffix(s)
        class FakePaid:
            def begin_step(self,n):self.step=n;self.ordinal=0
            def generate(self,user_prompt,system_prompt=None,**kw):
                self.ordinal+=1;q=responses[self.step,self.ordinal]
                expected=q['messages'][1]['content']+(meta['suffix'] if self.step==meta['start'] else '')
                assert system_prompt==q['messages'][0]['content'] and user_prompt==expected
                return Provider.result(q)
        with tempfile.TemporaryDirectory(prefix='scar28-smoke-') as tmp:
            p=ObjectiveProvider.__new__(ObjectiveProvider);p.folder=Path(tmp);p.ident=ident;p.meta=meta;p.paid=FakePaid();p.audit=Path(tmp)/'interventions.jsonl';p.records={}
            with contextlib.redirect_stdout(io.StringIO()):agent=make_agent('remnant',42,p,Path(tmp)/'memory');agent.load_memory(cp)
            env=restore(gzip.decompress((cp/'physical.pkl.gz').read_bytes()),tmp,agent)
            for r in rr[:2]:
                p.begin_step(r['step']);assert state_digest(env)==r['state_hash_before'] and agent.short_term_memory==r['memory_before']
                with contextlib.redirect_stdout(io.StringIO()):action,tin,tout,response=agent.act(env.obs[AGENT_ID])
                assert action==r['action'] and digest(agent.decision)==digest(r['decision'])
                with contextlib.redirect_stdout(io.StringIO()):obs,reward,done,info=env.step({AGENT_ID:action});env.update_scores(reward)
                assert state_digest(env)==r['state_hash'];agent.observe_transition(r['observation'],action,obs[AGENT_ID]);agent.control.events.clear()
            assert {r['step'] for r in p.records.values() if r['injected']}=={meta['start']}
            env=restore(gzip.decompress((cp/'physical.pkl.gz').read_bytes()),tmp)
            with contextlib.redirect_stdout(io.StringIO()):obs,reward,done,info=env.step({AGENT_ID:s['candidate_action']});env.update_scores(reward)
            probe=dict(action=s['candidate_action'],feedback=obs[AGENT_ID],accepted=not extract(obs[AGENT_ID])['failed'],reward=vars(reward[AGENT_ID]))
            assert not probe['accepted'],'Selected trigger must still be blocked at the post-failure checkpoint.'
            write(cp/'initial_retry_probe.json',probe)
        receipts.append(dict(id=ident,passed=True,two_original_actions_reproduced=True,one_injection_decision=True,initial_retry_rejected=True))
    write(RESULTS/'smoke.json',dict(passed=True,cases=receipts,new_model_calls=0,agent_memory_control_untouched=True))
    print(json.dumps(dict(passed=True,cases=len(receipts))),flush=True)

if __name__=='__main__':main()
