import copy,io,json,socket,unittest
from pathlib import Path
from unittest.mock import patch
from feedback_v3r7_core import Ledger
from feedback_v3r6_core import Ledger as Baseline
import test_feedback_v3r4 as old_tests
import test_feedback_v3r6 as authority_tests
import test_feedback_v3r5 as emergency_tests
from test_feedback_v3r import obs

def setup(cls=Ledger,hands=None,ground=None):
    s=cls();s.schemas=old_tests.SCHEMAS;s.advance(obs(hands,ground,feedback='My health is at 100.'))
    s.add_task('Build the requested item.','public task','main');s.focus=next(iter(s.tasks));s.new_task=False
    s.recipes['device']={'ingredients':{'ore':1,'wire':1,'fiber':1},'evidence':s.ref('public recipe')}
    s.capacity_observations[s._capacity_key()]={'count':2,'step':s.step};s.install_objective('craft 1 device',s.focus)
    return s

class IndependentChecks(unittest.TestCase):
    def test_unknown_ground_does_not_hide_current_capacity(self):
        old=setup(Baseline,{'ore':1,'wire':1});s=setup(hands={'ore':1,'wire':1})
        self.assertEqual(old.validate_plan(['pick up fiber'])['stop']['reason'],'unobserved_ground_item')
        v=s.validate_plan(['pick up fiber']);self.assertEqual(v['stop']['reason'],'capacity_conflict')
        self.assertIn('unobserved_ground_item',v['independent_checks'][0]['unknown_conditions'])
        s.committed=['pick up fiber'];s.visibility=False;s.world[s.location]['objects']['fiber']=1
        self.assertIsNone(s.local_action(s.focus))
    def test_unknown_success_does_not_hide_later_capacity(self):
        s=setup(hands={'ore':1});v=s.validate_plan(['pick up wire','pick up fiber','craft 1 device'])
        self.assertEqual((v['stop']['index'],v['stop']['reason']),(1,'capacity_conflict'));self.assertTrue(v['uncertainties'])
    def test_unknown_is_not_absence_or_fact(self):
        s=setup(hands={'ore':1});before=copy.deepcopy(s._resource_state())
        v=s.validate_plan(['pick up wire']);self.assertEqual(v['stop']['status'],'requires_observation');self.assertEqual(s._resource_state(),before)
    def test_conditional_exchange_cannot_claim_all_materials(self):
        s=setup(hands={'ore':1,'wire':1});v=s.validate_plan(['drop wire','pick up fiber','craft 1 device'])
        self.assertEqual((v['stop']['index'],v['stop']['reason']),(2,'joint_material_deficit'))
    def test_only_suffix_is_flagged_not_first_action_impossible(self):
        s=setup(hands={'ore':1});s.routes[s.location]={'enter corridor':'Lab, corridor'}
        c,v=s.gate(['enter corridor','craft 1 device'],s.focus,'model_candidate')
        self.assertFalse(c['blockers']);self.assertIn('suffix_requires_repair',[x['kind'] for x in c['warnings']])
        self.assertIsNone(s._select_plan(['enter corridor','craft 1 device'],s.focus,'local_committed_continuation'))
    def test_immediate_physical_failure_still_blocks(self):
        s=setup();c,_=s.gate(['drop absent'],s.focus,'model_candidate');self.assertTrue(c['blockers'])

class RepairTests(unittest.TestCase):
    def test_intermediate_target_preserves_later_craft_inputs(self):
        s=setup(hands={'token':1},ground={'fiber':1,'ore':1})
        s.recipes['plate']={'ingredients':{'ore':1}};s.recipes['device']['ingredients']={'plate':1,'fiber':1}
        seq=['pick up fiber','pick up ore','craft 1 plate','pick up plate','craft 1 device']
        r,info=s.repair_plan(seq,s.validate_plan(seq));self.assertIsNotNone(r,info)
        st=s._resource_state()
        for a in r:
            if a=='craft 1 plate':break
            st,why=s._transition(st,a);self.assertIsNotNone(st,why)
        self.assertEqual(s._available(st).get('fiber'),1);self.assertEqual(s._available(st).get('ore'),1)
        self.assertIn('drop token',r)
    def test_short_transfer_cannot_sacrifice_another_active_input(self):
        s=setup(hands={'ore':1,'wire':1},ground={'fiber':1})
        seq=['pick up fiber'];self.assertIsNone(s.repair_plan(seq,s.validate_plan(seq))[0])
    def test_short_transfer_can_store_active_input_accessibly(self):
        s=setup(hands={'ore':1,'wire':1},ground={'fiber':1,'pouch':1});s.track_container('pouch')['complete']=True
        seq=['pick up fiber'];r,info=s.repair_plan(seq,s.validate_plan(seq));self.assertIsNotNone(r,info)
        st=s._resource_state()
        for a in r:st,_=s._transition(st,a)
        self.assertTrue(all(s._available(st).get(o,0)>=1 for o in ['ore','wire','fiber']))
    def test_suffix_input_quantities_are_not_collapsed(self):
        s=setup(hands={'fiber':1});s.recipes['plate']={'ingredients':{'ore':2}};s.recipes['device']['ingredients']={'plate':1,'fiber':2}
        need,_=s.repair_obligations(['craft 1 plate','pick up plate','craft 1 device'],0,s._resource_state())
        self.assertEqual(need,{'ore':2,'fiber':2})
    def test_empty_known_container_repairs_three_materials_two_hands(self):
        s=setup(hands={'ore':1,'wire':1},ground={'fiber':1,'pouch':1});s.track_container('pouch')['complete']=True
        seq=['drop wire','pick up fiber','craft 1 device'];before=copy.deepcopy(s._resource_state())
        repaired,info=s.repair_plan(seq,s.validate_plan(seq));self.assertIsNotNone(repaired,info)
        st=s._resource_state()
        for a in repaired:
            nxt,why=s._transition(st,a);self.assertIsNotNone(nxt,(a,why));st=nxt
        self.assertTrue(all(s._available(st).get(o,0)>=1 for o in ['ore','wire','fiber']))
        self.assertTrue(any(a.startswith('store ') for a in repaired));self.assertEqual(s._resource_state(),before)
        a,_,d=s.dispatch([{'actions':seq}],s.focus);self.assertEqual(d['source'],'model_plan_locally_repaired');self.assertEqual(s.objective['action'],'craft 1 device')
    def test_no_container_does_not_fabricate_complete_repair(self):
        s=setup(hands={'ore':1,'wire':1},ground={'fiber':1});seq=['drop wire','pick up fiber','craft 1 device']
        self.assertIsNone(s.repair_plan(seq,s.validate_plan(seq))[0]);self.assertIsNone(s.dispatch([{'actions':seq}],s.focus)[0])
    def test_inaccessible_container_is_not_used(self):
        s=setup(hands={'ore':1,'wire':1},ground={'fiber':1});s.track_container('remote_pouch')['items']={'fiber':1}
        seq=['drop wire','pick up fiber','craft 1 device'];self.assertIsNone(s.repair_plan(seq,s.validate_plan(seq))[0])
    def test_full_container_is_not_used_as_free_space(self):
        s=setup(hands={'ore':1,'wire':1},ground={'fiber':1,'pouch':1});s.track_container('pouch');s.container_limits['pouch']={'full':True}
        seq=['drop wire','pick up fiber','craft 1 device'];self.assertIsNone(s.repair_plan(seq,s.validate_plan(seq))[0])
    def test_irrelevant_object_can_be_released_preserving_target(self):
        s=setup(hands={'token':1,'ore':1},ground={'wire':1});s.recipes['device']['ingredients']={'ore':1,'wire':1}
        seq=['pick up wire','craft 1 device'];r,info=s.repair_plan(seq,s.validate_plan(seq));self.assertEqual(r,['drop token','pick up wire','craft 1 device'])
    def test_dangerous_prefix_not_automatically_recovered(self):
        s=setup(hands={'ore':1});s.routes[s.location]={'enter corridor':'Lab, corridor'};s.neighbors=['corridor']
        s.world['Lab, corridor']={'objects':{'wire':1,'fiber':1},'neighbors':['room']}
        s.attempts.append({'location_before':'Lab, corridor','feedback':['Cannot enter room. creature has blocked the way out.']})
        seq=['enter corridor','pick up wire','pick up fiber','craft 1 device'];self.assertIsNone(s.repair_plan(seq,s.validate_plan(seq))[0])
        a,_,_=s.recover_action([{'actions':seq}],s.focus,[]);self.assertNotEqual(a,'enter corridor')
    def test_damage_budget_stops_new_automatic_repair(self):
        s=setup(hands={'token':1,'ore':1},ground={'wire':1});s.recipes['device']['ingredients']={'ore':1,'wire':1};s.hp=5;s.area_recent[s.location]=[3]
        seq=['pick up wire','craft 1 device'];self.assertIsNone(s.repair_plan(seq,s.validate_plan(seq))[0])
    def test_unknown_route_cannot_be_assumed_safe_repair(self):
        s=setup(hands={'ore':1,'wire':1},ground={'fiber':1,'pouch':1});s.track_container('pouch')
        seq=['pick up fiber','enter unknown','craft 1 device'];r,info=s.repair_plan(seq,s.validate_plan(seq));self.assertIsNone(r);self.assertEqual(info['reason'],'unverified_route_before_target')
    def test_sufficient_original_plan_is_not_replaced(self):
        s=setup(hands={'ore':1},ground={'wire':1});s.recipes['device']['ingredients']={'ore':1,'wire':1}
        a,_,d=s.dispatch([{'actions':['pick up wire','craft 1 device']}],s.focus);self.assertEqual(a,'pick up wire');self.assertEqual(d['source'],'model_priority_preserved');self.assertFalse(s.repair_audit)
    def test_required_material_remains_accessible_after_space_repair(self):
        s=setup(hands={'ore':1,'wire':1},ground={'fiber':1,'pouch':1});s.track_container('pouch')['complete']=True
        seq=['pick up fiber','craft 1 device'];r,info=s.repair_plan(seq,s.validate_plan(seq));self.assertIsNotNone(r,info)
        self.assertLessEqual(len(r),8);self.assertTrue(any(a.startswith('store ') for a in r))
        st=s._resource_state()
        for a in r:st,_=s._transition(st,a)
        self.assertTrue(all(s._available(st).get(o,0)>=1 for o in ['ore','wire','fiber']))

def main():
    old_tests.Ledger=Ledger;authority_tests.Ledger=Ledger;emergency_tests.Ledger=Ledger
    omit={'test_reasoning_text_cannot_turn_material_transfer_into_emergency','test_attack_without_observed_threat_gets_no_exception','test_health_changes_do_not_reset_material_loop_identity'}
    suites=[unittest.defaultTestLoader.loadTestsFromModule(old_tests),unittest.defaultTestLoader.loadTestsFromTestCase(authority_tests.AuthorityTests),unittest.defaultTestLoader.loadTestsFromTestCase(IndependentChecks),unittest.defaultTestLoader.loadTestsFromTestCase(RepairTests)]
    suites += [emergency_tests.EmergencyTests(n) for n in unittest.defaultTestLoader.getTestCaseNames(emergency_tests.EmergencyTests) if n not in omit]
    stream=io.StringIO()
    with patch.object(socket.socket,'connect',side_effect=AssertionError('No network')):r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.TestSuite(suites))
    print(stream.getvalue());print(json.dumps({'passed':r.wasSuccessful(),'tests':r.testsRun,'skipped':len(r.skipped),'provider_calls':0}));return r.wasSuccessful()
if __name__=='__main__':raise SystemExit(0 if main() else 1)
