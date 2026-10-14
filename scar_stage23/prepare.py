"""Rebuild ten exact original checkpoints, without any new model calls."""
import contextlib
import copy
import io
import tempfile
from .common import *


def load_agent_state(agent,state):
    from scar_stage18_fixed.agent import Controller18Fixed
    from scar_stage16.knowledge import PublicFacts16
    agent.controller=Controller18Fixed.from_dict(state['controller'])
    agent.facts=PublicFacts16.from_dict(state['facts'])
    agent.short_term_memory=copy.deepcopy(state['memory'])
    agent.events=[]


def main():
    from scar_stage22b.common import forbid_network
    forbid_network()
    from scar_stage22b.native import create_actual
    from scar.environment import snapshot,state_digest,restore
    from scar_stage22.integration import make_agent
    from scar.io import digest
    from scar_stage22b.common import internal
    original=rows(SOURCE/'trajectory.jsonl.gz')
    states=rows(ROOT/'results/stage22b/agent_audit/Stage18-Fixed.jsonl.gz')
    requests=rows(SOURCE/'requests.jsonl.gz')
    class Saved:
        n=0
        def generate(self,user_prompt,system_prompt=None,**kwargs):
            q=requests[self.n-1]
            assert q['messages']==[dict(role='system',content=system_prompt),dict(role='user',content=user_prompt)]
            return dict(response=q['raw_response']['choices'][0]['message']['content'],
                num_input_tokens=q['usage']['prompt_tokens'],num_output_tokens=q['usage']['completion_tokens'])
    manifest=[]
    with tempfile.TemporaryDirectory(prefix='scar23-checkpoints-') as temp:
        env=create_actual('Stage18-Fixed',temp)
        for r in original:
            n=r['step'];assert state_digest(env)==r['state_hash_before']
            if n in CASES:
                p=RESULTS/'checkpoints'/case_id(n);p.mkdir(parents=True,exist_ok=True)
                raw=snapshot(env)
                assert state_digest(restore(raw,set_rng=False))==r['state_hash_before']
                with gzip.open(p/'physical.pkl.gz','wb') as f:f.write(raw)
                provider=Saved();provider.n=n
                with contextlib.redirect_stdout(io.StringIO()):agent=make_agent('Stage18-Fixed','mark',provider,Path(temp)/'memory')
                load_agent_state(agent,states[n-1]['internal_before'])
                assert internal(agent,'Stage18-Fixed')==states[n-1]['internal_before']
                agent.save_memory(p)
                with contextlib.redirect_stdout(io.StringIO()):action,*_=agent.act(r['observation'])
                assert action==r['action'] and digest(agent.decision)==digest(r['decision'])
                write(p/'meta.json',dict(case=case_id(n),start_before_action=n,remaining_actions=301-n,
                    state_hash=r['state_hash_before'],original_evidence_id=states[n-1]['evidence_id'],
                    source_trajectory='results/stage22/runs/mark__Stage18-Fixed/trajectory.jsonl.gz',
                    source_requests='results/stage22/runs/mark__Stage18-Fixed/requests.jsonl.gz',
                    first_context_and_action_exact=True,source_seed=42,independent_parent_episodes=1))
                manifest.append(dict(case=case_id(n),start=n,physical_sha256=sha(p/'physical.pkl.gz'),
                    memory_sha256={s:sha(p/s) for s in ('memory.json','stage18.json')},state_hash=r['state_hash_before']))
                print('Exact original checkpoint',n,flush=True)
            with contextlib.redirect_stdout(io.StringIO()):
                obs,reward,done,info=env.step({AGENT:r['action']});env.update_scores(reward)
            assert obs[AGENT]==r['feedback'] and vars(reward[AGENT])==r['reward']
            assert state_digest(env)==r['state_hash'] and bool(done)==r['done'],('native mismatch',n)
    assert len(manifest)==10
    write(RESULTS/'checkpoint_manifest.json',dict(checkpoints=manifest,original_native_actions_verified=300,
        api_calls=0,independent_parent_episodes=1,seed=42,pythonhashseed='0 for Stage23 preparation and all continuations'))


if __name__=='__main__':main()
