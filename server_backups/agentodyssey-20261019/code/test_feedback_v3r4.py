import copy,json,unittest
from pathlib import Path
from feedback_v3r4_core import Ledger
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

class StateControlTests(unittest.TestCase):
    def test_tutorial_finished_and_next_contact(self):
        s=Ledger();s.advance(obs(feedback='Required action: `enter corridor`'))
        s.choose('enter corridor','go');s.advance(obs(feedback='Tutorial Finished. You have exited to spawn.\nTalk to guide about what to do next.\nguide enters the area.'))
        self.assertFalse(any(t['scope']=='tutorial' and t['status']=='open' for t in s.tasks.values()))
        self.assertEqual(s.tasks[s.focus]['scope'],'main');self.assertEqual(s.pending_contact,'guide')
    def test_dialogue_narration_does_not_replace_main_task(self):
        s=Ledger();s.advance(obs(feedback='Tutorial Finished. You have exited to spawn.\nTalk to guide about what to do next.'))
        for tail in ['', '\nI was attacked by creature_0 and lost 2 HP.','\nSense of peacefulness sneaks in.','']:
            s.advance(obs(feedback='guide says: Find the missing traveler.'+tail))
            tasks=[t for t in s.tasks.values() if t['scope']=='main' and t['status']=='open']
            self.assertEqual([t['text'] for t in tasks],['Find the missing traveler.'])
        self.assertIsNone(s.pending_contact)
    def test_dialogue_retains_multiline_parameters_and_new_stage(self):
        s=Ledger();s.advance(obs(feedback='Talk to guide about what to do next.'))
        s.advance(obs(feedback='guide says: The target is within:\n  Region A; Region B\nSearch the named regions.\nI was attacked by creature and lost 2 HP.'))
        t=s.tasks[s.focus];self.assertIn('Region B',t['text']);self.assertNotIn('attacked',t['text'])
        s.advance(obs(feedback='Stage completed. A new route opens.\nTalk to guide about what to do next.'))
        self.assertEqual(t['status'],'observed_complete')
        s.advance(obs(feedback='guide says: Obtain a protective garment.'))
        self.assertEqual(s.tasks[s.focus]['text'],'Obtain a protective garment.')
    def test_newly_prepared_unknown_route_continues_without_another_model_call(self):
        s=setup();s.choose('enter corridor','test');s.advance(obs(feedback='Cannot enter corridor, the door is locked.'))
        s.install_objective('enter corridor',s.focus)
        s.committed=['pick up token','enter corridor'];s.choose('pick up token','prepare')
        s.advance(obs({'token':1},feedback='I picked up token.'));s.new_task=False
        local=s.local_action(s.focus);self.assertIsNotNone(local);self.assertEqual(local[0],'enter corridor')
        self.assertEqual(s.routes.get(s.location,{}),{})
    def test_tool_precondition_applies_to_all_sources(self):
        s=setup();s.choose('lockpick corridor','test');s.advance(obs(feedback='Cannot lockpick corridor. No probe_tool tool in hand.'))
        self.assertTrue(any(x['kind']=='observed_held_tool_missing' for x in s.action_check('lockpick corridor')['blockers']))
        s.committed=['lockpick corridor'];s.new_task=False;self.assertIsNone(s.local_action(s.focus))
        self.assertIsNone(s.dispatch([{'actions':['lockpick corridor']}],s.focus)[0])
        a,_,_=s.recover_action([{'actions':['lockpick corridor']}],s.focus,[]);self.assertNotEqual(a,'lockpick corridor')
        s.hands={'probe_tool':1};self.assertFalse(any(x['kind']=='observed_held_tool_missing' for x in s.action_check('lockpick corridor')['blockers']))
    def test_preferred_admissible_action_is_not_replaced_by_short_dialogue(self):
        s=setup({'probe_tool':1});s.schemas+=[('talk to',['npc'])];s.held_tools['lockpick']={'object':'probe_tool','step':1};s.area_recent[s.location]=[8,0,0];s.hp=80
        a,_,_=s.dispatch([{'actions':['lockpick corridor','enter corridor']},{'actions':['talk to guide']}],s.focus)
        self.assertEqual(a,'lockpick corridor')
    def test_failed_action_context_cannot_be_bypassed_with_a_new_suffix(self):
        s=setup({'ore':1});seq=['drop ore','inspect ore'];key=s._plan_key(seq);s.failed_plans[key]={'step':1,'reason':['loop']}
        self.assertEqual(key,s._plan_key(['drop ore','enter corridor']))
        self.assertIsNone(s.dispatch([{'actions':['drop ore','enter corridor']}],s.focus)[0])
        s.committed=['drop ore'];self.assertIsNone(s.local_action(s.focus))
        a,_,_=s.recover_action([{'actions':['drop ore']}],s.focus,[]);self.assertNotEqual(a,'drop ore')
    def test_no_automatic_reacquisition_after_deliberate_release(self):
        s=setup({'ore':1,'wire':1});s.recipes['device']={'ingredients':{'ore':1,'wire':1,'thread':1},'evidence':s.ref('public recipe')};s.install_objective('craft 1 device',s.focus)
        s.choose('drop ore','release hand for unresolved dependency');s.advance(obs({'wire':1},{'ore':1},feedback='I dropped ore.'));s.new_task=False;s.committed=[]
        self.assertIsNone(s.local_action(s.focus))
    def test_known_inventory_registers_before_contents_are_inspected(self):
        s=setup({'pouch':1,'ore':1});s.choose('equip pouch','inventory')
        t=obs({'ore':1},feedback='I equipped pouch as inventory.').replace('I have equipped no objects.','I have equipped 1 pouch.')
        s.advance(t);self.assertIn('pouch',s.containers)
        a,_,_=s.dispatch([{'actions':['store 1 ore pouch']}],s.focus);self.assertEqual(a,'store 1 ore pouch')
    def test_unobserved_contents_are_not_a_definite_material_deficit(self):
        s=setup({'pouch':1});s.track_container('pouch');s.recipes['device']={'ingredients':{'ore':1},'evidence':s.ref('public recipe')}
        v=s.validate_plan(['craft 1 device']);self.assertEqual(v['stop']['status'],'requires_observation')
    def test_recent_damage_not_diluted_by_prior_safe_turns(self):
        s=setup();s.hp=26;s.area_costs[s.location]={'damage':100,'visits':80,'noise':0};s.area_recent[s.location]=[22,0,22]
        self.assertTrue(s.cost_context()['immediate_risk']);s.committed=['enter corridor'];self.assertIsNone(s.local_action(s.focus))
    def test_failed_attempt_is_not_a_permanent_impossibility(self):
        s=setup({'probe_tool':1});s.committed=['lockpick corridor','enter corridor'];s.choose('lockpick corridor','try')
        s.advance(obs(feedback='I failed to pick the lock.'));self.assertFalse(s.committed);self.assertTrue(s.history[-1]['attempt_failed']);self.assertFalse(s.history[-1]['action_success'])
    def test_consumed_entry_tool_not_retained_when_observation_is_dark(self):
        s=setup({'token':1});s.choose('enter corridor','go');s.advance(obs(feedback='I used a token to unlock the path to corridor. I entered corridor.',loc='Lab, corridor',dark=True))
        self.assertNotIn('token',s.hands);self.assertTrue(s.hands_known)
    def test_joint_capacity_check_still_rejects_impossible_sequence(self):
        s=setup({'pouch':1});s.track_container('pouch')['items']={'ore':1,'wire':1};s.capacity_observations[s._capacity_key()]={'count':2}
        v=s.validate_plan(['take out ore pouch','take out wire pouch']);self.assertEqual(v['stop']['reason'],'capacity_conflict')

class PublicReplayTests(unittest.TestCase):
    def test_frozen_observations_keep_main_task_open_and_tutorial_closed(self):
        root=Path(__file__).parent/'results_feedback_v3r3_300';files=list(root.rglob('agent_log.jsonl'))
        if not files:self.skipTest('Public trace is tested locally')
        rows=[json.loads(x) for x in files[0].read_text(encoding='utf8').splitlines()];s=Ledger()
        for i,r in enumerate(rows,1):
            s.advance(r['observation']['text'])
            if i>=27:
                self.assertTrue(any(t['scope']=='main' and t['status']=='open' for t in s.tasks.values()),i)
                self.assertFalse(any(t['scope']=='tutorial' and t['status']=='open' for t in s.tasks.values()),i)
            s.choose(r['action'],'public observation replay')
    def test_old_weapon_stage_keeps_verifiable_goal_and_parameters(self):
        root=Path(__file__).parent/'results_feedback_v3r2_verified';files=list(root.rglob('agent_log.jsonl'))
        if not files:self.skipTest('Public trace is tested locally')
        rows=[json.loads(x) for x in files[0].read_text(encoding='utf8').splitlines()];s=Ledger()
        for i,r in enumerate(rows[:87],1):
            s.advance(r['observation']['text'])
            if i==34:self.assertTrue(any('Arm yourself' in t['text'] and 'attacked' not in t['text'] for t in s.tasks.values() if t['status']=='open'))
            if i==84:
                self.assertTrue(s.target_satisfied('craft 1 wooden_dagger'));self.assertIn('wooden_dagger',s.nearby)
            if i==85:self.assertTrue(s.target_satisfied('pick up wooden_dagger'))
            s.choose(r['action'],'public observation replay',s.focus)

if __name__=='__main__':unittest.main(verbosity=2)

