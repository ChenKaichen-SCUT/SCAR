"""Native terminal alternatives, including proposals passed to AGC confidence review."""
import contextlib
import copy
import io
import tempfile
from agents.rec_v1.state import failed,visible
from scar.agents.scar.repair import valid_syntax
from scar_stage26.replay import Saved
from .common import *
from .integration import make_agent
from .metrics import source

def main():
    offline()
    from scar.environment import restore,state_digest,isolated_copy
    out=[];replayed=0;probed=0
    for seed in SEEDS:
        folder=source(seed,'REC');terminal=folder/'decision_exhausted.json'
        if not terminal.exists():continue
        rr=rows(folder/'trajectory.jsonl.gz');stop=read(terminal)
        with tempfile.TemporaryDirectory(prefix='scar31-terminal-') as tmp:
            with contextlib.redirect_stdout(io.StringIO()):agent=make_agent(seed,'REC',Saved([]),Path(tmp)/'memory')
            env=restore(gzip.decompress((initial(seed)/'physical.pkl.gz').read_bytes()),tmp,agent)
            for r in rr:
                assert state_digest(env)==r['state_hash_before']
                with contextlib.redirect_stdout(io.StringIO()):obs,reward,done,info=env.step({AGENT_ID:r['action']});env.update_scores(reward)
                assert state_digest(env)==r['state_hash'];replayed+=1
            with contextlib.redirect_stdout(io.StringIO()):agent.load_memory(folder/'final_memory')
            assert env.obs[AGENT_ID]==stop['observation'];records=[]
            for i,r in enumerate(stop['decision'].get('rec_records',[]),1):
                proposal=r['proposal'];action=proposal.get('action','').strip() if isinstance(proposal,dict) else ''
                syntax=valid_syntax(action,agent.available_actions)
                agc=agent.control.assess(proposal,stop['observation'],syntax,stop['step'])
                entry=dict(index=i,proposal=proposal,rec_check=r['check'],passed_to_agc=r['passed_to_agc'],
                    agc_assessment_at_terminal_state=agc,syntax_valid=syntax)
                if syntax:
                    before=state_digest(env)
                    with isolated_copy(env) as clone:
                        with contextlib.redirect_stdout(io.StringIO()):obs,reward,done,info=clone.step({AGENT_ID:action});clone.update_scores(reward)
                        entry['native']=dict(action=action,feedback=obs[AGENT_ID],reward=vars(reward[AGENT_ID]),info=info,
                            accepted=not failed(obs[AGENT_ID]) and not info.get('step_invalid_action',{}).get(AGENT_ID,False),
                            visible=visible(obs[AGENT_ID]),state_hash=state_digest(clone));probed+=1
                    assert state_digest(env)==before
                records.append(entry)
            out.append(dict(case=case_id(seed,'REC'),step=stop['step'],state_hash=state_digest(env),observation=stop['observation'],
                control=agent.control.to_dict(),records=records,source=str(terminal.relative_to(ROOT))))
    write(RESULTS/'terminal_review.json',dict(passed=True,cases=out,replayed_actions=replayed,isolated_probe_actions=probed,new_model_calls=0,
        caveat='AGC assessments are replayed at the saved terminal control state; original raw request sequence identifies whether it was reached. Native acceptance is local feasibility, not guaranteed model continuation.'))
    print(json.dumps(dict(passed=True,replayed_actions=replayed,probes=probed)),flush=True)

if __name__=='__main__':main()
