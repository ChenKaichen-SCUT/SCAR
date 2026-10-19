"""Offline behavior tests and frozen-trajectory checks; no inference or rollout."""
import json,unittest
from pathlib import Path
from feedback_v2_core import Ledger
def obs(hands='no objects',equipped='no objects',near='no objects',feedback='',loc='Plant, shop'):
    return f'Current Location: {loc}\n{feedback}\nI am holding {hands}.\nI have equipped {equipped}.\nI see {near} near me.\nMy health is at 100.\n'
class V2Tests(unittest.TestCase):
    def test_exact_recipe_quantity_beats_claim(self):
        s=Ledger();s.advance(obs('1 ore, 1 wire',feedback='It can be used to craft: shield (2 ore, 1 wire)'))
        c=s.action_check('craft 1 shield');self.assertEqual(c['blockers'][0]['missing'],1)
        s.apply_review({'hypotheses':[{'id':'container','claim':'containers cannot supply ingredients','status':'supported','test_action':'craft 1 shield','evidence':[s.ref('shield (2 ore, 1 wire)')]}]})
        self.assertEqual(s.hypotheses['container']['status'],'open')
        s.choose('craft 1 shield','test',test_id='container',check=c)
        s.advance(obs('1 ore, 1 wire',feedback='Cannot craft a single shield. Do not have sufficient amount of necessary ingredients.'))
        self.assertEqual(s.history[-1]['hypothesis_test']['outcome'],'indeterminate')
    def test_inventory_and_hand_quantities_jointly_counted(self):
        s=Ledger();s.advance(obs('1 wire',equipped='1 pouch',feedback='It can be used to craft: shield (2 ore, 1 wire)'))
        s.choose('inspect inventory','check')
        s.advance(obs('1 wire',equipped='1 pouch',feedback='I inspected my inventory.\nIt contains: 2 ore (capacity: 2/10).'))
        self.assertEqual(s.accessible()[0]['ore'],2)
        self.assertFalse(s.action_check('craft 1 shield')['blockers'])
    def test_unknown_container_is_not_empty(self):
        s=Ledger();s.advance(obs('1 wire',equipped='1 pouch',feedback='It can be used to craft: shield (2 ore, 1 wire)'))
        c=s.action_check('craft 1 shield');self.assertFalse(c['blockers']);self.assertTrue(c['unknown']);self.assertTrue(c['warnings'])
    def test_distinct_task_parameters_persist(self):
        s=Ledger();s.advance(obs(feedback='guide says: Main goal: Restore access.\nCurrent tasks:\n[1] Record the cipher phrase on a sheet.\n\nThe cipher phrase is SILVER-DAWN.'))
        tid=next(t['id'] for t in s.tasks.values() if 'Record' in t['text'])
        for _ in range(10):s.advance(obs(feedback='The restoration clause is RETURN-FIRST-LAW.'))
        self.assertEqual([s.literals[x]['value'] for x in s.tasks[tid]['bindings']],['SILVER-DAWN'])
        self.assertTrue(s.action_check('write RETURN-FIRST-LAW sheet',tid)['blockers'])
        self.assertFalse(s.action_check('write SILVER-DAWN sheet',tid)['blockers'])
    def test_authoritative_list_does_not_erase_other_owner(self):
        s=Ledger();s.advance(obs(feedback='guide says: Main goal: Restore access.\nCurrent tasks:\n[1] Find a token.\n[2] Open the gate.'))
        s.advance(obs(feedback='helper says: Main goal: Rescue.\nCurrent tasks:\n[1] Find a rope.'))
        self.assertEqual(sum(t['status']=='open' for t in s.tasks.values()),3)
        s.advance(obs(feedback='guide says: Main goal: Restore access.\nCurrent tasks:\n[1] Open the gate.'))
        self.assertEqual(sum(t['status']=='open' for t in s.tasks.values()),2)
    def test_new_instruction_supersedes_same_quest_owner(self):
        s=Ledger();s.advance(obs(feedback='Stage completed.\nTalk to mentor about what to do next.'))
        s.advance(obs(feedback='mentor says: Craft a shield.'))
        s.advance(obs(feedback='mentor says: The entrance is somewhere within:\nPlant, upper floor; Plant, lower floor'))
        active=[t for t in s.tasks.values() if t['status']=='open']
        self.assertEqual(len(active),1);self.assertIn('lower floor',active[0]['text'])
    def test_successful_inverse_cycle_detected(self):
        s=Ledger();s.advance(obs(near='1 token'))
        for _ in range(3):
            s.choose('pick up token','collect');s.advance(obs('1 token',feedback='I picked up token.'))
            s.choose('drop token','free capacity');s.advance(obs(near='1 token',feedback='I dropped token.'))
        self.assertIsNotNone(s.loop);self.assertEqual(len(s.completed_messages),0)
        self.assertFalse(any(t['denials'] for t in s.history))
    def test_accumulating_needed_items_not_cycle(self):
        s=Ledger();s.advance(obs(near='8 ore'))
        for i in range(1,5):
            s.choose('pick up ore','collect');s.advance(obs(f'{i} ore',near=f'{8-i} ore',feedback='I picked up ore.'))
        self.assertIsNone(s.loop)
    def test_local_success_not_task_success(self):
        s=Ledger();s.advance(obs(feedback='guide says: Main goal: Open a gate.\nCurrent tasks:\n[1] Open the gate.'))
        tid=next(iter(s.tasks));s.plans['x']={'task_id':tid,'expected':[{'kind':'held','object':'key'}]}
        s.advance(obs('1 key'));v=s.evaluate_plan()['x']
        self.assertTrue(v['local_observable_satisfied']);self.assertFalse(v['task_confirmed'])
    def test_review_budget_spread_not_exhausted_early(self):
        s=Ledger();used=[]
        for step in range(1,501):
            s.advance(obs(feedback='Cannot enter room, the door is locked.'))
            s.choose('enter room','try')
            if s.trigger():s.apply_review({});used.append(step)
        self.assertLessEqual(len(used),80);self.assertGreater(max(used),470)
    def test_facts_remain_without_fresh_guidance(self):
        s=Ledger();s.advance(obs(feedback='It can be used to craft: shield (2 ore, 1 wire)'));s.apply_review({})
        for _ in range(20):s.advance(obs())
        self.assertIsNone(s.packet()['guidance']);self.assertTrue(s.packet()['observed_recipes'])
    def test_no_predicted_success_committed(self):
        s=Ledger();s.advance(obs());s.choose('pick up token','will succeed')
        self.assertEqual(s.hands,{});self.assertEqual(s.history,[])

class FrozenTraceTests(unittest.TestCase):
    def rows(self,game):
        path=Path(__file__).resolve().parent/'results_feedback/runs'/f'{game}__feedback_v1/agent_adam_davis/agent_log.jsonl'
        if not path.exists():self.skipTest('frozen local evidence not present; synthetic behavior tests still run')
        return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines()]
    def test_mark_bad_probe_is_flagged_from_public_history(self):
        s=Ledger();rows=self.rows('mark')
        for r in rows[:295]:
            s.advance(r['observation']['text']);check=s.action_check(r['action'])
            if r['step']==294:
                deficits=[x for x in check['blockers']+check['warnings'] if x['kind']=='quantity_deficit']
                self.assertTrue(any(x['object']=='leather_strip' and x['required']==2 and x['missing']==1 for x in deficits))
            s.choose(r['action'],'offline historical action',check=check)
    def test_metropolis_old_parameter_not_overwritten(self):
        s=Ledger();rows=self.rows('metropolis')
        for r in rows[:170]:s.advance(r['observation']['text']);s.choose(r['action'],'offline historical action')
        t=next(t for t in s.tasks.values() if 'Record the cipher phrase' in t['text'])
        self.assertIn('AURUM-NOCTIS',[s.literals[x]['value'] for x in t['bindings']])
        self.assertTrue(s.action_check(rows[169]['action'],t['id'])['blockers'])

if __name__=='__main__':unittest.main(verbosity=2)
