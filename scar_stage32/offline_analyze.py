"""Exact offline context replay and descriptive fixed-candidate results."""
import contextlib,io,tempfile
from collections import Counter
from agents.saer.reflection import calibrate
from agents.saer.state import rejected
from agents.agc.state import extract
from scar_stage26.replay import Saved
from scar.agents.scar.repair import valid_syntax
from scar.io import digest
from .common import *
from .integration import make_agent

def main():
    offline();assert read(RESULTS/'offline_completion.json')['complete']
    from scar.environment import restore,state_digest,isolated_copy
    data=[];counts=Counter();allq=[];native_actions=0
    for s in read(RESULTS/'samples.json'):
        folder=RESULTS/'offline'/s['id'];r=read(folder/'result.json');qq=rows(folder/'requests.jsonl.gz');assert r['status']=='complete'
        p=Saved(qq);p.begin_step(s['step']);calls=[]
        def call(phase,user,system):
            result=p.generate(user,system);calls.append(dict(phase=phase,prompt_hash=digest(user),system_hash=digest(system),response=result['response'],input_tokens=result['num_input_tokens'],output_tokens=result['num_output_tokens']));return result
        final,record=calibrate(s['candidate'],s['base_prompt'],s['system_prompt'],s['summary'],call)
        assert record==r['record'] and calls==r['calls'] and len(p.calls)==2
        with tempfile.TemporaryDirectory(prefix='scar32-offline-check-') as tmp:
            with contextlib.redirect_stdout(io.StringIO()):agent=make_agent(s['seed'],p,Path(tmp)/'memory')
            env=restore(gzip.decompress((RESULTS/'checkpoints'/s['checkpoint']/'physical.pkl.gz').read_bytes()),tmp,agent);assert state_digest(env)==s['state_hash']
            for which in ['candidate_native','final_native']:
                value=r[which]
                if value is None:continue
                before=state_digest(env)
                with isolated_copy(env) as clone:
                    with contextlib.redirect_stdout(io.StringIO()):obs,reward,done,info=clone.step({AGENT_ID:value['action']});clone.update_scores(reward)
                    assert obs[AGENT_ID]==value['feedback'] and vars(reward[AGENT_ID])==value['reward'] and state_digest(clone)==value['state_hash'];native_actions+=1
                    if value.get('followup'):
                        f=value['followup']
                        with contextlib.redirect_stdout(io.StringIO()):obs,reward,done,info=clone.step({AGENT_ID:f['action']});clone.update_scores(reward)
                        assert obs[AGENT_ID]==f['feedback'] and state_digest(clone)==f['state_hash'];native_actions+=1
                assert state_digest(env)==before
            proposal=agent.cfg.json_parser(final['response']);assert proposal==r['final_proposal']
        before=r['candidate_native'];after=r['final_native'];warning=record['warning'];same=bool(after and after['action']==before['action'])
        event=dict(id=s['id'],seed=s['seed'],step=s['step'],kind=s['kind'],candidate=before['action'],final_action=after['action'] if after else None,
            warning=warning,risk=(record['prediction'] or {}).get('goal_risk'),changed=r['changed'],candidate_accepted=before['accepted'],final_accepted=bool(after and after['accepted']),
            candidate_visible=extract(before['feedback'])['hands'] is not None,final_visible=bool(after and extract(after['feedback'])['hands'] is not None),
            candidate_followup_accepted=before.get('followup',{}).get('accepted'),final_followup_accepted=after.get('followup',{}).get('accepted') if after else None,
            same_action=same,final_wait=bool(after and after['action']=='wait'),prediction=record['prediction'],source=f'results/stage32/offline/{s["id"]}/result.json')
        counts['samples']+=1;counts['warnings']+=warning;counts['changed']+=r['changed'];counts['warning_changed']+=warning and r['changed'];counts['invalid_final']+=not r['final_syntax_valid'];counts['invalid_prediction']+=record['prediction'] is None
        counts['candidate_accepted']+=before['accepted'];counts['final_accepted']+=bool(after and after['accepted']);counts['final_wait']+=event['final_wait']
        if s['kind']=='rejected':counts['rejected_to_accepted']+=event['final_accepted'];counts['same_rejected_action_retained']+=same
        if s['kind']=='condition_loss':counts['loss_to_visible']+=event['final_visible'];counts['loss_to_accepted_visible']+=event['final_visible'] and event['final_accepted']
        if s['kind']=='terminal':counts['legal_terminal_final_accepted']+=event['final_accepted'];counts['legal_terminal_same_action']+=same
        data.append(event);allq.extend(qq)
    assert len(data)==77 and len(allq)==154
    write(RESULTS/'offline_comparison.json',data)
    write(RESULTS/'offline_summary.json',dict(complete=True,counts=dict(counts),new_requests=len(allq),cost_usd=sum(q['cost_usd'] for q in allq),
        input_tokens=sum(q['usage']['prompt_tokens'] for q in allq),output_tokens=sum(q['usage']['completion_tokens'] for q in allq),
        exact_contexts=154,verified_native_probe_actions=native_actions,new_verification_model_calls=0,independent_parent_episodes=3,strict_causal_reflection_effect=False))
    print(json.dumps(read(RESULTS/'offline_summary.json')),flush=True)

if __name__=='__main__':main()
