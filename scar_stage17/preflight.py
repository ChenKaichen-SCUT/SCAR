"""Zero-API adapter acceptance on old development objectives and synthetic public fixtures."""
import contextlib
import copy
import io
import json
import tempfile
from pathlib import Path
from scar.environment import restore,snapshot,state_digest,AGENT_ID
from scar.io import digest
from scar_stage16.controller import BaselineController
from scar_stage16.verify import verify
from .budget_adapter import Budget100Controller,adapt
from .common import RESULTS,write
from .environment import create_initial
from .methods import make_method,decision_state
from .evaluate import native_step,physical
from third_party_adapters.adaplanner_agentodyssey import validate_plan


class MockProvider:
    def __init__(self):self.calls=[]
    def generate(self,user_prompt,system_prompt=None,required=('action','reasoning'),phase='action',max_tokens=None,validator=None):
        self.calls.append(dict(user=user_prompt,system=system_prompt,phase=phase))
        if phase in ('plan','plan_check','revision'):
            steps=[dict(id=1,op='ask_LLM',question='What legal neutral action can be used?',bind='neutral'),
                   dict(id=2,op='action',action='${neutral}',expect={'not_error':True})]
            data=dict(reasoning='mock plan',steps=steps)
        elif phase=='resume':data=dict(reasoning='continue',start_from=1)
        elif phase=='ask_LLM':data=dict(answer='wait',reasoning='mock')
        else:data=dict(action='wait',reasoning='mock')
        if validator:validator(data)
        return dict(response=json.dumps(data),parsed=data,num_input_tokens=0,num_output_tokens=0)


def main():
    outcomes=[]
    # Function identity proves there is no policy transcription. The only altered
    # global of either cloned function is the explicitly authorized horizon.
    for name in ('finish','choose'):
        old=getattr(BaselineController,name);new=getattr(Budget100Controller,name)
        assert old.__code__ is new.__code__
        changes=[k for k in old.__globals__ if old.__globals__[k] is not new.__globals__[k]]
        assert changes==['EPISODE_ACTIONS'],changes
        assert old.__globals__['EPISODE_ACTIONS']==40 and new.__globals__['EPISODE_ACTIONS']==100
    oldverify=verify()
    for game,target in [('robot_kingdom','bandage_roll'),('quarantine','key'),('saltglass','brass_key')]:
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with contextlib.redirect_stdout(io.StringIO()):env,history=create_initial(game,171901,root/'initial')
            data=snapshot(env);initial=state_digest(env);objective='Obtain 1 '+target+' within 100 actions.'
            for method in ('A0','A1','A2','A3','A4'):
                provider=MockProvider();agent=make_method(method,game,provider,objective,target,history,root/method)
                test=restore(data,root/method,agent=agent);assert state_digest(test)==initial
                actions=[]
                for index in range(3):
                    before=copy.deepcopy(test.obs[AGENT_ID]);pre=snapshot(test)
                    with contextlib.redirect_stdout(io.StringIO()):action,*_=agent.act(before)
                    oid=test.world.auxiliary['obj_name_to_id'][target]
                    (obs,reward,done,info),effect=native_step(test,action,oid);test.update_scores(reward)
                    after=snapshot(test)
                    clone=restore(pre);ro,rr,rd,ri=clone.step({AGENT_ID:action});clone.update_scores(rr)
                    assert state_digest(clone)==state_digest(test),'observer changes native dynamics'
                    test=restore(after,agent=agent)
                    if hasattr(agent,'observe_transition'):agent.observe_transition(before,action,obs[AGENT_ID])
                    actions.append(action)
                memory=root/(method+'-memory');memory.mkdir();agent.save_memory(str(memory))
                restored=make_method(method,game,MockProvider(),objective,target,history,root/(method+'-restore'))
                restored.load_memory(str(memory))
                if method=='A0':adapt(restored)
                assert decision_state(restored,method).get('memory')==decision_state(agent,method).get('memory')
                if method=='A1':assert len(restored.short_term_memory)<=5
                if method=='A2':assert restored.memory.context==agent.memory.context and not agent.cfg.enable_summarization and not agent.cfg.enable_reflection
                if method in ('A3','A4'):assert restored.export()==agent.export()
                if method=='A3':
                    # Induce a public expectation discrepancy outside holdout.
                    agent.deviation={'kind':'test_discrepancy','feedback':'Cannot craft absent_object.'}
                    with contextlib.redirect_stdout(io.StringIO()):agent.act(test.obs[AGENT_ID])
                    phases=[c['phase'] for c in provider.calls]
                    assert all(p in phases for p in ('plan','plan_check','ask_LLM','revision','resume'))
                outcomes.append(dict(game=game,method=method,actions=actions,initial_hash=initial,
                    memory_restore=True,uninstrumented_native_replay=True,api_calls=0))
    # The controlled plan language rejects executable code and unbounded loops.
    rejected=0
    for plan in [{'steps':[{'id':1,'op':'exec','code':'open("hidden")'}]},
                 {'steps':[{'id':1,'op':'repeat','times':10000,'body':[]}]},
                 {'steps':[{'id':1,'op':'action','action':'wait','expect':{'hidden_state':True}}]}]:
        try:validate_plan(plan)
        except ValueError:rejected+=1
    assert rejected==3
    result=dict(passed=True,checks=outcomes,old_stage16_verification=oldverify,
        horizon_adaptation=dict(internal=100,old_source=40,unchanged_function_code_objects=True,
            changed_global_only='EPISODE_ACTIONS',unchanged_finish_window=6),
        controlled_language_rejections=rejected,formal_test_policy_runs=0,api_calls=0)
    write(RESULTS/'preflight_local.json',result);print(json.dumps({'passed':True,'method_game_checks':len(outcomes)}))

if __name__=='__main__':main()
