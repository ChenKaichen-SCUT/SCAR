import unittest
from study_selection import select,PRIORITY,GAMES
class SelectionTests(unittest.TestCase):
    def reference(self):return {'remnant':{'main':1},'metropolis':{'main':18}}
    def runs(self):return {g+'__ab_'+v:{'main_quest':self.reference()[g]['main'],'returncode':0,'completion_reason':'step_limit'} for v in PRIORITY for g in GAMES}
    def test_no_evidence_does_not_remove(self):self.assertEqual(select(self.reference(),self.runs())['disabled_components'],[])
    def test_single_valid_gain_can_select_one_group(self):
        r=self.runs();r['remnant__ab_no_hypothesis']['main_quest']=2
        self.assertEqual(select(self.reference(),r)['disabled_components'],['hypothesis'])
    def test_failure_cannot_win_by_score(self):
        r=self.runs();r['remnant__ab_no_repeat'].update(main_quest=20,returncode=1,completion_reason='api_balance_exhausted')
        self.assertIsNone(select(self.reference(),r)['selected_ablation'])
    def test_metropolis_regression_disqualifies(self):
        r=self.runs();r['remnant__ab_no_checks']['main_quest']=3;r['metropolis__ab_no_checks']['main_quest']=17
        self.assertIsNone(select(self.reference(),r)['selected_ablation'])
if __name__=='__main__':unittest.main(verbosity=2)
