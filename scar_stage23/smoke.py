"""No-network end-to-end continuation and terminal idempotence smoke check."""
import contextlib
import copy
import io
import tempfile
from .common import *


def main():
    from scar_stage22b.common import forbid_network
    forbid_network()
    from . import run
    from scar.io import digest
    source_results=RESULTS
    with tempfile.TemporaryDirectory(prefix='scar23-smoke-') as tmp:
        temp=Path(tmp);out=temp/'results';out.mkdir()
        (out/'checkpoints').symlink_to(source_results/'checkpoints',target_is_directory=True)
        run.RESULTS=out;run.RUNTIME=temp/'runtime';run.MAX_STEPS=35;run.check_freeze=lambda:None
        calls=[]
        class Fake:
            def __init__(self,folder,*args):self.folder=folder;self.calls={};self.last=None
            def begin_step(self,n,h):self.n=n;self.h=h
            def generate(self,user_prompt,system_prompt=None,**kwargs):
                # Clearly labelled synthetic I/O check, not an experiment or
                # saved-response approximation on a divergent real trajectory.
                messages=[dict(role='system',content=system_prompt),dict(role='user',content=user_prompt)]
                response=json.dumps(dict(reasoning='offline synthetic transport test',action='wait'))
                self.last=dict(step=self.n,messages=messages,signature=digest(messages),
                    request_id='offline-smoke-'+str(self.n),state_hash_before=self.h,sample_origin='synthetic-smoke',
                    incremental_cost_usd=0,usage=dict(prompt_tokens=1,completion_tokens=1),
                    raw_response=dict(choices=[dict(message=dict(content=response))]))
                self.calls[self.n]=self.last;calls.append(self.n)
                return dict(response=response,num_input_tokens=1,num_output_tokens=1)
        run.PairedProvider=Fake
        with contextlib.redirect_stdout(io.StringIO()):
            result=run.execute(33,'Stage18-Reset',None)
        assert result['status']=='step_limit' and result['steps']==3 and result['last_step']==35,result
        assert result['new_model_requests']==0
        with contextlib.redirect_stdout(io.StringIO()):again=run.execute(33,'Stage18-Reset',None)
        assert again==result and calls==[33,34,35]
        rr=rows(out/'runs/mark-a033/Stage18-Reset/trajectory.jsonl.gz')
        assert len(rr)==3 and len(rows(out/'runs/mark-a033/Stage18-Reset/requests.jsonl.gz'))==3
        assert (out/'runs/mark-a033/Stage18-Reset/final_memory/stage18.json').exists()
    write(RESULTS/'smoke.json',dict(passed=True,synthetic_steps=3,api_calls=0,
        scope='Runner I/O and terminal idempotence only; synthetic actions excluded from all scientific results'))
    print('Offline continuation/checkpoint/archive/idempotence smoke passed',flush=True)


if __name__=='__main__':main()
