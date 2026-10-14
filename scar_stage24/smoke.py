"""Offline three-action adapter/checkpoint tests; not measured agent trials."""
import contextlib
import io
import tempfile
from types import SimpleNamespace
from .common import *
from scar.io import append_jsonl


def main():
    offline()
    import scar_stage24.run as run
    results=RESULTS;receipts=[]
    with tempfile.TemporaryDirectory(prefix='scar24-smoke-') as tmp:
        root=Path(tmp);run.RUNTIME=root/'runtime';run.RESULTS=root/'results';run.MAX_STEPS=3;run.check_freeze=lambda:None
        import shutil
        shutil.copytree(results/'initial',run.RESULTS/'initial')
        for game in GAMES:
            original=rows(source(game)/'trajectory.jsonl.gz')
            class Fake:
                def __init__(self,folder,*a):
                    self.audit=folder/'requests.jsonl';self.episode=SimpleNamespace(total=lambda:0);self.cache={}
                def begin_step(self,n):self.step=n
                def generate(self,**kwargs):
                    quote=original[self.step-1]['observation']['text'].splitlines()[1]
                    proposal=dict(action=original[self.step-1]['action'],reasoning='Offline adapter smoke only.',
                        goal_description='Execute the current public instruction',goal_evidence=quote)
                    record=dict(step=self.step,charged_or_reserved_usd=0,cost_usd=0,usage=dict(prompt_tokens=1,completion_tokens=1))
                    append_jsonl(self.audit,record);self.cache[self.step]=record
                    return dict(response=json.dumps(proposal),num_input_tokens=1,num_output_tokens=1)
            run.SharedProvider=Fake
            with contextlib.redirect_stdout(io.StringIO()):summary=run.execute(game,'unused')
            assert summary['status']=='step_limit' and summary['steps']==3,summary
            new=rows(run.RESULTS/'runs'/f'{game}__AGC'/'trajectory.jsonl.gz')
            assert [r['state_hash'] for r in new]==[r['state_hash'] for r in original[:3]],game
            with contextlib.redirect_stdout(io.StringIO()):assert run.execute(game,'unused')==summary
            receipts.append(dict(game=game,actions=3,native_exact=True,checkpoint_archive_and_idempotence=True))
    write(results/'smoke.json',dict(passed=True,new_model_calls=0,synthetic_adapter_test_only=True,runs=receipts))
    print(json.dumps(receipts))

if __name__=='__main__':main()
