import json,os,tempfile,unittest
from pathlib import Path
from agents.feedback_v5_core import Ledger
import v5_full500_runtime
class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'runtime.jsonl';os.environ['AO_RUNTIME_AUDIT']=str(self.path)
    def tearDown(self):self.temp.cleanup()
    def test_invalid_array_is_ignored_without_inventing_test(self):
        s=Ledger();s.observations[1]='The workshop has a bench.'
        for pre,post in [([], 'effect'),('precondition',[]),(None,[])]:
            s.apply_review({'hypotheses':[{'id':'bad','preconditions':pre,'expected':post,'evidence':[{'step':1,'quote':'workshop has a bench'}]}]})
        self.assertEqual(s.test_specs,{})
        self.assertEqual(len(self.path.read_text().splitlines()),3)
    def test_valid_hypothesis_survives(self):
        s=Ledger();s.observations[1]='The workshop has a bench.'
        s.apply_review({'hypotheses':[{'id':'ok','preconditions':[{'kind':'held','object':'ore'}],'expected':[{'kind':'crafted','object':'bar','amount':1}],'evidence':[{'step':1,'quote':'workshop has a bench'}]}]})
        self.assertIn('ok',s.test_specs)
    def test_screen_stop_records_but_does_not_end_full_evaluation(self):
        s=Ledger();s.step=52;s.replan_at=40
        self.assertFalse(s.request_replan_if_needed());self.assertEqual(s.replan_at,40)
        self.assertEqual(json.loads(self.path.read_text())['event'],'screen_stop_recorded_without_termination')
if __name__=='__main__':unittest.main(verbosity=2)
