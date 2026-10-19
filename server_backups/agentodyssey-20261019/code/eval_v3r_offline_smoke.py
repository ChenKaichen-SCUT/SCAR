"""Exercise the real evaluator's keyword save and final-observation hooks, no network."""
import json,runpy,socket
from unittest.mock import patch
from agents.feedback_v3r_agent import Model
def fake_generate(self,*args,**kw):return {'response':json.dumps({'action':'wait','reasoning':'offline interface check'}),'num_input_tokens':0,'num_output_tokens':0}
with patch.object(Model,'generate',fake_generate),patch.object(socket.socket,'connect',side_effect=AssertionError('Offline harness attempted network')):
    runpy.run_path(__file__.replace('eval_v3r_offline_smoke.py','eval_feedback_v3r.py'),run_name='__main__')
