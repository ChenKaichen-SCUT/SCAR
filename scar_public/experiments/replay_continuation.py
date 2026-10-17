"""Exact environment replay plus same-state one-action diagnostic comparisons."""
import argparse
import contextlib
import json
import os
from pathlib import Path
import sys

from scar.environment import AGENT_ID,restore,snapshot,state_digest
from scar.io import atomic_json
from scar_public.continuation import feedback_lines


def main():
    p=argparse.ArgumentParser();p.add_argument('--block',type=Path,required=True);a=p.parse_args()
    manifest=json.loads((a.block/'manifest.json').read_text())
    assert os.environ['PYTHONHASHSEED']==manifest['hash_seed']
    start=(a.block/'fork_environment.pkl').read_bytes()
    result=dict(arms={},same_state_diagnostics=[],qualification='One-step effects do not establish continuation value.')
    for arm in manifest['arms']:
        state=start;count=0
        out=a.block/'private_audit'/arm;out.mkdir(parents=True,exist_ok=True)
        for path in sorted((a.block/arm/'trace').glob('*.json')):
            r=json.loads(path.read_text())
            with contextlib.redirect_stdout(sys.stderr):
                env=restore(state,out);before_scores=dict(env.scores[AGENT_ID])
                assert state_digest(env)==r['before_digest']
                assert env.obs[AGENT_ID]['text']==r['observation']
                obs,reward,done,_=env.step({AGENT_ID:r['action']});env.update_scores(reward)
                assert state_digest(env)==r['after_digest']
                assert obs[AGENT_ID]['text']==r['next_observation']
                assert env.scores[AGENT_ID]==r['scores'] and bool(done)==r['done']
                actual=snapshot(env)
                e=r['response']['continuation']
                if arm=='repair' and e['changed']:
                    alt=restore(state,out)
                    alt_obs,alt_reward,alt_done,_=alt.step({AGENT_ID:e['original']});alt.update_scores(alt_reward)
                    result['same_state_diagnostics'].append(dict(step=r['step'],original=e['original'],
                        executed=r['action'],trigger=e['trigger']['kind'],
                        original_failures=feedback_lines(alt_obs[AGENT_ID]['text']),
                        executed_failures=feedback_lines(r['next_observation']),
                        original_quest_change=alt.scores[AGENT_ID]['quest']-before_scores['quest'],
                        executed_quest_change=r['scores']['quest']-before_scores['quest'],
                        original_death_change=alt.scores[AGENT_ID]['death']-before_scores['death'],
                        executed_death_change=r['scores']['death']-before_scores['death']))
                state=actual;count+=1
        result['arms'][arm]=dict(transitions=count,mismatches=0)
    atomic_json(a.block/'environment_audit.json',result)
    print(json.dumps(dict(block=a.block.name,arms=result['arms'],diagnostics=len(result['same_state_diagnostics']))))


if __name__=='__main__':main()
