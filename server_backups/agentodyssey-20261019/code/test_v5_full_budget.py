import tempfile,unittest
from pathlib import Path
from budget_guard_v5_full import BudgetGuard,BudgetStopped
class Tests(unittest.TestCase):
    def test_longer_history_still_subject_to_persistent_total(self):
        with tempfile.TemporaryDirectory() as temp:
            limits=dict(calls=2,input_tokens=3_000_000,uncached_input_tokens=3_000_000,output_tokens=2000)
            g=BudgetGuard(Path(temp)/'budget.sqlite',limits)
            req=g.reserve('game',[{'role':'user','content':'x'*200000}],768)
            self.assertTrue(g.complete(req,dict(prompt_tokens=50000,completion_tokens=20,prompt_cache_miss_tokens=5000)))
            g2=BudgetGuard(Path(temp)/'budget.sqlite',limits);g2.reserve('game',[{'role':'user','content':'test'}],768)
            with self.assertRaises(BudgetStopped):g2.reserve('game',[{'role':'user','content':'test'}],768)
            self.assertEqual(g2.usage()['calls'],2)
    def test_new_single_request_limit_still_pre_request(self):
        with tempfile.TemporaryDirectory() as temp:
            limits=dict(calls=2,input_tokens=3_000_000,uncached_input_tokens=3_000_000,output_tokens=2000);g=BudgetGuard(Path(temp)/'b.sqlite',limits)
            with self.assertRaises(BudgetStopped):g.reserve('game',[{'role':'user','content':'x'*1_000_000}],768)
            self.assertEqual(g.usage()['calls'],0)
if __name__=='__main__':unittest.main(verbosity=2)
