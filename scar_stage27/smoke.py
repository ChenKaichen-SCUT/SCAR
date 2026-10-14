"""No model calls: all saved post-failure states must reproduce the next action."""
import contextlib
import gzip
import io
import tempfile
from .common import *
from .fixtures import make_messages,provenance_check

def main():
    offline()
    from scar.environment import restore,state_digest
    from scar.io import digest
    from scar.agents.scar.repair import valid_syntax
    sources={};verified=0;terminal=0
    for s in samples():
        for condition,h in s['input_hashes'].items():assert digest(make_messages(s,condition))==h
        if not s['action_test_eligible']:continue
        cp=RESULTS/'checkpoints'/s['id'];prefix=read_prefix(cp)
        provenance_check(s['grounded_state'],prefix)
        src=s['source_trajectory']
        if src not in sources:sources[src]={r['step']:r for r in rows(ROOT/src)}
        with tempfile.TemporaryDirectory(prefix='scar27-smoke-') as tmp:
            env=restore(gzip.decompress((cp/'physical.pkl.gz').read_bytes()),tmp)
            assert state_digest(env)==s['post_state_hash']
            if s['step']+1 in sources[src]:
                r=sources[src][s['step']+1]
                assert valid_syntax(r['action'],env.agents[0].available_actions)
                with contextlib.redirect_stdout(io.StringIO()):obs,reward,done,info=env.step({AGENT_ID:r['action']});env.update_scores(reward)
                assert state_digest(env)==r['state_hash'] and obs[AGENT_ID]==r['feedback']
                verified+=1
            else:terminal+=1
    assert verified+terminal==334
    write(RESULTS/'smoke.json',dict(passed=True,post_failure_states=334,exact_next_native_actions=verified,
        no_next_executed_action=terminal,input_hashes_checked=True,public_provenance_checked=True,new_model_calls=0))

def read_prefix(cp):
    import json
    return json.loads(gzip.decompress((cp/'public_prefix.json.gz').read_bytes()))

if __name__=='__main__':main()
