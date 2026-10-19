"""Paired scope/negative controls; no provider calls or hidden game data."""
import copy,json,socket,unittest
from pathlib import Path
from unittest.mock import patch
from feedback_v3r4_core import Ledger as Baseline
from feedback_v3r5_core import Ledger,NO_RESOURCE_PROGRESS
from test_feedback_v3r4 import SCHEMAS
from test_feedback_v3r import obs

def make(cls=Ledger,ore='ore',enemy='creature',hp=40,threat=True):
    s=cls();s.schemas=SCHEMAS
    fb=(f'I was attacked by {enemy} and lost 5 HP.\n' if threat else '')+f'My health is at {hp}.\nI see {enemy} nearby.'
    s.advance(obs({ore:1},{'food':5},feedback=fb));s.add_task('Assemble the requested device.','public task','main');s.focus=next(iter(s.tasks));s.new_task=False
    s.recipes['device']={'ingredients':{ore:1,'wire':1},'evidence':s.ref('public recipe')};s.install_objective('craft 1 device',s.focus)
    return s

def stale_parent_failure(s,a):
    s.failed_plans[s._plan_key([a])]={'step':s.step,'reason':[NO_RESOURCE_PROGRESS]}

class EmergencyTests(unittest.TestCase):
    def test_same_snapshot_old_rejects_new_allows_qualified_attack(self):
        old=make(Baseline);stale_parent_failure(old,'attack creature');new=copy.deepcopy(old);new.__class__=Ledger;new.init_emergency_fields();new.observe_threats(new.observations[new.step],new.location,new.life)
        self.assertTrue(old.gate(['attack creature'],old.focus,'test')[0]['blockers'])
        self.assertFalse(new.gate(['attack creature'],new.focus,'test')[0]['blockers'])
        self.assertEqual(old.failed_plans,new.failed_plans)
    def test_actual_damage_is_progress_without_reducing_material_deficit(self):
        s=make();before=copy.deepcopy(s.contract);s.contract['seen'][s.relevant_context()]=2;seen=copy.deepcopy(s.contract['seen'])
        s._select_plan(['attack creature'],s.focus,'test');s.choose('attack creature','combat',s.focus)
        s.advance(obs({'ore':1},{'food':5},feedback='I attacked creature for 4 damage. creature has 16 HP remaining.\nI was attacked by creature and lost 7 HP.\nMy health is at 33.\nI see creature nearby.'))
        self.assertEqual(s.emergency_progress[-1]['effect_amount'],4);self.assertEqual(s.emergency_progress[-1]['status'],'effect_observed')
        self.assertEqual(s.contract['seen'],seen);self.assertEqual(s.contract['action'],before['action']);self.assertEqual(s.contract['status'],'active')
        self.assertFalse(s.gate(['attack creature'],s.focus,'test')[0]['blockers'])
    def test_healing_effect_and_net_health_are_distinct(self):
        s=make(hp=15);s.choose('eat food','recover',s.focus)
        s.advance(obs({'ore':1},{'food':4},feedback='I ate food from ground and restored 10 HP (HP: 25/100).\nI was attacked by creature and lost 11 HP.\nMy health is at 14.\nI see creature nearby.'))
        r=s.emergency_progress[-1];self.assertEqual((r['effect_amount'],r['net_health_change']),(10,-1));self.assertTrue(r['losing_health_despite_healing'])
        stale_parent_failure(s,'eat food');c,_=s.gate(['eat food'],s.focus,'test');self.assertFalse(c['blockers']);self.assertIn('healing_effect_positive_but_net_health_not_improving',[x['kind'] for x in c['warnings']])
    def test_nominal_heal_at_full_health_is_not_progress(self):
        s=make(hp=100);s.observed_max_hp=100;s.choose('eat food','recover',s.focus)
        s.advance(obs({'ore':1},{'food':4},feedback='I ate food from ground and restored 10 HP (HP: 100/100).\nMy health is at 100.\nI see creature nearby.'))
        self.assertEqual(s.emergency_progress[-1]['status'],'no_effect_observed');self.assertEqual(s.emergency_progress[-1]['effect_amount'],0)
    def test_zero_damage_requires_reassessment_not_fabricated_progress(self):
        s=make();s.new_task=False
        for _ in range(2):
            s._select_plan(['attack creature'],s.focus,'test');s.choose('attack creature','try',s.focus)
            s.advance(obs({'ore':1},{'food':5},feedback='I attacked creature for 0 damage.\nMy health is at 40.\nI see creature nearby.'))
        s.committed=['attack creature'];self.assertIsNone(s.local_action(s.focus))
        c,_=s.gate(['attack creature'],s.focus,'test');self.assertIn('repeated_emergency_no_effect',[x['kind'] for x in c['warnings']])
        self.assertTrue(all(r['status']=='no_effect_observed' for r in s.emergency_progress))
    def test_unknown_feedback_is_not_positive_or_negative_evidence(self):
        s=make();s.choose('attack creature','try',s.focus);s.advance(obs({'ore':1},feedback='The scene changes.\nMy health is at 40.\nI see creature nearby.'))
        self.assertEqual(s.emergency_progress[-1]['status'],'unresolved')
    def test_environment_denial_remains_binding_for_attack_and_heal(self):
        for a,msg in [('attack creature','Cannot attack creature, no usable weapon.'),('eat food','Cannot eat food, not found.')]:
            with self.subTest(a=a):
                s=make();s.failed_plans[s._plan_key([a])]={'step':s.step,'reason':[msg]}
                c,_=s.gate([a],s.focus,'test');self.assertIn('same_failed_action_context',[b['kind'] for b in c['blockers']])
    def test_tool_and_capacity_checks_are_not_removed(self):
        s=make();s.held_tools['attack']={'object':'tool','step':s.step};stale_parent_failure(s,'attack creature')
        c,_=s.gate(['attack creature'],s.focus,'test');self.assertIn('observed_held_tool_missing',[x['kind'] for x in c['blockers']])
        s.capacity_observations[s._capacity_key()]={'count':1};s.nearby['wire']=1
        c,_=s.gate(['pick up wire'],s.focus,'test');self.assertIn('future_plan_conflict',[x['kind'] for x in c['blockers']])
    def test_reasoning_text_cannot_turn_material_transfer_into_emergency(self):
        s=make();stale_parent_failure(s,'drop ore');s.choose('drop ore','urgent emergency healing',s.focus)
        self.assertNotIn('emergency_scope',s.pending);self.assertTrue(s.gate(['drop ore'],s.focus,'test')[0]['blockers'])
    def test_attack_without_observed_threat_gets_no_exception(self):
        s=make(threat=False);stale_parent_failure(s,'attack creature');self.assertTrue(s.gate(['attack creature'],s.focus,'test')[0]['blockers'])
    def test_death_resets_scope_and_does_not_complete_emergency(self):
        s=make(hp=2);s.choose('eat food','recover',s.focus)
        s.advance(obs(feedback='I ate food from ground and restored 10 HP (HP: 12/100).\nI have died.\nI revived at the starting point with full health but lost all items in hand, equipped items, and inventory items at the place I died.\nMy health is at 100.'))
        self.assertEqual(s.emergency_progress[-1]['status'],'context_reset');self.assertIsNone(s.emergency_progress[-1]['effect_amount']);self.assertFalse(s.threats)
    def test_defeated_target_closes_combat_scope(self):
        s=make();s.choose('attack creature','combat',s.focus);s.advance(obs({'ore':1},feedback='I attacked creature for 4 damage and defeated creature!\nMy health is at 40.\nI see no one nearby.'))
        self.assertTrue(s.emergency_progress[-1]['scope_completed']);self.assertIsNone(s.emergency_scope('attack creature'));self.assertEqual(s.contract['action'],'craft 1 device')
    def test_health_changes_do_not_reset_material_loop_identity(self):
        s=make();key=s.relevant_context();s.hp=1;self.assertEqual(key,s.relevant_context());stale_parent_failure(s,'drop ore');s.hp=99
        self.assertTrue(s.gate(['drop ore'],s.focus,'test')[0]['blockers'])

class CarryCycleTests(unittest.TestCase):
    def test_useful_emergency_between_each_cycle_cannot_reset_transfer_history(self):
        results=[]
        for ore in ['ore','renamed_material']:
            for emergency in ['attack creature','eat food']:
                for kind in ['drop_pick','store_take']:
                    s=make(ore=ore);s.track_container('pouch');s.nearby['pouch']=1
                    actions=['drop '+ore,'pick up '+ore] if kind=='drop_pick' else ['store 1 '+ore+' pouch','take out '+ore+' pouch']
                    blocked=None;emergency_effects=0
                    for i in range(12):
                        if i%2==0:
                            self.assertIsNotNone(s._select_plan([emergency],s.focus,'test'))
                            s.choose(emergency,'observed emergency',s.focus)
                            fb='I attacked creature for 4 damage. creature has '+str(100-i)+' HP remaining.' if emergency.startswith('attack') else 'I ate food from ground and restored 10 HP (HP: 50/100).'
                            s.advance(obs({ore:1},{'pouch':1,'food':5},feedback=fb+'\nI was attacked by creature and lost 10 HP.\nMy health is at 40.\nI see creature nearby.'))
                            self.assertEqual(s.emergency_progress[-1]['status'],'effect_observed');emergency_effects+=1
                        a=actions[i%2];c,_=s.gate([a],s.focus,'test')
                        if c['blockers']:blocked=i+1;break
                        self.assertIsNotNone(s._select_plan([a],s.focus,'test'));s.choose(a,'transfer',s.focus)
                        holding=i%2==1;hands={ore:1} if holding else {};ground={'pouch':1,'food':5}
                        if kind=='drop_pick':
                            if not holding:ground[ore]=1
                            fb=f'I picked up {ore}.' if holding else f'I dropped {ore}.'
                        else:fb=f'I took out {ore} from pouch.' if holding else f'I stored 1 {ore} in pouch.'
                        s.advance(obs(hands,ground,feedback=fb+'\nMy health is at 40.\nI see creature nearby.'))
                    self.assertIsNotNone(blocked,(ore,emergency,kind));self.assertLessEqual(blocked,7)
                    results.append({'item':ore,'kind':kind,'interleaved_emergency':emergency,'transfer_number_blocked':blocked,'useful_emergency_actions':emergency_effects})
        CarryCycleTests.interleaved_results=results

    def test_renamed_transfer_cycles_match_old_detection_with_and_without_interrupt(self):
        results=[]
        for ore in ['ore','sample','material_c','piece_7']:
            for kind in ['drop_pick','store_take']:
                for interrupt in [False,True]:
                    cells=[]
                    for cls in [Baseline,Ledger]:
                        s=make(cls,ore=ore);s.track_container('pouch');s.nearby['pouch']=1
                        actions=['drop '+ore,'pick up '+ore] if kind=='drop_pick' else ['store 1 '+ore+' pouch','take out '+ore+' pouch']
                        if interrupt:
                            s._select_plan(['attack creature'],s.focus,'test');s.choose('attack creature','combat',s.focus)
                            s.advance(obs({ore:1},{'pouch':1},feedback='I attacked creature for 4 damage. creature has 20 HP remaining.\nMy health is at 35.\nI see creature nearby.'))
                        blocked=None
                        for i in range(12):
                            a=actions[i%2];c,_=s.gate([a],s.focus,'test')
                            if c['blockers']:
                                blocked={'transfer_number':i+1,'kinds':sorted(b['kind'] for b in c['blockers'])};break
                            s._select_plan([a],s.focus,'test');s.choose(a,'move',s.focus)
                            holding=i%2==1;hands={ore:1} if holding else {};ground={'pouch':1}
                            if kind=='drop_pick':
                                if not holding:ground[ore]=1
                                fb=f'I picked up {ore}.' if holding else f'I dropped {ore}.'
                            else:fb=f'I took out {ore} from pouch.' if holding else f'I stored 1 {ore} in pouch.'
                            s.advance(obs(hands,ground,feedback=fb+f'\nMy health is at {35-i}.\nI see creature nearby.'))
                        self.assertIsNotNone(blocked,(ore,kind,interrupt,cls));cells.append(blocked)
                    # A useful emergency action must not count as an extra
                    # failed material visit. After three complete two-action
                    # cycles, the seventh transfer proposal must be stopped.
                    self.assertLessEqual(cells[1]['transfer_number'],7,(ore,kind,interrupt,cells))
                    if not interrupt:self.assertEqual(cells[0],cells[1])
                    results.append({'item':ore,'kind':kind,'after_interrupt':interrupt,'old':cells[0],'candidate':cells[1]})
        self.assertEqual(len(results),16);CarryCycleTests.results=results

if __name__=='__main__':
    with patch.object(socket.socket,'connect',side_effect=AssertionError('No network allowed')):unittest.main(verbosity=2)
