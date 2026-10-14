import contextlib,io,tempfile,json
from agents.agc_v2.control import Control
from agents.saer.state import TaskState
from agents.saer.reflection import REFLECTION_SYSTEM
from scar_stage22.provider import Provider
from .common import *
from .integration import make_agent

def main():
    offline()
    from scar.environment import restore,state_digest
    receipts=[]
    for seed in SEEDS:
        rr=rows(baseline(seed)/'trajectory.jsonl.gz')[:2];qq=rows(baseline(seed)/'requests.jsonl.gz')
        class Fake:
            def begin_step(self,n):self.n=n;self.count=0
            def generate(self,user_prompt,system_prompt=None,**kwargs):
                self.count+=1;q=next(q for q in qq if q['step']==self.n and q['ordinal']==1)
                if system_prompt==REFLECTION_SYSTEM:return dict(response=json.dumps(dict(predicted_effect='A scripted uncertain effect.',goal_risk='high',reason='A test advisory warning.')),num_input_tokens=1,num_output_tokens=1)
                return Provider.result(q)
        p=Fake()
        with tempfile.TemporaryDirectory(prefix='scar32-smoke-') as tmp:
            with contextlib.redirect_stdout(io.StringIO()):agent=make_agent(seed,p,Path(tmp)/'memory')
            env=restore(gzip.decompress((initial(seed)/'physical.pkl.gz').read_bytes()),tmp,agent);agent.initialize_official(env.obs[AGENT_ID])
            for r in rr:
                p.begin_step(r['step'])
                with contextlib.redirect_stdout(io.StringIO()):action,ti,to,response=agent.act(r['observation'])
                assert action==r['action'] and p.count==3 and agent.decision['saer_records'][0]['warning']
                assert not agent.decision['saer_risk_veto'];assert len(agent.short_term_memory)==r['step']
                with contextlib.redirect_stdout(io.StringIO()):obs,reward,done,info=env.step({AGENT_ID:action});env.update_scores(reward)
                assert state_digest(env)==r['state_hash'];agent.observe_transition(r['observation'],action,obs[AGENT_ID]);agent.control.events.clear()
            agent.save_memory(Path(tmp)/'roundtrip');state=agent.task_state.to_dict();agent.load_memory(Path(tmp)/'roundtrip');assert agent.task_state.to_dict()==state
            if seed==42:
                observation=dict(step=1,text='Current Location: Test, room\n\nI am holding 1 resource.\nI have equipped no objects.\nI see 1 resource near me.\nI see no one nearby.\nNeighboring areas: elsewhere.\n')
                class Script:
                    def __init__(self,mode):self.mode=mode;self.n=0
                    def generate(self,user_prompt,system_prompt=None,**kw):
                        self.n+=1
                        if system_prompt==REFLECTION_SYSTEM:
                            response='{' if self.mode=='malformed' else json.dumps(dict(predicted_effect='May lose a resource.',goal_risk=self.mode,reason='Unknown recoverability.'))
                        else:response=json.dumps(dict(action='drop resource',reasoning='A deliberate test choice.',goal_description='Acquire a resource',goal_evidence='I am holding 1 resource.'))
                        return dict(response=response,num_input_tokens=1,num_output_tokens=1)
                for mode in ['high','low','malformed']:
                    agent.control=Control();agent.task_state=TaskState();agent.short_term_memory=[];agent.llm=Script(mode)
                    action,ti,to,response=agent._act(observation)
                    assert action=='drop resource' and agent.llm.n==3 and ti==to==3 and len(agent.short_term_memory)==1
                    record=agent.decision['saer_records'][0];assert record['warning']==(mode=='high') and not record['risk_veto']
        receipts.append(dict(seed=seed,actions=2,high_risk_kept_without_veto=True))
    write(RESULTS/'smoke.json',dict(passed=True,receipts=receipts,malformed_reflection_soft_continuation=True,
        high_and_low_risk_candidates_may_execute_unchanged=True,token_accounting_and_persistence_verified=True,new_model_calls=0))
    print(json.dumps(read(RESULTS/'smoke.json')),flush=True)

if __name__=='__main__':main()
