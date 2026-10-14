import contextlib
import io
import tempfile
import copy
from agents.rec_v1.state import Tracker
from agents.agc_v2.control import Control
from agents.agc.agent import DecisionUnavailable
from scar_stage26.replay import Saved
from scar_stage22.provider import Provider
from .common import *
from .integration import make_agent

def unit_checks():
    def obs(step,held,feedback='',location='Test, room',ground='1 fixture'):
        return dict(step=step,text=f'Current Location: {location}\n\n{feedback}\n\nI am holding {held}.\nI have equipped no objects.\nI see {ground} near me.\nI see no one nearby.\nNeighboring areas: other.\n')
    t=Tracker();a=obs(1,'2 mineral','I have acquired a new item: mineral. It can be used to craft: product (2 mineral)')
    t.ingest(a);proposal=dict(goal_description='craft product',action='drop mineral')
    assert t.assess(proposal)['decision']=='RECONSIDER'
    assert t.assess(dict(proposal,action='store 1 mineral box'))['decision']=='ALLOW'
    assert t.assess(dict(proposal,goal_description='explore the world'))['decision']=='ALLOW'
    unknown=dict(step=2,text='Current Location: Test, room\nIt is too dark to see anything here.')
    t.ingest(unknown);assert t.inventory()['owned_counts'] is None and t.requirements('craft product')['missing']['mineral'] is None
    t=Tracker();t.observe(a,'craft 1 product',obs(2,'2 mineral','Cannot craft a single product. Do not have sufficient amount of necessary ingredients.'),'craft product')
    assert t.assess(dict(proposal,action='craft 1 product'))['decision']=='RECONSIDER'
    t.ingest(obs(3,'3 mineral'));assert t.assess(dict(proposal,action='craft 1 product'))['decision']=='ALLOW'
    t=Tracker();t.observe(unknown,'take out lamp box',dict(step=3,text='Current Location: Test, room\nCannot take out lamp, not enough space in hand.\nIt is too dark to see anything here.'),'explore')
    assert t.assess(dict(goal_description='explore',action='take out lamp box'))['decision']=='ALLOW'
    t=Tracker();t.observe(a,'craft 1 product',obs(2,'no objects','I successfully crafted 1 product. It is now on the ground.'),'craft product')
    assert not t.requirements('craft product')['known']
    t=Tracker();before=obs(1,'1 lamp');after=dict(step=2,text='Current Location: Test, room\nI dropped lamp.\nIt is too dark to see anything here.')
    assert t.assess(dict(goal_description='explore',action='drop lamp'))['decision']=='ALLOW'
    t.observe(before,'drop lamp',after,'explore');t.ingest(obs(3,'1 lamp'))
    assert any(x['kind']=='observed_condition_loss_risk' for x in t.assess(dict(goal_description='explore',action='drop lamp'))['reasons'])
    assert t.assess(dict(goal_description='explore',action='store 1 lamp absent_box'))['decision']=='ALLOW'
    assert Tracker.from_dict(t.to_dict()).to_dict()==t.to_dict()
    return dict(passed=True,checks=11,zero_hidden_state=True)

def main():
    offline();units=unit_checks()
    from scar.environment import restore,state_digest
    from scar.io import digest
    receipts=[]
    for seed in SEEDS:
        source=baseline(seed);rr=rows(source/'trajectory.jsonl.gz')[:2];qq=rows(source/'requests.jsonl.gz')
        lookup={(q['step'],q['ordinal']):q for q in qq}
        class Fake:
            def begin_step(self,n):self.step=n;self.ordinal=0
            def generate(self,user_prompt,system_prompt=None,**kw):
                self.ordinal+=1;q=lookup[self.step,self.ordinal]
                assert system_prompt==q['messages'][0]['content']
                assert user_prompt.startswith(q['messages'][1]['content']+'\n\nREC public execution state:\n')
                return Provider.result(q)
        p=Fake()
        with tempfile.TemporaryDirectory(prefix='scar31-smoke-') as tmp:
            with contextlib.redirect_stdout(io.StringIO()):agent=make_agent(seed,'REC',p,Path(tmp)/'memory')
            env=restore(gzip.decompress((initial(seed)/'physical.pkl.gz').read_bytes()),tmp,agent);agent.initialize_official(env.obs[AGENT_ID])
            for r in rr:
                p.begin_step(r['step']);assert state_digest(env)==r['state_hash_before']
                with contextlib.redirect_stdout(io.StringIO()):action,ti,to,response=agent.act(r['observation'])
                assert action==r['action'] and agent.decision['rec_reconsider_calls']==0
                with contextlib.redirect_stdout(io.StringIO()):obs,reward,done,info=env.step({AGENT_ID:action});env.update_scores(reward)
                assert state_digest(env)==r['state_hash'];agent.observe_transition(r['observation'],action,obs[AGENT_ID]);agent.control.events.clear()
            agent.save_memory(Path(tmp)/'roundtrip');before=agent.rec.to_dict();agent.load_memory(Path(tmp)/'roundtrip');assert agent.rec.to_dict()==before
            if seed==42:
                synthetic=dict(step=1,text='Current Location: Test, room\n\nI have acquired a new item: mineral. It can be used to craft: product (2 mineral)\n\nI am holding 2 mineral.\nI have equipped no objects.\nI see 1 fixture near me.\nI see no one nearby.\nNeighboring areas: other.\n')
                class Scripted:
                    def __init__(self,repeat=False):self.n=0;self.repeat=repeat
                    def generate(self,**kw):
                        self.n+=1;action='drop mineral' if self.n==1 or self.repeat else 'inspect mineral'
                        return dict(response=json.dumps(dict(action=action,reasoning='A scripted integration fixture.',goal_description='craft product',goal_evidence='I am holding 2 mineral.')),num_input_tokens=1,num_output_tokens=1)
                agent.control=Control();agent.rec=Tracker();agent.short_term_memory=[];agent.llm=Scripted()
                action,ti,to,response=agent._act(synthetic)
                assert action=='inspect mineral' and agent.llm.n==2 and agent.decision['rec_reconsider_calls']==1 and ti==to==2
                assert len(agent.short_term_memory)==1 and 'Action: drop mineral' not in agent.short_term_memory[0]
                agent.control=Control();agent.rec=Tracker();agent.short_term_memory=[];agent.llm=Scripted(True)
                try:agent._act(synthetic)
                except DecisionUnavailable:pass
                else:raise AssertionError('Repeated resource loss must not create a fallback action')
                assert agent.llm.n==3 and not agent.short_term_memory and agent.decision['executed_action'] is None
        receipts.append(dict(seed=seed,passed=True,exact_native_initial_actions=2))
    write(RESULTS/'smoke.json',dict(passed=True,units=units,receipts=receipts,scripted_reconsider_and_exhaustion_passed=True,new_model_calls=0))
    print(json.dumps(read(RESULTS/'smoke.json')),flush=True)

if __name__=='__main__':main()
