"""One-action native checks of final hard rejections, without model calls."""
import contextlib
import io
import tempfile
from .common import *
from .analyze import final_folder


def main():
    offline();check_freeze()
    from scar.environment import restore,state_digest
    output=[]
    for game in GAMES:
        folder=final_folder(game);p=folder/'decision_exhausted.json'
        if not p.exists():continue
        terminal=read(p);rr=rows(folder/'trajectory.jsonl.gz')
        with tempfile.TemporaryDirectory(prefix='scar24-terminal-') as tmp:
            env=restore(gzip.decompress((RESULTS/'initial'/game/'physical.pkl.gz').read_bytes()),tmp)
            with contextlib.redirect_stdout(io.StringIO()):
                for r in rr:
                    obs,reward,done,info=env.step({AGENT_ID:r['action']});env.update_scores(reward)
                    assert state_digest(env)==r['state_hash']
            assert env.obs[AGENT_ID]==terminal['observation']
            before=state_digest(env);proposal=terminal['decision']['attempts'][0]['proposal']
            with contextlib.redirect_stdout(io.StringIO()):obs,reward,done,info=env.step({AGENT_ID:proposal['action']});env.update_scores(reward)
            output.append(dict(game=game,decision=terminal['step'],proposal=proposal,
                same_state_hash=before,feedback=obs[AGENT_ID],reward=vars(reward[AGENT_ID]),info=info,
                scope='Offline one-action audit only, excluded from formal action and reward totals.',new_model_calls=0))
    write(RESULTS/'terminal_native_audit.json',output);print(json.dumps([dict(game=x['game'],decision=x['decision'],info=x['info']) for x in output]))

if __name__=='__main__':main()
