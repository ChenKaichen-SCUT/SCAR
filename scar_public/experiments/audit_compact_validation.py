"""No-API exact replay and one-step diagnostics of the independent screen."""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import sys
from scar.environment import AGENT_ID,restore,snapshot,state_digest
from scar.io import atomic_json
from scar_public.continuation import feedback_lines


def audit(block):
    report=dict(arms={},one_step_diagnostics=[],paired_prefix_checks=0)
    shared={};initial_hashes=[]
    for phase in ('main','scheduled'):
        root=block/phase;manifest=json.loads((root/'manifest.json').read_text())
        assert manifest['hash_seed']==os.environ['PYTHONHASHSEED']
        assert (root/'result.json').exists()
        initial=(root/'initial.pkl').read_bytes();initial_hash=hashlib.sha256(initial).hexdigest()
        initial_hashes.append(initial_hash)
        for arm in manifest['arms']:
            state=initial;lineage=initial_hash;n=0
            private=block/'private_audit'/arm;private.mkdir(parents=True,exist_ok=True)
            for path in sorted((root/arm/'trace').glob('*.json')):
                r=json.loads(path.read_text());response=json.loads(r['response'])
                with contextlib.redirect_stdout(sys.stderr):
                    env=restore(state,private);scores=dict(env.scores[AGENT_ID])
                    assert state_digest(env)==r['before_digest']
                    assert env.obs[AGENT_ID]['text']==r['observation']
                    obs,reward,done,_=env.step({AGENT_ID:r['action']});env.update_scores(reward)
                    assert state_digest(env)==r['after_digest']
                    assert obs[AGENT_ID]['text']==r['next_observation']
                    assert env.scores[AGENT_ID]==r['scores'] and bool(done)==r['done']
                    actual=snapshot(env)
                    event=response.get('continuation',{})
                    if event.get('changed'):
                        alt=restore(state,private)
                        ao,ar,ad,_=alt.step({AGENT_ID:event['original']});alt.update_scores(ar)
                        report['one_step_diagnostics'].append(dict(arm=arm,step=r['step'],
                            original=event['original'],executed=r['action'],trigger=event['trigger']['kind'],
                            original_failures=feedback_lines(ao[AGENT_ID]['text']),
                            executed_failures=feedback_lines(r['next_observation']),
                            original_quest_delta=alt.scores[AGENT_ID]['quest']-scores['quest'],
                            executed_quest_delta=r['scores']['quest']-scores['quest'],
                            original_death_delta=alt.scores[AGENT_ID]['death']-scores['death'],
                            executed_death_delta=r['scores']['death']-scores['death']))
                    state=actual
                key=(lineage,r['action']);value=(r['before_digest'],r['after_digest'],r['next_observation'])
                if key in shared:
                    assert value==shared[key];report['paired_prefix_checks']+=1
                else:shared[key]=value
                lineage=hashlib.sha256((lineage+'\0'+r['action']).encode()).hexdigest();n+=1
            report['arms'][arm]=dict(transitions=n,mismatches=0)
    assert len(set(initial_hashes))==1
    report['shared_initial_sha256']=initial_hashes[0]
    report['qualification']='One-step diagnostics do not identify full-trajectory intervention value.'
    atomic_json(block/'environment_audit.json',report)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--block',type=Path,required=True)
    audit(p.parse_args().block)
