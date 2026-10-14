"""Replay paid replies and native transitions, without model/network access."""
import argparse
import contextlib
import copy
import io
import tempfile
from .common import *
from .reset import ResetGate,attach


def verify_case(start):
    from scar_stage22b.common import forbid_network
    forbid_network();check_freeze()
    from scar.environment import restore,state_digest
    from scar_stage22.integration import make_agent
    from scar.io import digest
    original=rows(SOURCE/'trajectory.jsonl.gz');original_requests={r['step']:r for r in rows(SOURCE/'requests.jsonl.gz')}
    cp=RESULTS/'checkpoints'/case_id(start);results=[]
    prior_pair={}
    for variant in VARIANTS:
        output=RESULTS/'runs'/case_id(start)/variant;rr=rows(output/'trajectory.jsonl.gz')
        assert len(rr)==301-start or rr[-1]['done']
        if variant=='Stage18-Origin':
            for r in rr:
                old=original[r['step']-1]
                for key in ['action','observation','feedback','reward','scores','state_hash','state_hash_before','main_quest_progress']:
                    assert r[key]==old[key],(start,variant,r['step'],key)
            results.append(dict(variant=variant,original_exact_suffix=len(rr),native_basis='Original full300 replay verified in preparation',passed=True))
            continue
        requests={r['step']:r for r in rows(output/'requests.jsonl.gz')}
        paid=rows(output/'paid_requests.jsonl.gz');assert all(r['status']=='ok' for r in paid)
        paid_ids={r['request_id'] for r in paid};seen_calls=[]
        assert len(requests)==len(rr)
        for r in requests.values():
            assert r['signature']==digest(r['messages'])
            if r['sample_origin']=='Stage22-original':
                q=original_requests[r['step']]
                assert r['messages']==q['messages'] and r['raw_response']==q['raw_response']
                assert r['state_hash_before']==original[r['step']-1]['state_hash_before']
                assert r['incremental_cost_usd']==0
            elif r['sample_origin']=='paired-identical-state-and-input':
                key=(r['step'],r['state_hash_before'],r['signature']);q=prior_pair[key]
                assert r['raw_response']==q['raw_response'] and r['incremental_cost_usd']==0
            else:assert r['sample_origin']=='new-model-request' and r['request_id'] in paid_ids
        class Saved:
            n=0
            def generate(self,user_prompt,system_prompt=None,**kwargs):
                q=requests[self.n]
                assert q['messages']==[dict(role='system',content=system_prompt),dict(role='user',content=user_prompt)],(start,variant,self.n,'prompt')
                seen_calls.append(self.n)
                return dict(response=q['raw_response']['choices'][0]['message']['content'],
                    num_input_tokens=q['usage']['prompt_tokens'],num_output_tokens=q['usage']['completion_tokens'])
        provider=Saved();gate=ResetGate(variant,start,original[:start-1]);checked=0;failure=None
        with tempfile.TemporaryDirectory(prefix='scar23-verify-') as temp:
            with contextlib.redirect_stdout(io.StringIO()):
                agent=make_agent('Stage18-Fixed','mark',provider,Path(temp)/'memory');agent.load_memory(cp)
            env=restore(gzip.decompress((cp/'physical.pkl.gz').read_bytes()),temp,agent);attach(agent,variant)
            for r in rr:
                n=r['step'];before=copy.deepcopy(env.obs[AGENT])
                assert before==r['observation'] and state_digest(env)==r['state_hash_before'],(start,variant,n,'before')
                assert agent.short_term_memory==r['memory_before'] and agent.facts.to_dict()==r['facts_before'],(start,variant,n,'memory')
                reset=gate.before(n,agent.controller,before);assert reset==r['reset'],(start,variant,n,'reset')
                provider.n=n;attach(agent,variant)
                with gate.enabled(),contextlib.redirect_stdout(io.StringIO()):action,tin,tout,response=agent.act(before)
                assert action==r['action'] and response==r['response'] and (tin,tout)==(r['input_tokens'],r['output_tokens'])
                assert digest(agent.decision)==digest(r['decision']),(start,variant,n,'decision')
                with contextlib.redirect_stdout(io.StringIO()):obs,reward,done,info=env.step({AGENT:action});env.update_scores(reward)
                checks=dict(observation=obs[AGENT]==r['feedback'],reward=vars(reward[AGENT])==r['reward'],
                    done=bool(done)==r['done'],state=state_digest(env)==r['state_hash'])
                if not all(checks.values()):failure=dict(step=n,checks=checks);break
                agent.observe_transition(before,action,obs[AGENT]);gate.observe(action,obs[AGENT],r['decision']['controller_before']);checked+=1
            if not failure:
                assert read(output/'final_memory/memory.json')['short_term_memory']==agent.short_term_memory
                final=read(output/'final_memory/stage18.json')
                assert digest(final['controller'])==digest(agent.controller.to_dict())
                assert digest(final['facts'])==digest(agent.facts.to_dict())
        result=dict(variant=variant,steps=len(rr),exact_native_steps=checked,
            exact_model_contexts=len(seen_calls),exact_agent_and_native_all=checked==len(rr),first_native_mismatch=failure,
            new_model_requests=len(paid),api_calls_during_verification=0,passed=failure is None)
        results.append(result)
        for r in requests.values():prior_pair[(r['step'],r['state_hash_before'],r['signature'])]=r
    receipt=dict(case=case_id(start),passed=all(r['passed'] for r in results),variants=results,new_model_calls=0)
    write(RESULTS/'verification'/f'{case_id(start)}.json',receipt)
    print(json.dumps(receipt),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--start',type=int,choices=CASES,required=True)
    verify_case(parser.parse_args().start)
