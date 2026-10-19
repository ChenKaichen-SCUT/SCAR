import unittest
from feedback_v3r2_core import Ledger
from test_feedback_v3r import obs

class ExecutionAuthorityTests(unittest.TestCase):
    def test_fresh_route_is_not_overwritten_by_old_queue_or_preparation(self):
        s=Ledger();s.advance(obs());s.neighbors=['store','forest'];s.queue=['enter forest']
        s.preparation=lambda:'enter forest'
        a,c,d=s.dispatch([{'actions':['enter store','pick up part']}],None)
        self.assertEqual(a,'enter store');self.assertEqual(s.queue,['enter store','pick up part'])
        self.assertEqual(d['source'],'fresh_model_candidate')
    def test_existing_intermediate_precedes_recursive_manufacturing(self):
        s=Ledger();s.advance(obs());s.neighbors=['store','forest']
        s.world={'Lab, store':{'objects':{'part':1},'step':1,'epoch':s.epoch},'Lab, forest':{'objects':{'raw':1},'step':2,'epoch':s.epoch}}
        s.recipes={'part':{'ingredients':{'raw':2}}}
        self.assertEqual(s.acquire('part',1,{'part':1}),'enter store')
    def test_historic_resource_travel_is_not_automatic_but_fresh_commitment_can_be(self):
        s=Ledger();s.advance(obs());s.new_task=False
        cert,_=s.preparation_certificate('enter corridor',None,'dependency_preparation')
        self.assertFalse(cert['authorized'])
        cert,_=s.preparation_certificate('enter corridor',None,'committed_short_plan')
        self.assertTrue(cert['authorized'],cert)
    def test_loop_invalidates_even_committed_local_travel(self):
        s=Ledger();s.advance(obs());s.loop={'actions':['enter corridor','enter room']}
        cert,_=s.preparation_certificate('enter corridor',None,'committed_short_plan')
        self.assertFalse(cert['authorized']);self.assertIn('net_state_recurrence_requires_fresh_decision',cert['reasons'])
        self.assertEqual(s.dispatch([{'actions':['enter corridor']}],None)[0],'enter corridor')
    def test_dark_remembered_pickup_requires_fresh_decision(self):
        s=Ledger();s.advance(obs({}, {'part':1}));s.advance(obs(dark=True));s.new_task=False
        self.assertEqual(s.acquire('part',1,{'part':1}),'pick up part')
        cert,_=s.preparation_certificate('pick up part',None,'dependency_preparation')
        self.assertFalse(cert['authorized']);self.assertEqual(s.dispatch([{'actions':['pick up part']}],None)[0],'pick up part')
        self.assertFalse(s.world[s.location]['object_list_currently_observed'])
        self.assertFalse(s.last_visits[s.location]['visibility'])
    def test_observed_light_effect_is_warning_and_ingredient_is_preserved(self):
        for lamp,material in [('lamp','ore'),('beacon','wire')]:
            s=Ledger();s.advance(obs({lamp:1,material:1}));s.choose('drop '+lamp,'capacity tradeoff')
            s.advance(obs(feedback='I dropped '+lamp+'.',dark=True))
            self.assertFalse(s.visibility);self.assertEqual(s.world[s.location]['objects'][lamp],1)
            s.choose('pick up '+lamp,'restore');s.advance(obs({lamp:1,material:1},feedback='I picked up '+lamp+'.'))
            check=s.action_check('drop '+lamp)
            self.assertFalse(check['blockers'],check);self.assertTrue(any(w['kind']=='breaks_observed_visibility_support' for w in check['warnings']))
            self.assertEqual(s.free_hand({material:1}),'drop '+lamp)
            self.assertEqual(s.dispatch([{'actions':['drop '+lamp]}],None)[0],'drop '+lamp)
            cert,_=s.preparation_certificate('drop '+lamp,None,'dependency_preparation');self.assertFalse(cert['authorized'])
    def test_confirmed_hidden_pickup_updates_historical_ground_count(self):
        s=Ledger();s.advance(obs({}, {'part':2}));s.choose('pick up part','get')
        s.advance(obs(feedback='I picked up part.',dark=True))
        self.assertEqual(s.world[s.location]['objects']['part'],1);self.assertEqual(s.hands['part'],1)
        s.choose('pick up absent','probe');s.world[s.location]['objects']['absent']=1
        s.advance(obs(feedback='Cannot pick up absent, not found in current area.',dark=True))
        self.assertNotIn('absent',s.world[s.location]['objects'])
    def test_known_capability_failure_remains_hard_evidence(self):
        s=Ledger();s.advance(obs({'tool':1}));s.choose('equip tool','test')
        s.advance(obs({'tool':1},feedback='Cannot equip tool, it is not equippable.'))
        self.assertTrue(any(b['kind']=='observed_non_equippable' for b in s.action_check('equip tool')['blockers']))
    def test_known_locked_door_still_rejected(self):
        s=Ledger();s.advance(obs());s.choose('enter corridor','go');s.advance(obs(feedback='Cannot enter corridor, the door is locked.'))
        self.assertTrue(s.action_check('enter corridor')['blockers'])
    def test_visible_pickup_can_still_save_a_call(self):
        s=Ledger();s.advance(obs({}, {'part':1}));s.new_task=False;s.queue=['pick up part']
        local=s.local_action(None);self.assertEqual(local[0],'pick up part');self.assertTrue(local[2]['certificate']['authorized'])

if __name__=='__main__':unittest.main(verbosity=2)
