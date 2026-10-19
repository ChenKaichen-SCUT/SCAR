"""Behavioral acceptance: independent synthetic transitions and frozen public traces.
No real model calls or game rollouts. Fixtures are never imported by the agent.
"""
import copy, json, unittest
from collections import Counter
from pathlib import Path
from feedback_v3_core import Ledger

def obs(hands=None,equipped=None,near=None,feedback='',loc='Workshop, room',dark=False):
    def fmt(d):return ', '.join(f'{n} {o}' for o,n in (d or {}).items() if n) or 'no objects'
    s=f'Current Location: {loc}\n{feedback}\n'
    if dark:return s+'It is too dark to see anything here.\n'
    return s+f'I am holding {fmt(hands)}.\nI have equipped {fmt(equipped)}.\nI see {fmt(near)} near me.\nNeighboring areas: corridor.\n'

def goal(s,text='Craft a device.'):
    s.parse_tasks('guide says: Main goal: Finish work.\nCurrent tasks:\n[1] '+text)
    return next(t['id'] for t in s.tasks.values() if t['status']=='open')

class BehaviorTests(unittest.TestCase):
    def test_dependency_preparation_reaches_product_under_renaming(self):
        # A separate tiny transition model enforces capacities and accessible containers.
        for metal,cord,bag,product in [('ore','wire','pouch','device'),('plank','fiber','case','lever'),('clay','strap','basket','mold')]:
            with self.subTest(product=product):
                s=Ledger();hands=Counter({metal:1,cord:1});ground=Counter({bag:1});inside=Counter({metal:1});equipped={}
                recipe=f'It can be used to craft: {product} (2 {metal}, 1 {cord})'
                s.advance(obs(hands,near=ground,feedback=recipe));gid=goal(s)
                s.choose('inspect '+bag,'resolve contents');s.advance(obs(hands,near=ground,feedback=f'I inspected {bag}: A container.\nIt contains: 1 {metal} (capacity: 1/6).'))
                s.choose('pick up '+bag,'capacity probe');s.advance(obs(hands,near=ground,feedback=f'Cannot pick up {bag}, not enough space in hand.'))
                s.install_objective('craft 1 '+product,gid)
                seen=[]
                for _ in range(7):
                    act,check,record=s.dispatch([{'actions':['craft 1 '+product]}],gid)
                    self.assertIsNotNone(act,record);self.assertFalse(check['blockers']);seen.append(act)
                    s.choose(act,'synthetic dependency preparation',gid,check=check);p=act.split();feedback=''
                    if p[0]=='store':
                        self.assertGreater(hands[p[2]],0);hands[p[2]]-=1;inside[p[2]]+=1;feedback=f'I stored 1 {p[2]} in {bag}.'
                    elif p[:2]==['pick','up']:
                        self.assertLess(sum(hands.values()),2);self.assertGreater(ground[p[2]],0);ground[p[2]]-=1;hands[p[2]]+=1;feedback=f'I picked up {p[2]}.'
                    elif p[0]=='equip':
                        self.assertGreater(hands[bag],0);hands[bag]-=1;equipped[bag]=1;feedback=f'I equipped {bag} as inventory.'
                    elif p[0]=='craft':
                        accessible=hands+inside if hands[bag] or equipped.get(bag) else hands
                        self.assertGreaterEqual(accessible[metal],2);self.assertGreaterEqual(accessible[cord],1)
                        for obj,n in [(metal,2),(cord,1)]:
                            consumed=min(hands[obj],n);hands[obj]-=consumed;inside[obj]-=n-consumed
                        ground[product]+=1;feedback=f'I successfully crafted 1 {product}. It is now on the ground.'
                    else:self.fail('Unexpected preparation '+act)
                    s.advance(obs(hands,equipped,ground,feedback))
                    if ground[product]:break
                self.assertEqual(ground[product],1);self.assertLessEqual(len(seen),5);self.assertFalse(any(x.startswith('inspect ') for x in seen))

    def test_surplus_is_not_progress_and_missing_input_is_selected(self):
        s=Ledger();s.advance(obs({'cord':1,'cloth':1},near={'plank':1},feedback='It can be used to craft: blade (1 plank, 1 cord), cord (0.5 cloth)'))
        gid=goal(s);s.install_objective('craft 1 blade',gid)
        self.assertTrue(any(x['kind']=='already_satisfied_dependency' for x in s.action_check('craft 1 cord')['blockers']))
        a,c,d=s.dispatch([{'actions':['craft 1 cord']}],gid);self.assertEqual(a,'pick up plank')
        s.choose('craft 1 cord','historical bad action',gid);s.advance(obs({'cord':1},near={'plank':1,'cord':1},feedback='I successfully crafted 1 cord. It is now on the ground.'))
        self.assertFalse(s.history[-1]['objective_effect_observed']);self.assertFalse(s.history[-1]['dependency_deficit_reduced'])

    def test_transitive_equipment_goal_also_blocks_surplus(self):
        s=Ledger();s.advance(obs({'cord':1,'cloth':1},feedback='It can be used to craft: blade (1 plank, 1 cord), cord (0.5 cloth)'))
        gid=goal(s);s.install_objective('equip blade',gid)
        self.assertTrue(any(x['kind']=='already_satisfied_dependency' for x in s.action_check('craft 1 cord')['blockers']))

    def test_objective_cannot_be_relabelled_as_easy_substep(self):
        s=Ledger();s.advance(obs({'cord':1},feedback='It can be used to craft: blade (1 plank, 1 cord), cord (0.5 cloth)'));gid=goal(s)
        s.install_objective('craft 1 blade',gid);self.assertFalse(s.install_objective('craft 1 cord',gid));self.assertEqual(s.objective['action'],'craft 1 blade')

    def test_prediction_requires_preconditions_and_effect(self):
        for has_lamp,after_dark,expected in [(False,True,'indeterminate_preconditions'),(True,True,'prediction_not_observed_in_context'),(True,False,'predicted_effect_observed_in_context')]:
            with self.subTest(has_lamp=has_lamp,after_dark=after_dark):
                s=Ledger();s.advance(obs({'lamp':1} if has_lamp else {},feedback='A lamp is nearby.'));s.visibility=False
                s.test_specs['light']={'id':'light','created_step':s.step,'test_action':'enter archive','preconditions':[{'kind':'held','object':'lamp'}],'expected':[{'kind':'visible'}]}
                s.choose('enter archive','test',test_id='light');s.advance(obs({'lamp':1} if has_lamp else {},feedback='I entered archive.',loc='Workshop, archive',dark=after_dark))
                self.assertEqual(s.history[-1]['hypothesis_test']['outcome'],expected)

    def test_no_test_identity_by_action_string(self):
        s=Ledger();s.advance(obs());s.test_specs['old']={'id':'old','created_step':1,'test_action':'enter archive','preconditions':[{'kind':'held','object':'lamp'}],'expected':[{'kind':'visible'}]}
        s.choose('enter archive','travel, not experiment');s.advance(obs(feedback='I entered archive.',dark=True))
        self.assertNotIn('hypothesis_test',s.history[-1])

    def test_already_true_prediction_is_not_new_support(self):
        s=Ledger();s.advance(obs({'lamp':1}));s.test_specs['x']={'id':'x','created_step':1,'test_action':'wait','preconditions':[{'kind':'held','object':'lamp'}],'expected':[{'kind':'held','object':'lamp'}]}
        s.choose('wait','test',test_id='x');s.advance(obs({'lamp':1},feedback='I waited for a while.'))
        self.assertEqual(s.history[-1]['hypothesis_test']['outcome'],'uninformative_already_true')

    def test_hypothesis_without_observable_prediction_rejected(self):
        s=Ledger();s.advance(obs(feedback='The engine is silent.'))
        s.apply_review({'hypotheses':[{'id':'x','claim':'works','test_action':'wait','evidence':[s.ref('The engine is silent.')]}]})
        self.assertNotIn('x',s.test_specs)

    def test_three_object_inspection_rotation_cannot_continue(self):
        s=Ledger();s.advance(obs(near={'a':1,'b':1,'c':1}));gid=goal(s)
        for obj in ['a','b','c']:
            s.choose('inspect '+obj,'look');s.advance(obs(near={'a':1,'b':1,'c':1},feedback='I inspected '+obj+': no new information.'))
        a,c,d=s.dispatch([{'actions':['inspect '+o]} for o in ['a','b','c']],gid)
        self.assertIsNone(a);self.assertEqual(len(d['rejected']),3)
        a,c,d=s.dispatch([{'actions':['enter corridor']}],gid);self.assertEqual(a,'enter corridor')

    def test_changed_container_can_be_inspected_again(self):
        s=Ledger();s.advance(obs({'ore':1},near={'pouch':1}));s.choose('inspect pouch','look');s.advance(obs({'ore':1},near={'pouch':1},feedback='I inspected pouch.\nIt contains: no objects (capacity: 0/5).'))
        self.assertTrue(s.action_check('inspect pouch')['blockers'])
        s.choose('store 1 ore pouch','store');s.advance(obs(near={'pouch':1},feedback='I stored 1 ore in pouch.'))
        self.assertFalse(s.action_check('inspect pouch')['blockers'])

    def test_failed_action_blocked_until_context_changes(self):
        s=Ledger();s.advance(obs());s.choose('enter corridor','try');s.advance(obs(feedback='Cannot enter corridor, the door is locked.'))
        self.assertTrue(any(x['kind']=='repeated_context_action' for x in s.action_check('enter corridor')['blockers']))
        s.advance(obs({'key':1},feedback='I picked up key.'));self.assertFalse(s.action_check('enter corridor')['blockers'])

    def test_combat_not_banned_as_generic_loop(self):
        s=Ledger();s.advance(obs())
        for _ in range(4):s.choose('attack enemy','fight');s.advance(obs(feedback='I attacked enemy for 2 damage.'))
        self.assertFalse(s.action_check('attack enemy')['blockers'])

    def test_crafting_effect_is_product_not_existing_ingredients(self):
        s=Ledger();s.advance(obs({'ore':2,'wire':1},feedback='It can be used to craft: device (2 ore, 1 wire)'));gid=goal(s);s.install_objective('craft 1 device',gid)
        s.choose('inspect ore','look',gid);s.advance(obs({'ore':2,'wire':1},feedback='I inspected ore.'))
        self.assertFalse(s.history[-1]['objective_effect_observed'])
        s.choose('craft 1 device','make',gid);s.advance(obs(near={'device':1},feedback='I successfully crafted 1 device. It is now on the ground.'))
        self.assertTrue(s.history[-1]['objective_effect_observed'])

    def test_ingredient_listing_not_station_capability(self):
        s=Ledger();s.advance(obs(near={'bench':1},feedback='It can be used to craft: blade (1 plank, 1 cord)'));s.choose('inspect bench','look')
        s.advance(obs(near={'bench':1},feedback='I inspected bench: A work station.\nIt can be used to craft: None.'))
        self.assertIn('NOT station',s.observed_roles['bench']['craft_listing_semantics']);self.assertIn('blade',s.recipes);self.assertFalse(s.stations)

    def test_dark_observation_clears_current_visible_objects(self):
        s=Ledger();s.advance(obs(near={'tool':1}));s.choose('enter archive','move');s.advance(obs(loc='Workshop, archive',dark=True))
        self.assertEqual(s.nearby,{});self.assertIn('tool',s.world['Workshop, room']['objects'])

    def test_short_plan_preserved_and_denial_cancels_it(self):
        s=Ledger();s.advance(obs());gid=goal(s);a,c,d=s.dispatch([{'actions':['enter corridor','inspect map']}],gid)
        s.choose(a,'route');s.advance(obs(loc='Workshop, corridor',feedback='I entered corridor.'))
        self.assertEqual(s.queue,['inspect map'])
        s.choose('inspect map','look');s.advance(obs(loc='Workshop, corridor',feedback='Cannot inspect map, not found.'));self.assertEqual(s.queue,[])

    def test_tutorial_finished_instruction_not_left_open(self):
        s=Ledger();s.advance(obs(feedback='Required action: `enter corridor`'));s.choose('enter corridor','tutorial');s.advance(obs(feedback='Tutorial Step 26 complete.',loc='Workshop, corridor'))
        self.assertFalse(any(t['scope']=='tutorial' and t['status']=='open' for t in s.tasks.values()))

    def test_correct_parameter_does_not_imply_write_effect(self):
        s=Ledger();s.advance(obs(feedback='guide says: Main goal: Record.\nCurrent tasks:\n[1] Record the cipher phrase on a sheet.\nThe cipher phrase is SILVER-DAWN.'));gid=next(iter(s.tasks));s.install_objective('write SILVER-DAWN sheet',gid)
        s.choose('write SILVER-DAWN sheet','try',gid);s.advance(obs(feedback='Cannot write on sheet. No writing tools held in hand.'))
        self.assertFalse(s.history[-1]['objective_effect_observed']);self.assertIn('write',s.tool_requirements)
        self.assertTrue(s.action_check('write WRONG-PHRASE sheet',gid)['blockers'])

    def test_uncertain_container_does_not_prove_quantity_absent(self):
        s=Ledger();s.advance(obs({'wire':1},equipped={'pouch':1},feedback='It can be used to craft: shield (2 ore, 1 wire)'))
        s.track_container('pouch');c=s.action_check('craft 1 shield')
        self.assertFalse(c['blockers']);self.assertTrue(c['unknown'])
        s.choose('inspect pouch','resolve quantity');s.advance(obs({'wire':1},equipped={'pouch':1},feedback='I inspected pouch.\nIt contains: 2 ore (capacity: 2/5).'))
        self.assertEqual(s.accessible()[0]['ore'],2);self.assertFalse(s.action_check('craft 1 shield')['blockers'])

    def test_facts_survive_craft_when_unrelated_contents_unchanged(self):
        s=Ledger();s.advance(obs({'ore':2},equipped={'pouch':1},feedback='It can be used to craft: shield (2 ore)'));s.track_container('pouch').update(items={'map':1},complete=True)
        s.choose('craft 1 shield','make');s.advance(obs(equipped={'pouch':1},near={'shield':1},feedback='I successfully crafted 1 shield. It is now on the ground.'))
        self.assertEqual(s.containers['pouch']['items'],{'map':1});self.assertTrue(s.containers['pouch']['complete'])

    def test_fresh_rule_rewrite_allows_retesting_context(self):
        s=Ledger();s.advance(obs());s.choose('enter corridor','try');s.advance(obs(feedback='Cannot enter corridor, the door is locked.'))
        self.assertTrue(s.action_check('enter corridor')['blockers'])
        s.advance(obs(feedback='THE LAWS REWRITE THEMSELVES'))
        self.assertFalse(s.action_check('enter corridor')['blockers'])

class FrozenFailureTests(unittest.TestCase):
    def fixture(self,g):
        p=Path(__file__).resolve().parent/'v3_validation_cases.json'
        self.assertTrue(p.exists(),'required frozen acceptance fixtures must be present')
        return json.loads(p.read_text(encoding='utf-8'))[g]
    def replay(self,g):
        s=Ledger()
        for row in self.fixture(g):s.advance(row['observation']['text']);s.choose(row['action'],'offline historical action')
        s.advance(self.fixture(g)[-1]['next_observation']['text']);return s
    def test_metropolis_known_deadlock_produces_container_preparation(self):
        s=self.replay('metropolis');gid=next(t['id'] for t in s.tasks.values() if t['status']=='open' and t['text'].startswith('Obtain and equip'))
        s.install_objective('craft 1 gavel_club',gid);a,c,d=s.dispatch([{'actions':['craft 1 gavel_club']}],gid)
        self.assertIsNotNone(a);self.assertTrue(a.startswith(('store ','pick up ','equip ')),a);self.assertFalse(a.startswith('inspect '));self.assertFalse(c['blockers'])
    def test_remnant_surplus_and_no_new_weapon_are_distinguished(self):
        s=self.replay('remnant');gid=next(t['id'] for t in s.tasks.values() if t['status']=='open' and 'Arm yourself' in t['text'])
        s.install_objective('craft 1 wooden_dagger',gid)
        self.assertTrue(any(x['kind']=='already_satisfied_dependency' for x in s.action_check('craft 1 thread')['blockers']))
        self.assertFalse(s.target_satisfied('craft 1 wooden_dagger'))

if __name__=='__main__':unittest.main(verbosity=2)
