"""Read-only independent historical prefix verification.

Physical digest is the invariant. Cloudpickle snapshot bytes include temporary
run_dir/config_path, so the one-time frozen materializer is not a byte-stable
reconstruction command. This checker never overwrites published checkpoints.
"""
import contextlib
import gzip
import tempfile
from pathlib import Path
from scar_stage14.common import ROOT,load,episodes
from scar_stage14.replay import verify_freezes


def main():
    from scar.environment import AGENT_ID,restore,state_digest
    from scar.diagnostics.build import transition
    verify_freezes();eps={ep['task_id']:ep for _,_,ep,_,_ in episodes()}
    states={s['state_id']:s for s in load(ROOT/'residual_checkpoint_manifest.json')};checks=[]
    with open('/dev/null','w') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        for j in load(ROOT/'residual_replay_plan.json')['jobs']:
            ep=eps[j['source_task']];raw=gzip.decompress(Path('results/stage11/initial_states',j['case_id']+'.pkl.gz').read_bytes())
            with tempfile.TemporaryDirectory() as tmp:
                env=restore(raw,tmp)
                for r in ep['rows'][:j['source_index']]:
                    assert env.obs[AGENT_ID]==r['observation']
                    assert transition(env,r['executed_action'])['after']==r['next_observation']
                assert env.obs[AGENT_ID]==j['public']['observation']
                assert state_digest(env)==states[j['state_id']]['physical_hash']
                checks.append(j['state_id'])
    print({'passed':True,'independent_public_prefix_and_physical_checks':len(checks),'api_calls':0,'checkpoints_modified':False})

if __name__=='__main__':main()
