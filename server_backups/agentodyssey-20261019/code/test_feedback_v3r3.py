import copy,json,unittest
from pathlib import Path
from feedback_v3r3_core import Ledger
from feedback_v2_core import compact
from test_feedback_v3r import obs

SCHEMAS=[('drop',['object']),('take out',['object','container']),('store',['amount','object','container']),('eat',['object']),('defend',[]),('wait',[]),('enter',['area']),('equip',['object']),('unequip',['object']),('inspect',['object']),('pick up',['object']),('craft',['amount','object']),('lockpick',['area']),('attack',['target'])]

def setup(hands=None,ground=None):
    s=Ledger();s.schemas=SCHEMAS;s.advance(obs(hands,ground));s.add_task('Deliver the requested device.','public task','main');s.focus=next(iter(s.tasks));s.new_task=False
    return s

class CompletionTests(unittest.TestCase):
    def test_supported_success_is_finite_but_not_main_completion(self):
        pairs=[('drop coin','I dropped coin.'),('take out coin pouch','I took out coin from pouch.'),('eat apple','I ate apple from ground and restored 10 HP (HP: 21/100).'),('defend','I am defending.'),('store 1 coin pouch','I stored 1 coin in pouch.'),('wait','I waited for a while.')]
        for a,fb in pairs:
            with self.subTest(action=a):
                s=setup({'coin':1});s.track_container('pouch')['items']={'coin':1}
                self.assertTrue(s.install_objective(a,s.focus));s.choose(a,'one operation',s.focus)
                s.advance(obs(feedback=fb+'\nMy health is at 5.\nI lost 15 HP.'))
                self.assertEqual(s.objective['status'],'effect_observed');self.assertEqual(s.tasks[s.focus]['status'],'open')
                self.assertEqual(len(s.objective_completions),1);self.assertFalse(s.objective_completions[0]['main_task_completed'])
                s.choose('wait','later');s.advance(obs(feedback='I waited for a while.'))
                self.assertEqual(len(s.objective_completions),1)
    def test_denial_wrong_object_and_stale_success_do_not_complete(self):
        for fb in ['Cannot drop coin, not held.','I dropped rock.','Nothing happened.']:
            s=setup({'coin':1});s.install_objective('drop coin',s.focus);s.choose('drop coin','release');s.advance(obs({'coin':1},feedback=fb))
            self.assertEqual(s.objective['status'],'active');self.assertFalse(s.objective_completions)
        s=setup();s.choose('defend','guard');s.advance(obs(feedback='I am defending.'))
        s.install_objective('defend',s.focus);self.assertEqual(s.objective['status'],'active')
        s.choose('defend','guard again');s.advance(obs(feedback='I am defending.'));self.assertEqual(len(s.objective_completions),1)
    def test_unsupported_goal_is_rejected_not_permanently_active(self):
        s=setup();self.assertFalse(s.install_objective('attack monster',s.focus));self.assertIsNone(s.objective)
    def test_preparation_preserves_terminal_contract(self):
        s=setup();s.recipes['device']={'ingredients':{'ore':1}};s.install_objective('craft 1 device',s.focus)
        self.assertFalse(s.install_objective('drop coin',s.focus));self.assertEqual(s.objective['action'],'craft 1 device')

class PlanAndProbeTests(unittest.TestCase):
    def prepared(self):
        s=setup({'pouch':1,'ore':1});s.track_container('pouch')['items']={'wire':1,'bar':1}
        s.recipes['device']={'ingredients':{'ore':1,'wire':1,'bar':1},'evidence':{'step':1,'quote':'observed recipe'}};s.install_objective('craft 1 device',s.focus)
        return s
    def test_accessible_ingredients_trigger_trial_not_unpacking(self):
        s=self.prepared();local=s.local_action(s.focus)
        self.assertIsNotNone(local);self.assertEqual(local[0],'craft 1 device');self.assertEqual(local[2]['source'],'local_discriminating_probe')
        s.choose(local[0],'resolve material access');s.advance(obs({'pouch':1,'ore':1},feedback='Cannot craft device. Missing necessary workbench in the current area.'))
        self.assertEqual(s.probe_results[-1]['outcome'],'indeterminate_other_precondition')
        self.assertFalse(any(e.get('support')=='supported_in_context' for e in s.operation_evidence.values()))
        self.assertIsNone(s.diagnostic_action(s.focus))
    def test_supported_probe_closes_goal(self):
        s=self.prepared();a=s.local_action(s.focus)[0];s.choose(a,'probe');s.advance(obs({}, {'device':1},feedback='I successfully crafted 1 device. It is now on the ground.'))
        self.assertEqual(s.probe_results[-1]['outcome'],'supported_in_context');self.assertEqual(s.objective['status'],'effect_observed')
    def test_joint_check_catches_future_full_hand(self):
        s=setup({'pouch':1});s.track_container('pouch')['items']={'ore':1,'wire':1};s.capacity_observations[s._capacity_key()]={'count':2}
        v=s.validate_plan(['take out ore pouch','take out wire pouch'])
        self.assertEqual(v['validated_prefix'],1);self.assertEqual(v['stop']['reason'],'capacity_conflict')
        a,_,d=s.dispatch([{'actions':['take out ore pouch','take out wire pouch']},{'actions':['inspect pouch']}],s.focus)
        self.assertEqual(a,'inspect pouch');self.assertTrue(d['rejected'])
    def test_local_search_uses_container_instead_of_dropping_ingredients(self):
        s=setup({'pouch':1,'ore':1},{'wire':1,'bar':1});s.track_container('pouch')
        s.recipes['device']={'ingredients':{'ore':1,'wire':1,'bar':1},'evidence':{'step':1,'quote':'observed recipe'}};s.install_objective('craft 1 device',s.focus)
        s.capacity_observations[s._capacity_key()]={'count':2};seq=s.resource_plan('craft 1 device')
        self.assertIsNotNone(seq);self.assertLessEqual(len(seq),5);self.assertFalse(any(a in ['drop ore','drop wire','drop bar'] for a in seq))
        st=s._resource_state()
        for a in seq:st,why=s._transition(st,a);self.assertIsNotNone(st,a)
        self.assertTrue(all(s._available(st).get(o,0)>=1 for o in ['ore','wire','bar']))
    def test_expected_darkness_does_not_cancel_remembered_pickup(self):
        s=setup({'lamp':1,'ore':1},{'wire':1});s.committed=['drop lamp','pick up wire'];s.choose('drop lamp','free hand')
        s.advance(obs(feedback='I dropped lamp.',dark=True));s.new_task=False
        a=s.local_action(s.focus);self.assertIsNotNone(a);self.assertEqual(a[0],'pick up wire');self.assertEqual(a[2]['source'],'local_committed_probe')
    def test_risk_interrupt_keeps_parent_and_remaining_plan(self):
        s=self.prepared();s.hp=2;s.area_costs[s.location]={'damage':10,'visits':2,'noise':2};s.committed=['store 1 ore pouch']
        self.assertIsNone(s.local_action(s.focus));self.assertEqual(s.objective['action'],'craft 1 device');self.assertTrue(s.committed)
    def test_failed_strategy_reopens_only_after_relevant_change(self):
        s=self.prepared();seq=['store 1 ore pouch'];k=s._plan_key(seq);s.failed_plans[k]={'reason':['loop']}
        self.assertIsNone(s.dispatch([{'actions':seq}],s.focus)[0]);s.step+=1;self.assertEqual(k,s._plan_key(seq))
        s.hands['ore']=2;self.assertNotEqual(k,s._plan_key(seq));self.assertIsNotNone(s.dispatch([{'actions':seq}],s.focus)[0])
    def test_locked_edge_survives_irrelevant_changes_but_tool_allows_new_test(self):
        s=setup();s.choose('enter corridor','go');s.advance(obs(feedback='Cannot enter corridor, the door is locked.'))
        s.hands={'junk':1};self.assertTrue(any(b['kind']=='observed_locked_edge' for b in s.action_check('enter corridor')['blockers']))
        s.held_tools['lockpick']={'object':'tool'};s.hands={'tool':1};self.assertFalse(any(b['kind']=='observed_locked_edge' for b in s.action_check('enter corridor')['blockers']))
        s.install_objective('enter corridor',s.focus);self.assertEqual(s.work_action(),'lockpick corridor')
        s.hands={};s.nearby={'tool':1};s.recipes['tool']={'ingredients':{'ore':1}}
        self.assertEqual(s.work_action(),'pick up tool')
    def test_death_invalidates_plan_without_fabricating_completion(self):
        s=self.prepared();s.committed=['craft 1 device'];s.choose('wait','wait');s.advance(obs(feedback='I have died.\nI revived at the starting point with full health but lost all items in hand, equipped items, and inventory items at the place I died.'))
        self.assertFalse(s.committed);self.assertFalse(s.objective_completions);self.assertEqual(s.contract['status'],'requires_revalidation_after_loss')
    def test_frozen_public_observation_replay_no_counterfactual_reward(self):
        root=Path(__file__).parent/'results_feedback_v3r2_verified'
        files=list(root.rglob('agent_log.jsonl'))
        if not files:self.skipTest('Public trace unavailable; synthetic tests remain portable')
        rows=[json.loads(x) for x in files[0].read_text(encoding='utf8').splitlines()];s=Ledger();s.schemas=SCHEMAS
        for r in rows[:315]:
            s.advance(r['observation']['text']);s.choose(r['action'],'replay public executed action')
        # This checks parser state and a proposed intervention, not an alternative score.
        counts,_=s.accessible();self.assertTrue(s.recipes);self.assertTrue(counts)
        s.add_task('Open the next passage.','public test objective','main');goal=list(s.tasks)[-1]
        s.install_objective('craft 1 lockpick',goal);s.new_task=False
        proposal=s.diagnostic_action(goal)
        self.assertIsNotNone(proposal);self.assertEqual(proposal[0],'craft 1 lockpick')

if __name__=='__main__':unittest.main(verbosity=2)
