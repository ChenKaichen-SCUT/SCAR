import json,os,socket,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from agents.feedback_v3r4_agent import create_feedback_v3r4_agent
from agents.llm_agent_config import LLMAgentConfig

class FakeAgent:
    def __init__(self,id,name):
        self.id=id;self.name=name;self.available_actions=[SimpleNamespace(verb=v,params=p) for v,p in [('enter',['area_name']),('wait',[]),('pick up',['object_name']),('craft',['amount','obj_name'])]]
class FakeModel:
    def __init__(self):self.calls=0
    def generate(self,*args,**kw):
        self.calls+=1
        return {'response':json.dumps({'action':'invalid_magic','candidates':[{'actions':['invalid_magic']}]}),'num_input_tokens':3,'num_output_tokens':2}
class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();os.environ['AO_CONTROL_AUDIT']=str(Path(self.tmp.name)/'audit.jsonl');os.environ['AO_API_BASE_URL']='http://127.0.0.1:8094/offline/v1';os.environ['AO_CALL_LIMIT']='502'
        self.tripwire=patch.object(socket.socket,'connect',side_effect=AssertionError('Unexpected network'));self.tripwire.start()
        self.a=create_feedback_v3r4_agent(FakeAgent)('fake','fake',LLMAgentConfig(llm_name='deepseek-flash',llm_provider='openai'));self.a.llm=FakeModel()
    def tearDown(self):self.tripwire.stop();self.tmp.cleanup()
    def test_300_rejected_batches_do_not_terminate_or_overspend(self):
        for step in range(300):
            room='room' if step%2==0 else 'corridor';other='corridor' if step%2==0 else 'room'
            text=f'Current Location: Lab, {room}\nI entered {room}.\nI am holding no objects.\nI have equipped no objects.\nI see no objects near me.\nNeighboring areas: {other}.\n'
            action,_,_,_=self.a._act({'text':text});self.assertTrue(action.startswith('enter ') or action=='wait')
        self.assertEqual(self.a.ledger.step,300);self.assertLessEqual(self.a.llm.calls,502);self.assertEqual(self.a.fallbacks,300)
        self.a.save_memory(full_memory_dir=self.tmp.name);self.assertTrue((Path(self.tmp.name)/'feedback_v3r4_state.json').exists())
        self.assertNotIn('"packet":',self.a.memory.context);self.assertNotIn('"containers":',self.a.memory.context)
    def test_explicit_tutorial_needs_no_api(self):
        action,ti,to,_=self.a._act({'text':'Current Location: Lab, room\nRequired action: `wait`\nI am holding no objects.\nI have equipped no objects.\nI see no objects near me.\n'})
        self.assertEqual((action,ti,to),('wait',0,0));self.assertEqual(self.a.llm.calls,0)
if __name__=='__main__':unittest.main(verbosity=2)
