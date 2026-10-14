"""Post-hoc one-state feasibility assay, not an Oracle Goal Stack model replay."""
import contextlib
import gzip
import io
import json
import tempfile
from .common import *
from scar_stage26.replay import Saved
from scar_stage25.integration import make_agent

def main():
    offline()
    from scar.environment import restore,state_digest,isolated_copy
    from scar.io import digest
    from agents.agc.state import extract
    ident='oracle037_a122';s,rr,qq,path,lines=data(ident,'OracleRecovery');cp=ROOT/f'results/stage28/checkpoints/{ident}';meta=read(cp/'meta.json')
    class Replay(Saved):
        def generate(self,user_prompt,system_prompt=None,**kw):
            return super().generate(user_prompt+meta['suffix'] if self.step==meta['start'] else user_prompt,system_prompt,**kw)
    p=Replay(qq);out=[]
    with tempfile.TemporaryDirectory(prefix='scar29-probe-') as tmp:
        with contextlib.redirect_stdout(io.StringIO()):agent=make_agent('remnant',42,p,Path(tmp)/'memory');agent.load_memory(cp)
        env=restore(gzip.decompress((cp/'physical.pkl.gz').read_bytes()),tmp,agent)
        for r in rr:
            if r['step']==147:break
            p.begin_step(r['step']);assert state_digest(env)==r['state_hash_before'] and agent.short_term_memory==r['memory_before']
            with contextlib.redirect_stdout(io.StringIO()):action,_,_,_=agent.act(env.obs[AGENT_ID])
            assert action==r['action'] and digest(agent.decision)==digest(r['decision'])
            with contextlib.redirect_stdout(io.StringIO()):obs,reward,done,info=env.step({AGENT_ID:action});env.update_scores(reward)
            assert state_digest(env)==r['state_hash'];agent.observe_transition(r['observation'],action,r['feedback']);agent.control.events.clear()
        r=next(r for r in rr if r['step']==147);before=state_digest(env);assert before==r['state_hash_before']
        state=extract(env.obs[AGENT_ID]);assert state['hands']=={'torch':1.0} and state['ground']['iron_bar']>=1
        for action in [r['action'],'pick up iron_bar']:
            with isolated_copy(env) as clone:
                with contextlib.redirect_stdout(io.StringIO()):obs,reward,done,info=clone.step({AGENT_ID:action});clone.update_scores(reward)
                out.append(dict(action=action,feedback=obs[AGENT_ID],public_state=extract(obs[AGENT_ID]),state_hash=state_digest(clone),reward=vars(reward[AGENT_ID]),info=info,done=bool(done)))
            assert state_digest(env)==before
        assert out[0]['state_hash']==r['state_hash'] and out[0]['feedback']==r['feedback']
        assert out[1]['public_state']['hands']=={'torch':1.0,'iron_bar':1.0} and not out[1]['public_state']['failed']
    write(RESULTS/'native_local_counterfactual.json',dict(id=ident,step=147,source=path,source_line=lines[147],
        observation=r['observation'],original_reasoning=r['decision']['attempts'][-1]['proposal']['reasoning'],
        current_goal=r['decision']['control_before']['goal'],same_state_hash=before,alternatives=out,
        source_selection='Post-hoc public-state contradiction: original reasoning claims full hands while observation shows only torch; iron_bar is visible and proposal reasoning itself considers picking it up.',
        exact_prefix_actions=24,exact_saved_model_contexts=len(p.calls),native_probe_actions=2,new_model_calls=0,
        inference_limit='Verifies only immediate feasible resource gain, not survival superiority, eventual task success, or the effect of adding a Goal Stack.'))
    print(json.dumps(dict(passed=True,native_actions=26,new_model_calls=0,alternative_holds_torch_and_iron=True)),flush=True)

if __name__=='__main__':main()
