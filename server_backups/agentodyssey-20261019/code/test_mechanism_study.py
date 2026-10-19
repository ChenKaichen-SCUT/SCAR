"""Offline acceptance. No paid API calls, no outcome-selected game reruns."""
import json,unittest,copy
from pathlib import Path
from test_feedback_v3 import obs,goal
from feedback_v3_core import Ledger as V3
from feedback_v4_core import Ledger as V4
from mechanism_study_core import StudyLedger

class StudyTests(unittest.TestCase):
    def test_full_reference_equivalence_on_frozen_observations(self):
        fixtures=json.loads((Path(__file__).parent/'study_validation_cases.json').read_text(encoding='utf-8'))
        for game,rows in fixtures['traces'].items():
            a,b=V3(),StudyLedger(set())
            for row in rows:
                for s in [a,b]:s.advance(row['observation']['text'])
                self.assertEqual(a.packet(),b.packet(),(game,row['step']))
                self.assertEqual(a.action_check(row['action']),b.action_check(row['action']))
                for s in [a,b]:s.choose(row['action'],'identical frozen public action')

    def test_each_ablation_changes_its_component(self):
        a=StudyLedger(set());a.advance(obs({'ore':1},feedback='It can be used to craft: device (2 ore)',near={'ore':1}));gid=goal(a);a.install_objective('craft 1 device',gid)
        b=copy.deepcopy(a);b.disabled={'joint_checks'}
        self.assertTrue(a.action_check('craft 1 device')['blockers']);self.assertFalse(b.action_check('craft 1 device')['blockers'])
        b=copy.deepcopy(a);b.disabled={'dependency_execution'}
        self.assertEqual(a.dispatch([{'actions':['inspect ore']}],gid)[0],'pick up ore')
        self.assertEqual(b.dispatch([{'actions':['inspect ore']}],gid)[0],'inspect ore');self.assertEqual(b.queue,[])
        a=StudyLedger(set());a.advance(obs());a.choose('enter corridor','try');a.advance(obs(feedback='Cannot enter corridor, the door is locked.'))
        b=copy.deepcopy(a);b.disabled={'hard_repeat'}
        self.assertTrue(a.action_check('enter corridor')['blockers']);self.assertFalse(b.action_check('enter corridor')['blockers'])
        a.test_specs['probe']={'id':'probe','created_step':a.step,'test_action':'wait','preconditions':[{'kind':'visible'}],'expected':[{'kind':'visible'}]}
        b=copy.deepcopy(a);b.disabled={'hypothesis'}
        a.choose('wait','test',test_id='probe');b.choose('wait','test',test_id='probe')
        self.assertIsNotNone(a.pending['test_spec']);self.assertIsNone(b.pending['test_spec']);self.assertNotIn('hypotheses',b.packet())

    def test_unreported_inventory_never_implies_zero_capacity(self):
        s=V4(set());s.advance(obs(dark=True));s.choose('pick up fruit','try');s.advance(obs(dark=True,feedback='Cannot pick up fruit, not enough space in hand.'))
        self.assertIsNone(s.hand_limit);self.assertEqual(s.evaluate_predicate({'kind':'held','object':'tool'}),'unknown')
        s.advance(obs(feedback='I revived at the starting point with full health.'))
        self.assertFalse(s.action_check('pick up tool')['blockers']);self.assertEqual(s.life_generation,1)

    def test_capacity_scope_and_revocation(self):
        s=V4(set());s.advance(obs({'a':1,'b':1}));s.choose('pick up c','try');s.advance(obs({'a':1,'b':1},feedback='Cannot pick up c, not enough space in hand.'))
        self.assertTrue(s.capacity_applies('pick up c'));self.assertFalse(s.capacity_applies('pick up tiny'))
        s.advance(obs({'a':1,'b':1},loc='Workshop, other'));self.assertIsNone(s.hand_limit)
        s.advance(obs());self.assertFalse(s.action_check('pick up c')['blockers'])

    def test_successful_return_allowed_failed_door_still_blocked(self):
        s=V4(set())
        for _ in range(3):
            s.advance(obs(loc='Workshop, darkroom',dark=True));s.choose('enter corridor','retreat');s.advance(obs(loc='Workshop, corridor',feedback='I entered corridor.'))
        s.advance(obs(loc='Workshop, darkroom',dark=True));self.assertFalse(s.action_check('enter corridor')['blockers'])
        s.choose('enter cellar','try');s.advance(obs(loc='Workshop, darkroom',dark=True,feedback='Cannot enter cellar, the door is locked.'))
        self.assertTrue(s.action_check('enter cellar')['blockers'])

    def test_unchanged_inspection_not_reenabled(self):
        s=V4(set());s.advance(obs());s.choose('inspect ore','look');s.advance(obs(feedback='I inspected ore.'))
        self.assertTrue(s.action_check('inspect ore')['blockers'])

    def test_non_equippable_objective_revises_and_rewrite_releases(self):
        s=V4(set());s.advance(obs({'tool':1}));gid=goal(s,'Arm yourself.');s.install_objective('equip tool',gid)
        s.choose('equip tool','try',gid);s.advance(obs({'tool':1},feedback='Cannot equip tool, it is not equippable.'))
        self.assertEqual(s.objective['status'],'contradicted_by_observation');self.assertTrue(s.action_check('equip tool')['blockers'])
        self.assertTrue(s.install_objective('pick up weapon',gid));self.assertFalse(s.install_objective('inspect workbench',gid))
        s.advance(obs({'tool':1},feedback='THE LAWS REWRITE THEMSELVES'));self.assertNotIn('tool',s.negative_capabilities)

    def test_hazard_invalidates_old_queue_and_allows_fresh_retreat(self):
        s=V4(set());s.advance(obs());gid=goal(s);s.queue=['craft 1 device']
        s.advance(obs(feedback='I was attacked by enemy and lost 8 HP.',dark=True));self.assertFalse(s.queue)
        self.assertEqual(s.dispatch([{'actions':['enter corridor']}],gid)[0],'enter corridor')

    def test_unknown_prerequisites_are_not_false_hard_absence(self):
        s=V4(set());s.advance(obs(feedback='It can be used to craft: device (2 ore)'));s.advance(obs(dark=True))
        c=s.action_check('craft 1 device');self.assertFalse(c['blockers']);self.assertTrue(c['unknown'])

    def test_parameter_guard_survives_and_rejects_bad_commitment(self):
        s=V4(set());s.advance(obs(feedback='guide says: Main goal: Record.\nCurrent tasks:\n[1] Record the cipher phrase on a sheet.\nThe cipher phrase is SILVER-DAWN.'));gid=next(iter(s.tasks))
        self.assertTrue(s.action_check('write WRONG-PHRASE sheet',gid)['blockers']);self.assertFalse(s.install_objective('write WRONG-PHRASE sheet',gid))
        self.assertTrue(s.install_objective('write SILVER-DAWN sheet',gid))

    def test_remnant_frozen_zero_capacity_failure_removed(self):
        rows=json.loads((Path(__file__).parent/'study_validation_cases.json').read_text(encoding='utf-8'))['traces']['remnant']
        old,new=V3(),V4(set())
        for row in rows:
            for s in [old,new]:s.advance(row['observation']['text'])
            if row['step']==154:
                self.assertEqual(old.hand_limit['count'],0);self.assertIsNone(new.hand_limit)
                self.assertTrue(any(x['kind']=='observed_hand_capacity' for x in old.action_check('pick up tension_wrench')['blockers']))
                self.assertFalse(any(x['kind']=='observed_hand_capacity' for x in new.action_check('pick up tension_wrench')['blockers']))
                self.assertIn('tension_wrench',new.negative_capabilities)
            for s in [old,new]:s.choose(row['action'],'frozen historical action')

if __name__=='__main__':unittest.main(verbosity=2)
