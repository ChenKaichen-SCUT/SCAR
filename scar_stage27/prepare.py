"""Exhaustive failure census and exact native post-rejection snapshots, zero API."""
import contextlib
import copy
import gzip
import io
import json
import tempfile
from collections import Counter
from .common import *
from .fixtures import compile_state,provenance_check,failure_type,public_failure_line,make_messages
from scar_stage26.replay import Saved
from scar_stage26.common import CASES
from scar_stage25.integration import make_agent

def main():
    offline()
    from scar.environment import restore,snapshot,state_digest
    from scar.io import digest
    from agents.agc.state import extract
    parent=rows(PARENT/'trajectory.jsonl.gz');parentq=rows(PARENT/'requests.jsonl.gz')
    datasets=[('parent',parent,parentq,None)]
    for n in CASES:
        path=ROOT/f'results/stage26/runs/remnant_a{n:03d}/Oracle'
        datasets.append((f'oracle{n:03d}',rows(path/'trajectory.jsonl.gz'),
            [q for q in parentq if q['step']==n]+rows(path/'requests.jsonl.gz'),n))
    database=[];receipts=[];rejected=[]
    for name,rr,qq,start in datasets:
        provider=Saved(qq);qmap={(q['step'],q['ordinal']):q for q in qq if q['status']=='ok'}
        prefix=copy.deepcopy(parent[:start-1]) if start else []
        path=PARENT if not start else ROOT/f'results/stage26/runs/remnant_a{start:03d}/Oracle'
        with tempfile.TemporaryDirectory(prefix='scar27-prepare-') as tmp:
            with contextlib.redirect_stdout(io.StringIO()):agent=make_agent('remnant',42,provider,Path(tmp)/'memory')
            if start:
                cp=ROOT/f'results/stage26/checkpoints/remnant_a{start:03d}'
                with contextlib.redirect_stdout(io.StringIO()):agent.load_memory(cp)
                env=restore(gzip.decompress((cp/'physical.pkl.gz').read_bytes()),tmp,agent)
            else:
                initial=ROOT/'results/stage25/initial/remnant__s42__AGC-v2/physical.pkl.gz'
                env=restore(gzip.decompress(initial.read_bytes()),tmp,agent);agent.initialize_official(env.obs[AGENT_ID])
            for index,r in enumerate(rr,1):
                n=r['step'];provider.begin_step(n)
                assert env.obs[AGENT_ID]==r['observation'] and state_digest(env)==r['state_hash_before']
                assert agent.short_term_memory==r['memory_before']
                with contextlib.redirect_stdout(io.StringIO()):action,tin,tout,response=agent.act(r['observation'])
                assert action==r.get('proposed_action',r['action']) and digest(agent.decision)==digest(r['decision'])
                with contextlib.redirect_stdout(io.StringIO()):obs,reward,done,info=env.step({AGENT_ID:r['action']});env.update_scores(reward)
                assert obs[AGENT_ID]==r['feedback'] and vars(reward[AGENT_ID])==r['reward']
                assert state_digest(env)==r['state_hash']
                agent.observe_transition(r['observation'],r['action'],r['feedback'])
                assert digest(agent.control.to_dict())==digest(r['control_after'])
                agent.control.events.clear();prefix.append(r)
                for p in r['decision']['attempts']:
                    if p['hard']:rejected.append(dict(trajectory=name,step=n,proposal=p['proposal'],reasons=p['reasons']))
                if not extract(r['feedback'])['failed']:continue
                ident=f'{name}_a{n:03d}';state=compile_state(prefix);provenance_check(state,prefix)
                entry=dict(id=ident,trajectory=name,step=n,independent_parent_episodes=1,
                    current_goal=r['decision']['attempts'][-1]['proposal']['goal_description'],
                    observation=r['observation'],inventory=extract(r['observation'])['hands'],location=extract(r['observation'])['location'],
                    previous_actions=[dict(step=p['step'],action=p['action'],feedback=public_failure_line(p['feedback'])) for p in prefix[-6:-1]],
                    candidate_action=r['action'],environment_response=extract(r['feedback'])['feedback'],
                    failure_reason=public_failure_line(r['feedback']),failure_type=failure_type(extract(r['feedback'])['feedback']),
                    post_failure_observation=r['feedback'],grounded_state=state,
                    original_messages=qmap[n+1,1]['messages'] if (n+1,1) in qmap else None,
                    historical_next_response=qmap[n+1,1]['raw_response']['choices'][0]['message']['content'] if (n+1,1) in qmap else None,
                    action_test_eligible=n<300 and (n+1,1) in qmap,
                    recovery_horizon=3 if name=='parent' else 1,
                    source_trajectory=str((path/'trajectory.jsonl.gz').relative_to(ROOT)),source_line=index,
                    post_state_hash=r['state_hash'],public_context=extract(r['feedback'])['context'])
                if entry['action_test_eligible']:
                    cp=RESULTS/'checkpoints'/ident;cp.mkdir(parents=True,exist_ok=True)
                    (cp/'physical.pkl.gz').write_bytes(gzip.compress(snapshot(env),mtime=0))
                    write(cp/'public_prefix.json',[dict(step=p['step'],action=p['action'],observation=p['observation'],feedback=p['feedback']) for p in prefix])
                    # Prefix is public-only and compressed to avoid redundant storage.
                    raw=(cp/'public_prefix.json').read_bytes();(cp/'public_prefix.json.gz').write_bytes(gzip.compress(raw,mtime=0));(cp/'public_prefix.json').unlink()
                    entry['checkpoint_sha256']=sha(cp/'physical.pkl.gz')
                for condition in ['understanding','A','B'] if entry['action_test_eligible'] else ['understanding']:
                    entry.setdefault('input_hashes',{})[condition]=digest(make_messages(entry,condition))
                database.append(entry)
            receipts.append(dict(trajectory=name,exact_native_steps=len(rr),exact_model_contexts=len(provider.calls)))
        print(json.dumps(receipts[-1]),flush=True)
    assert len(database)==336 and sum(s['action_test_eligible'] for s in database)==334
    gzwrite(RESULTS/'failure_database.jsonl.gz',database)
    write(RESULTS/'preparation.json',dict(passed=True,native_replay=receipts,failures=len(database),
        subtype_counts=dict(Counter(s['failure_type'] for s in database)),action_pairs=334,understanding_queries=336,
        max_new_queries=1140,independent_parent_episodes=1,new_model_calls=0,provenance_checked=True))
    write(RESULTS/'filtered_proposals.json',rejected)

if __name__=='__main__':main()
