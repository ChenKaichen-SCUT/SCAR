"""All executed rejections and unique valid terminal candidates, before calls."""
import contextlib,copy,io,tempfile
from agents.saer.state import TaskState,rejected
from agents.agc.state import extract
from scar_stage26.replay import Saved
from scar_stage31.integration import make_agent as original_rec
from scar.agents.scar.repair import valid_syntax
from scar.io import digest
from .common import *

def main():
    offline()
    from scar.environment import restore,snapshot,state_digest
    samples=[];receipts=[];excluded=[]
    for seed in SEEDS:
        folder=parent(seed);rr=rows(folder/'trajectory.jsonl.gz');qq=rows(folder/'requests.jsonl.gz');stop=read(folder/'decision_exhausted.json');p=Saved(qq)
        with tempfile.TemporaryDirectory(prefix='scar32-prepare-') as tmp:
            with contextlib.redirect_stdout(io.StringIO()):agent=original_rec(seed,'REC',p,Path(tmp)/'memory')
            env=restore(gzip.decompress((initial(seed)/'physical.pkl.gz').read_bytes()),tmp,agent);agent.initialize_official(env.obs[AGENT_ID]);state=TaskState()
            def add(step,proposal,q,kind,indices):
                assert proposal['action'].strip() and q['raw_response']['choices'][0]['message']['content']
                marker='\n\nREC public execution state:\n';assert marker in q['messages'][1]['content']
                base_prompt=q['messages'][1]['content'].split(marker)[0];goal=agent.control.goal.goal_description if agent.control.goal else ''
                key=f's{seed}_a{step:03d}_{kind}_{len(samples):03d}';cp=f's{seed}_a{step:03d}'
                dest=RESULTS/'checkpoints'/cp;dest.mkdir(parents=True,exist_ok=True)
                if not (dest/'physical.pkl.gz').exists():(dest/'physical.pkl.gz').write_bytes(gzip.compress(snapshot(env),mtime=0))
                record=dict(id=key,checkpoint=cp,seed=seed,step=step,kind=kind,candidate=proposal,candidate_source_request_id=q['request_id'],
                    duplicate_source_proposal_indices=indices,base_prompt=base_prompt,system_prompt=q['messages'][0]['content'],
                    summary=state.summary(env.obs[AGENT_ID],goal,proposal),observation=copy.deepcopy(env.obs[AGENT_ID]),state_hash=state_digest(env),
                    source=str(folder.relative_to(ROOT)),task_state=state.to_dict(),no_future_feedback_in_input=True,
                    followup_action=rr[-1]['action'] if kind=='terminal' and rejected(rr[-1]['feedback']) else None)
                samples.append(record)
            for r in rr:
                n=r['step'];assert state_digest(env)==r['state_hash_before']
                bad=rejected(r['feedback']) or r['invalid_action']
                loss=extract(r['observation'])['hands'] is not None and extract(r['feedback'])['hands'] is None and 'too dark to see' in r['feedback']['text'].lower() and r['action'].startswith(('drop ','store ','unequip '))
                if bad or loss:
                    q=next(q for q in reversed(qq) if q['step']==n);proposal=r['decision']['attempts'][-1]['proposal'];add(n,proposal,q,'rejected' if bad else 'condition_loss',[len(r['decision']['rec_records'])])
                p.begin_step(n)
                with contextlib.redirect_stdout(io.StringIO()):action,ti,to,response=agent.act(r['observation'])
                assert action==r['action'] and digest(agent.decision)==digest(r['decision'])
                with contextlib.redirect_stdout(io.StringIO()):obs,reward,done,info=env.step({AGENT_ID:action});env.update_scores(reward)
                assert state_digest(env)==r['state_hash'];accepted_goal=agent.control.goal.goal_description if agent.control.goal else ''
                agent.observe_transition(r['observation'],action,obs[AGENT_ID]);assert digest(agent.control.to_dict())==digest(r['control_after']);agent.control.events.clear()
                state.observe(r['observation'],action,r['feedback'],accepted_goal,r['control_after'])
            unique={}
            for i,r in enumerate(stop['decision']['rec_records'],1):
                proposal=r['proposal'];syntax=isinstance(proposal,dict) and isinstance(proposal.get('action'),str) and valid_syntax(proposal['action'].strip(),agent.available_actions)
                if not syntax:excluded.append(dict(seed=seed,step=stop['step'],index=i,proposal=proposal,reason='Already invalid under unchanged native syntax; not a legal-path diagnostic.'));continue
                k=(proposal['action'].strip(),proposal['goal_description'])
                if k in unique:unique[k]['indices'].append(i)
                else:unique[k]=dict(proposal=proposal,indices=[i],q=next(q for q in qq if q['step']==stop['step'] and q['ordinal']==i))
            for item in unique.values():add(stop['step'],item['proposal'],item['q'],'terminal',item['indices'])
        receipts.append(dict(seed=seed,actions=len(rr),saved_contexts=len(p.calls),passed=True))
    assert len(samples)==77 and sum(s['kind']=='rejected' for s in samples)==70
    write(RESULTS/'samples.json',samples);write(RESULTS/'preparation.json',dict(passed=True,samples=len(samples),executed_rejections=70,observed_condition_losses=2,unique_terminal_candidates=5,
        source_episodes=3,receipts=receipts,excluded_invalid_terminal_candidates=excluded,unique_physical_checkpoints=len({s['checkpoint'] for s in samples}),new_model_calls=0))
    print(json.dumps(read(RESULTS/'preparation.json')),flush=True)

if __name__=='__main__':main()
