"""Reconstruct each saved agent state from paid responses, never resample."""
import argparse
import contextlib
import copy
import io
import json
import tempfile
from .common import *


def execute(method):
    forbid_network();check_freeze()
    from scar_stage22.integration import make_agent
    from scar.io import digest
    d=source(method);trajectory=rows(d/'trajectory.jsonl.gz');requests=rows(d/'requests.jsonl.gz')
    by_step={q['step']:q for q in requests}
    assert len(by_step)==len(requests)==300
    class Saved:
        step=0
        seen=0
        def generate(self,user_prompt,system_prompt=None,**kwargs):
            q=by_step[self.step]
            assert q['phase']=='action' and q['status']=='ok'
            assert q['messages']==[dict(role='system',content=system_prompt),dict(role='user',content=user_prompt)],(method,self.step,'context')
            self.seen+=1
            return dict(response=q['raw_response']['choices'][0]['message']['content'],num_input_tokens=q['usage']['prompt_tokens'],num_output_tokens=q['usage']['completion_tokens'])
    audit=[];history=[];providers=Saved()
    with tempfile.TemporaryDirectory(prefix='scar22b-agent-') as tmp:
        with contextlib.redirect_stdout(io.StringIO()):agent=make_agent(method,'mark',providers,Path(tmp)/'memory')
        if method=='Stage18-Fixed':agent.initialize_official(read(d/'initial_public.json')['observation'])
        for r in trajectory:
            q=by_step[r['step']];providers.step=r['step']
            before=internal(agent,method)
            assert r['observation']==(trajectory[r['step']-2]['feedback'] if r['step']>1 else read(d/'initial_public.json')['observation'])
            with contextlib.redirect_stdout(io.StringIO()):
                action,tin,tout,response=agent.act(r['observation'])
            assert action==r['action'] and response==r['response'],(method,r['step'],'action')
            assert (tin,tout)==(r['agent_return_input_tokens'],r['agent_return_output_tokens'])
            if method=='Stage18-Fixed':assert digest(agent.decision)==digest(r['decision']),(method,r['step'],'decision')
            if hasattr(agent,'observe_transition'):agent.observe_transition(r['observation'],action,r['feedback'])
            after=internal(agent,method)
            audit.append(dict(method=method,step=r['step'],evidence_id=f'mark__{method}:a{r["step"]:03d}',
                observation=r['observation'],internal_before=before,internal_after=after,history_actions=list(history),
                selected_action=action,feedback=r['feedback'],reward=r['reward'],scores=r['scores'],
                main_quest_progress=r['main_quest_progress'],decision=r['decision'],
                model_request_id=q['request_id'],model_messages=q['messages'],model_parsed=q.get('parsed_json'),
                model_usage=q['usage'],original_state_hash_before=r['state_hash_before'],original_state_hash_after=r['state_hash'],
                note='Internal state reconstructed from exact saved responses and exact message/action checks; unlogged LLM latent states are unavailable.'))
            history.append(action)
        if method=='LongContextAgent':
            saved=gzip.decompress((d/'final_memory/content.txt.gz').read_bytes()).decode()
            assert saved==agent.memory.get_all_memory()
        else:
            saved=json.loads(gzip.decompress((d/'final_memory/memory.json.gz').read_bytes()))
            assert saved['short_term_memory']==agent.short_term_memory
            if method=='Stage18-Fixed':
                final=json.loads(gzip.decompress((d/'final_memory/stage18.json.gz').read_bytes()))
                assert digest(final['controller'])==digest(agent.controller.to_dict())
                assert digest(final['facts'])==digest(agent.facts.to_dict())
        # Persistence interface round-trip uses the exact frozen save/load code.
        agent.save_memory(tmp)
        with contextlib.redirect_stdout(io.StringIO()):
            clone=make_agent(method,'mark',providers,Path(tmp)/'other');clone.load_memory(tmp)
        assert digest(internal(clone,method))==digest(internal(agent,method)),(method,'round-trip')
    gzwrite(RESULTS/'agent_audit'/f'{method}.jsonl.gz',audit)
    receipt=dict(method=method,steps=len(audit),exact_contexts=providers.seen,exact_actions=300,
        exact_saved_final_memory=True,save_load_roundtrip_exact=True,api_calls=0,network_denied=True,
        input_sha256={n:sha(d/n) for n in ('trajectory.jsonl.gz','requests.jsonl.gz')})
    write(RESULTS/'agent_audit'/f'{method}.receipt.json',receipt)
    print(json.dumps(receipt),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--method',choices=METHODS,required=True);execute(p.parse_args().method)
