"""Zero-API adapter, save/load and native three-action tests for nine cases."""
import contextlib
import gzip
import io
import shutil
import tempfile
from types import SimpleNamespace
from .common import *

def main():
    offline()
    import scar_stage25.run as run
    from agents.agc.state import extract
    from scar.environment import restore,state_digest
    from scar.io import append_jsonl
    receipts=[]
    with tempfile.TemporaryDirectory(prefix='scar25-smoke-') as tmp:
        root=Path(tmp);run.RUNTIME=root/'runtime';run.RESULTS=root/'results';run.MAX_STEPS=3;run.check_freeze=lambda:None
        shutil.copytree(RESULTS/'initial',run.RESULTS/'initial')
        for game,seed in CASES:
            initial=RESULTS/'initial'/case_id(game,seed)
            class Fake:
                def __init__(self,folder,*a):self.audit=folder/'requests.jsonl';self.episode=SimpleNamespace(total=lambda:0);self.cache={}
                def begin_step(self,n):self.step=n
                def generate(self,**kw):
                    # Only public instruction parsing; deliberately not a model experiment.
                    text=kw['user_prompt'].split('AGC public state summary:')[0]
                    import re
                    required=re.findall(r'Required action:\s*`([^`]+)`',text)
                    action=required[-1] if required else 'wait'
                    proposal=dict(action=action,reasoning='Synthetic smoke.',goal_description='Execute the current public instruction',goal_evidence='Current Location:')
                    record=dict(step=self.step,charged_or_reserved_usd=0,cost_usd=0,usage=dict(prompt_tokens=1,completion_tokens=1))
                    append_jsonl(self.audit,record);self.cache[self.step]=record
                    return dict(response=json.dumps(proposal),num_input_tokens=1,num_output_tokens=1)
            run.SharedProvider=Fake
            with contextlib.redirect_stdout(io.StringIO()):summary=run.execute(game,seed,'unused')
            assert summary['status']=='step_limit' and summary['steps']==3,summary
            rr=rows(run.RESULTS/'runs'/case_id(game,seed)/'trajectory.jsonl.gz')
            with tempfile.TemporaryDirectory(prefix='scar25-smoke-native-') as native:
                env=restore(gzip.decompress((initial/'physical.pkl.gz').read_bytes()),native)
                for r in rr:
                    with contextlib.redirect_stdout(io.StringIO()):obs,reward,done,info=env.step({AGENT_ID:r['action']});env.update_scores(reward)
                    assert state_digest(env)==r['state_hash']
            with contextlib.redirect_stdout(io.StringIO()):assert run.execute(game,seed,'unused')==summary
            from .integration import make_agent
            with contextlib.redirect_stdout(io.StringIO()):agent=make_agent(game,seed,Fake(root),root/'loaded')
            cp=run.RUNTIME/'runs'/case_id(game,seed)/'checkpoint-003'
            with contextlib.redirect_stdout(io.StringIO()):agent.load_memory(cp)
            assert agent.control.to_dict()==read(cp/'agc_v2.json')['control']
            receipts.append(dict(case=case_id(game,seed),native_steps=3,checkpoint_and_idempotence=True))
    write(RESULTS/'smoke.json',dict(passed=True,runs=receipts,new_model_calls=0,synthetic_only=True));print(json.dumps(receipts))

if __name__=='__main__':main()
