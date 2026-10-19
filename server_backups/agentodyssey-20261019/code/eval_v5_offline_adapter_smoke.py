"""Exercise the real evaluator's keyword save and final-observation hooks, no network."""
import json,runpy,socket
from unittest.mock import patch
from agents.feedback_v5_agent import GuardedModel
def fake_generate(self,**kw):return {'response':json.dumps({'action':'wait','reasoning':'offline interface check'}),'num_input_tokens':0,'num_output_tokens':0}
with patch.object(GuardedModel,'generate',fake_generate),patch.object(socket.socket,'connect',side_effect=AssertionError('Offline harness attempted network')):
    runpy.run_path(__file__.replace('eval_v5_offline_adapter_smoke.py','eval_feedback_v5.py'),run_name='__main__')
