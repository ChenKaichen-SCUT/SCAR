"""End-to-end adapter with fake completions and a network tripwire."""
import json,os,socket,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from agents.feedback_v5_agent import create_feedback_v5_agent
from agents.feedback_v5_core import ScreenStopped
from agents.llm_agent_config import LLMAgentConfig

class FakeAgent:
    def __init__(self,id,name):
        self.id=id;self.name=name;self.available_actions=[SimpleNamespace(verb=v,params=p) for v,p in [('craft',['amount','obj_name']),('inspect',['object_name']),('pick up',['object_name']),('equip',['object_name']),('enter',['area_name']),('wait',[])]]
class FakeModel:
    def __init__(self,outputs):self.outputs=iter(outputs);self.calls=[]
    def generate(self,**kw):self.calls.append(kw);return {'response':json.dumps(next(self.outputs)),'num_input_tokens':10,'num_output_tokens':5}
def observation(hands='no objects',near='1 ore',extra='',place='workshop'):
    return f'Current Location: {place}\nguide says: Main goal: Build.\nCurrent tasks:\n[1] Craft a device.\nI am holding {hands}.\nI have equipped no objects.\nI see {near} near me.\nNeighboring areas: corridor.\nIt can be used to craft: device (2 ore)\n{extra}'
def proposal(action,path=None):return {'reasoning':'use observed prerequisites','action':action,'objective':{'action':'craft 1 device'},'candidates':[{'actions':path or [action]}]}

class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();os.environ['AO_CONTROL_AUDIT']=str(Path(self.tmp.name)/'audit.jsonl');os.environ['AO_V5_BASE_URL']='http://127.0.0.1:8094/offline/v1'
        self.tripwire=patch.object(socket.socket,'connect',side_effect=AssertionError('Offline test attempted network'));self.tripwire.start()
    def tearDown(self):self.tripwire.stop();self.tmp.cleanup()
    def agent(self,outputs):
        a=create_feedback_v5_agent(FakeAgent)('fake','fake',LLMAgentConfig(llm_name='deepseek-flash',llm_provider='openai'));a.llm=FakeModel(outputs);return a
    def test_queue_runs_before_model_and_audit_stays_local(self):
        a=self.agent([proposal('pick up ore',['pick up ore','enter corridor'])]);o1=observation();r1=a._act({'text':o1});self.assertEqual(r1[0],'pick up ore')
        o2=observation('1 ore','no objects','I picked up ore.');r2=a._act({'text':o2})
        self.assertEqual(r2[0],'enter corridor');self.assertEqual(r2[1:3],(0,0));self.assertEqual(len(a.llm.calls),1)
        self.assertIn(o1,a.memory.context);self.assertIn(o2,a.memory.context);self.assertNotIn('full_ledger',a.memory.context);self.assertNotIn('recent_dispatcher_interventions',a.memory.context)
        lines=[json.loads(x) for x in Path(os.environ['AO_CONTROL_AUDIT']).read_text().splitlines()];decisions=[x for x in lines if x['event']=='decision']
        self.assertEqual([x['paid_call_this_step'] for x in decisions],[True,False]);self.assertIn('full_ledger',decisions[1])
        a.observe_final(observation('1 ore',place='corridor'));a.save_memory(full_memory_dir=self.tmp.name);self.assertTrue((Path(self.tmp.name)/'feedback_v5_state.json').exists())
    def test_new_hazard_rechecks_with_model(self):
        a=self.agent([proposal('pick up ore',['pick up ore','enter corridor']),proposal('wait')]);a._act({'text':observation()})
        r=a._act({'text':observation('1 ore',extra='I picked up ore.\nI was attacked by enemy and lost 2 HP.')})
        self.assertEqual(r[0],'wait');self.assertEqual(len(a.llm.calls),2)
    def test_old_preparation_does_not_override_new_route(self):
        a=self.agent([proposal('wait'),proposal('enter corridor')]);a._act({'text':observation('1 ore')})
        # New danger requires a fresh decision; the old objective still wants nearby ore.
        r=a._act({'text':observation('1 ore',extra='I was attacked by enemy and lost 2 HP.')})
        self.assertEqual(r[0],'enter corridor');self.assertEqual(len(a.llm.calls),2)
    def test_bounded_repair_stops_instead_of_unlimited_calls(self):
        a=self.agent([proposal('craft 1 device')]*6)
        with self.assertRaises(ScreenStopped):a._act({'text':observation()})
        self.assertEqual(len(a.llm.calls),2);self.assertEqual(a.repairs,1)

if __name__=='__main__':unittest.main(verbosity=2)
