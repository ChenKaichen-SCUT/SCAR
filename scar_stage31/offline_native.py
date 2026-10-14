"""Validate shadow flags with unchanged saved-response replay and local probes."""
import contextlib
import io
import tempfile
from agents.rec_v1.state import visible
from scar_stage26.replay import Saved
from scar_stage25.integration import make_agent
from .offline import sources
from .common import *

def main():
    offline()
    from scar.environment import restore,state_digest,isolated_copy
    from scar.io import digest
    flags={(x['id'],x['variant'],x['step']):x for x in rows(RESULTS/'offline_action_audit.jsonl.gz') if x['assessment']['decision']=='RECONSIDER'}
    probes=[];receipts=[]
    for ident,variant,path in sources():
        cp=ROOT/f'results/stage28/checkpoints/{ident}';meta=read(cp/'meta.json')
        addition=meta['suffix'] if variant=='OriginalRecovery' else read(ROOT/f'results/stage30/checkpoints/{ident}/meta.json')['suffix']
        rr=rows(path);qq=rows(path.parent/'requests.jsonl.gz')
        class Replay(Saved):
            def generate(self,user_prompt,system_prompt=None,**kw):
                if self.step==meta['start']:user_prompt+=addition
                return super().generate(user_prompt,system_prompt,**kw)
        p=Replay(qq)
        with tempfile.TemporaryDirectory(prefix='scar31-offline-') as tmp:
            with contextlib.redirect_stdout(io.StringIO()):agent=make_agent('remnant',42,p,Path(tmp)/'memory');agent.load_memory(cp)
            env=restore(gzip.decompress((cp/'physical.pkl.gz').read_bytes()),tmp,agent)
            def probe(step,action,phase):
                original=state_digest(env)
                with isolated_copy(env) as clone:
                    with contextlib.redirect_stdout(io.StringIO()):obs,reward,done,info=clone.step({AGENT_ID:action});clone.update_scores(reward)
                    probes.append(dict(id=ident,variant=variant,step=step,action=action,phase=phase,source_state_hash=original,
                        feedback=obs[AGENT_ID],craft_success='I successfully crafted ' in obs[AGENT_ID]['text'],visible=visible(obs[AGENT_ID]),
                        reward=vars(reward[AGENT_ID]),done=bool(done),info=info,state_hash=state_digest(clone),model_calls=0))
                assert state_digest(env)==original
            for r in rr:
                assert state_digest(env)==r['state_hash_before'] and env.obs[AGENT_ID]==r['observation']
                flag=flags.get((ident,variant,r['step']));resource_action=None
                if flag:
                    kinds={x['kind'] for x in flag['assessment']['reasons']};req=flag['assessment']['requirements']
                    if kinds & {'required_resource_custody_risk','facility_departure_risk'}:
                        resource_action=f"craft {req['amount']:g} {req['target']}";probe(r['step'],resource_action,'before_flagged_action')
                    if 'observed_condition_loss_risk' in kinds:probe(r['step'],'wait','alternative_same_state')
                p.begin_step(r['step'])
                with contextlib.redirect_stdout(io.StringIO()):action,ti,to,response=agent.act(r['observation'])
                assert action==r['action'] and digest(agent.decision)==digest(r['decision'])
                with contextlib.redirect_stdout(io.StringIO()):obs,reward,done,info=env.step({AGENT_ID:action});env.update_scores(reward)
                assert state_digest(env)==r['state_hash'] and obs[AGENT_ID]==r['feedback'] and vars(reward[AGENT_ID])==r['reward']
                agent.observe_transition(r['observation'],action,obs[AGENT_ID]);assert digest(agent.control.to_dict())==digest(r['control_after']);agent.control.events.clear()
                if resource_action:probe(r['step'],resource_action,'after_flagged_action')
        receipts.append(dict(id=ident,variant=variant,passed=True,actions=len(rr),model_contexts=len(p.calls)))
        print(json.dumps(receipts[-1]),flush=True)
    gzwrite(RESULTS/'offline_native_probes.jsonl.gz',probes)
    out=[]
    for key,flag in flags.items():
        pp=[p for p in probes if (p['id'],p['variant'],p['step'])==key]
        before=next((p for p in pp if p['phase']=='before_flagged_action'),None);after=next((p for p in pp if p['phase']=='after_flagged_action'),None)
        alt=next((p for p in pp if p['phase']=='alternative_same_state'),None)
        verdict=('immediate_craft_feasibility_lost' if before['craft_success'] and not after['craft_success'] else
                 'immediate_craft_feasibility_preserved' if before['craft_success'] and after['craft_success'] else
                 'craft_already_infeasible_no_harm_isolated') if before else None
        out.append(dict(id=key[0],variant=key[1],step=key[2],kinds=[x['kind'] for x in flag['assessment']['reasons']],
            resource_or_facility_verdict=verdict,visibility_action_effect_confirmed=bool(alt and alt['visible'] and flag['observed_outcome']['visibility_lost']),
            alternative_wait_death_reward=alt['reward']['death'] if alt else None,probes=pp))
    write(RESULTS/'offline_native_validation.json',dict(passed=True,receipts=receipts,actions=sum(x['actions'] for x in receipts),
        exact_contexts=sum(x['model_contexts'] for x in receipts),isolated_probe_actions=len(probes),cases=out,new_model_calls=0))
    print(json.dumps(dict(passed=True,probes=len(probes))),flush=True)

if __name__=='__main__':main()
