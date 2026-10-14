"""Zero-model end-to-end intervention, checkpoint and resume contracts."""
import contextlib
import io
import shutil
import tempfile
from types import SimpleNamespace
from .common import *
from .replay import Saved
from scar.io import append_jsonl,digest

def main():
    offline();import scar_stage26.run as run
    original_results=RESULTS;receipts=[]
    with tempfile.TemporaryDirectory(prefix='scar26-smoke-') as tmp:
        run.RESULTS=Path(tmp)/'results';run.RUNTIME=Path(tmp)/'runtime';run.check_freeze=lambda:None
        shutil.copytree(RESULTS/'checkpoints',run.RESULTS/'checkpoints')
        class Fake(Saved):
            def __init__(self,folder,start,key):
                super().__init__(rows(SOURCE/'requests.jsonl.gz'));self.start=start;self.folder=Path(folder);self.reuses={}
                self.paid=SimpleNamespace(audit=self.folder/'requests.jsonl',cache={},episode=SimpleNamespace(total=lambda:0))
            def generate(self,user_prompt,system_prompt=None,**kw):
                if self.step==self.start:
                    output=super().generate(user_prompt,system_prompt,**kw);self.reuses[str(self.ordinal)]={'synthetic_reuse':True};return output
                self.ordinal+=1
                proposal=dict(action='defend',reasoning='Synthetic no-API continuation contract.',goal_description='Respond to current public state',goal_evidence='Current Location:')
                q=dict(step=self.step,ordinal=self.ordinal,usage=dict(prompt_tokens=1,completion_tokens=1),cost_usd=0,charged_or_reserved_usd=0)
                append_jsonl(self.paid.audit,q);self.paid.cache[self.ordinal]=q
                return dict(response=json.dumps(proposal),num_input_tokens=1,num_output_tokens=1)
        run.BranchProvider=Fake
        for n in CASES:
            run.MAX_STEPS=n
            with contextlib.redirect_stdout(io.StringIO()):s=run.execute(n,'unused')
            assert s['status']=='step_limit' and s['steps']==1 and s['intervention_count']==1,s
            out=run.RESULTS/'runs'/case_id(n)/'Oracle';first=rows(out/'trajectory.jsonl.gz')[0]
            expected=read(original_results/'checkpoints'/case_id(n)/'post_decision.json')
            assert first['memory_after_act_hash']==digest(expected['memory']) and first['goal_after_act_hash']==digest(expected['control'])
            assert first['state_hash']==read(original_results/'checkpoints'/case_id(n)/'oracle_probe.json')['state_hash']
            with contextlib.redirect_stdout(io.StringIO()):assert run.execute(n,'unused')==s
            # Only temporary smoke outputs are removed; preserve the committed checkpoint.
            (out/'summary.json').unlink();run.MAX_STEPS=n+1
            with contextlib.redirect_stdout(io.StringIO()):s=run.execute(n,'unused')
            rr=rows(out/'trajectory.jsonl.gz')
            assert s['status']=='step_limit' and len(rr)==2 and rr[0]==first and s['intervention_count']==1,s
            assert rr[1]['action']==rr[1]['proposed_action']=='defend' and not rr[1]['oracle_replacement']
            receipts.append(dict(case=case_id(n),intervention_exact=True,memory_and_goal_unedited=True,resume_without_repeat=True,idempotent_completed_run=True,synthetic_followup_actions=1))
    write(original_results/'smoke.json',dict(passed=True,cases=receipts,new_model_calls=0,synthetic_only=True))
    print(json.dumps(dict(passed=True,cases=len(receipts),new_model_calls=0)))

if __name__=='__main__':main()
