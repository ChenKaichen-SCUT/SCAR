import json,unittest
from pathlib import Path
from feedback_v3r_core import Ledger

def obs(hands=None,ground=None,feedback='',loc='Lab, room',dark=False):
    fmt=lambda d:', '.join(f'{n} {o}' for o,n in (d or {}).items() if n) or 'no objects'
    text=f'Current Location: {loc}\n{feedback}\n'
    if dark:text+='It is too dark to see anything here.\n'
    else:text+=f'I am holding {fmt(hands)}.\nI have equipped no objects.\nI see {fmt(ground)} near me.\n'
    return text+'Neighboring areas: corridor.\n'
class CoreTests(unittest.TestCase):
    def test_hidden_inventory_updates_from_confirmed_transfers(self):
        s=Ledger();s.advance(obs({'ore':1}));s.choose('pick up ore','get')
        s.advance(obs(feedback='I picked up ore.',dark=True));self.assertEqual(s.hands,{'ore':2});self.assertTrue(s.hands_known)
        s.choose('drop ore','release');s.advance(obs(feedback='I dropped ore.',dark=True));self.assertEqual(s.hands,{'ore':1})
    def test_capacity_unknown_cannot_be_zero_and_death_invalidates(self):
        s=Ledger();s.advance(obs(dark=True));s.choose('pick up ore','try');s.advance(obs(feedback='Cannot pick up ore, not enough space in hand.',dark=True))
        self.assertIsNone(s.hand_limit)
        s.advance(obs({'ore':2}));s.choose('pick up wire','get');s.advance(obs({'ore':2},feedback='Cannot pick up wire, not enough space in hand.'))
        self.assertTrue(s.capacity_applies('pick up wire'));self.assertFalse(s.capacity_applies('pick up other'))
        s.choose('wait','wait');s.advance(obs(feedback='I have died.\nI revived at the starting point with full health but lost all items in hand, equipped items, and inventory items at the place I died.'))
        self.assertIsNone(s.hand_limit);self.assertFalse(s.action_check('pick up wire')['blockers']);self.assertEqual(s.hands,{})
    def test_successful_return_never_permanently_banned(self):
        s=Ledger();s.advance(obs())
        for _ in range(5):s.choose('enter corridor','travel');s.advance(obs(feedback='I entered corridor.'))
        self.assertFalse(s.action_check('enter corridor')['blockers'])
    def test_known_failed_door_still_rejected(self):
        s=Ledger();s.advance(obs());s.choose('enter corridor','travel');s.advance(obs(feedback='Cannot enter corridor, the door is locked.'))
        self.assertTrue(s.action_check('enter corridor')['blockers'])
    def test_protect_enabler_and_free_different_item(self):
        for lamp,resource in [('lamp','ore'),('beacon','wire')]:
            s=Ledger();s.advance(obs({lamp:1,resource:1}));s.choose('drop '+lamp,'release');s.advance(obs(feedback='I dropped '+lamp+'.',dark=True))
            s.choose('pick up '+lamp,'restore');s.advance(obs({lamp:1,resource:1},feedback='I picked up '+lamp+'.'))
            self.assertIn(lamp,s.protected_items());self.assertEqual(s.free_hand(),'drop '+resource)
            self.assertTrue(s.action_check('store 1 '+lamp+' pouch')['blockers'])
    def test_non_equippable_not_retried_and_malformed_hypothesis_ignored(self):
        s=Ledger();s.advance(obs({'tool':1}));s.choose('equip tool','try');s.advance(obs({'tool':1},feedback='Cannot equip tool, it is not equippable.'))
        self.assertTrue(s.action_check('equip tool')['blockers'])
        s.apply_review({'hypotheses':[{'preconditions':[],'expected':'informal prose'}]});self.assertEqual(s.test_specs,{})
    def test_rejected_candidates_recover_without_wait_or_exception(self):
        s=Ledger();s.schemas=[('enter',['area_name']),('pick up',['object_name']),('wait',[])];s.advance(obs())
        action,check,record=s.recover_action([{'actions':['illegal spell']}],None,[])
        self.assertEqual(action,'enter corridor');self.assertEqual(record['source'],'local_recovery_after_rejected_batch')
    def test_dark_crafting_consumes_known_ingredients(self):
        s=Ledger();s.advance(obs({'ore':2},feedback='It can be used to craft: bar (2 ore)'));s.choose('craft 1 bar','make')
        s.advance(obs(feedback='I successfully crafted 1 bar. It is now on the ground.',dark=True))
        self.assertEqual(s.hands,{});self.assertTrue(s.hands_known)

if __name__=='__main__':unittest.main(verbosity=2)
