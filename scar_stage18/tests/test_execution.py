import copy
import json
import unittest
from scar_stage18.controller import Controller18
from scar_stage18.consequences import ConsequenceMemory, public_frame
from scar_stage18.acquisition import bound_store
from scar_stage18.execution_context import assess
from scar_stage18.arbitration import choose


def controller(owned=0, held=0, ground=17):
    c = Controller18(); c.set_goal('craft 1 widget', 'Craft and obtain 1 widget.')
    c.table.state = dict(location='workshop', step=8, hands={'ore':held} if held else {},
        equipment={'bag':1}, ground={'ore':ground,'bench':1}, neighbors=['yard'], feedback='')
    c.table.inventory = 'bag'
    c.table.containers['bag'] = dict(counts={'ore':owned} if owned else {}, load=owned,
        capacity=20, location='workshop', step=8, source='inspection')
    c.table.recipes['widget'] = dict(ingredients=['ore'], quantities={'ore':2}, stations=['bench'])
    return c


class ExecutionTests(unittest.TestCase):
    def test_demand_not_all_ground(self):
        c = controller()
        action, log = bound_store(c, 'store 17 ore inventory')
        self.assertEqual(action, 'store 2 ore inventory')
        self.assertEqual(log['new_ground_deficit'], 2)

    def test_unknown_bounded_and_no_batch_scaling(self):
        c = controller(); c.table.recipes = {}
        self.assertEqual(bound_store(c, 'store 17 ore inventory', hint=100)[0], 'store 1 ore inventory')
        c = controller(); c.queue_needs['widget'] = 4
        self.assertEqual(bound_store(c, 'store 17 ore inventory')[0], 'store 2 ore inventory')

    def test_store_hand_then_ground_p3(self):
        c = controller(held=1)
        # P3's one missing ground copy requires a two-copy transfer.
        self.assertEqual(bound_store(c, 'store 2 ore inventory', ground_need=1)[0], 'store 2 ore inventory')
        self.assertEqual(c.local_collect('ore',1), 'pick up ore')
        c.table.state['hands']['tool'] = 1
        self.assertEqual(c.local_collect('ore',1), 'store 2 ore inventory')

    def test_remote_inventory_not_owned(self):
        c = controller()
        c.table.containers['remote'] = dict(counts={'ore':99}, load=99, capacity=100, location='yard', step=1)
        self.assertEqual(bound_store(c, 'store 17 ore inventory')[0], 'store 2 ore inventory')

    def test_harm_requires_public_carrying_evidence(self):
        c = controller(); f = public_frame(c)
        before = dict(text='My health is at 100.', step=8)
        after = dict(text='I stored 8 ore in my inventory.\nA guard is attacking me. I lost 10 HP.\nMy health is at 90.', step=9)
        c.consequences.observe(before,'store 8 ore inventory',after,f,f)
        self.assertEqual(c.consequences.records[-1]['certainty'], 'temporal_association')
        self.assertNotEqual(c.consequences.check(c,'store 8 ore inventory')['status'], 'REJECT')

    def test_conditional_risk_and_discard_cessation(self):
        c = controller(); f = public_frame(c)
        before = dict(text='My health is at 100.',step=8)
        fb='I stored 8 ore in my inventory.\nThe energy of 8 unstable objects is draining 10 HP. Carrying more than 3 unstable items is dangerous.\nMy health is at 90.'
        after = dict(text=fb,step=9); carried=controller(owned=8); g=public_frame(carried)
        c.consequences.observe(before,'store 8 ore inventory',after,f,g)
        self.assertEqual(c.consequences.check(c,'store 8 ore inventory')['status'], 'REJECT')
        self.assertNotEqual(c.consequences.check(c,'store 1 ore inventory')['status'], 'REJECT')
        c.table.state['location']='yard'
        self.assertNotEqual(c.consequences.check(c,'store 8 ore inventory')['status'], 'REJECT')
        c.table.state['location']='workshop'; c.table.state['equipment']={'shield':1}
        self.assertNotEqual(c.consequences.check(c,'store 8 ore inventory')['status'], 'REJECT')
        c.table.state['equipment']={'bag':1}
        end=dict(text='I discarded 8 ore from bag.\nMy health is at 90.',step=10)
        c.consequences.observe(after,'discard 8 ore bag',end,g,f)
        self.assertTrue(c.consequences.discards[-1]['risk_related'])
        self.assertEqual(c.consequences.check(c,'store 4 ore inventory')['status'], 'REJECT')
        self.assertNotEqual(c.consequences.check(c,'store 2 ore inventory')['status'], 'REJECT')

    def test_unknown_is_not_reject(self):
        c=controller(); c.table.recipes={}
        self.assertEqual(assess(c,'craft 1 novel_product')['status'],'UNKNOWN')
        c.table.recipes['widget']=dict(ingredients=['ore'], quantities={'ore':2},stations=['bench'])
        self.assertEqual(assess(c,'craft 1 widget')['status'],'REJECT')
        c.table.containers['bag']['counts']={'ore':2}
        self.assertNotEqual(assess(c,'craft 4 widget')['status'],'REJECT')
        c.table.state['ground'].pop('bench')
        self.assertEqual(assess(c,'craft 1 widget')['status'],'REJECT')

    def test_arbitration_is_not_llm_default(self):
        c=controller()
        checks=dict(llm=assess(c,'craft 1 widget'),bounded_controller=assess(c,'store 2 ore inventory'))
        self.assertEqual(choose(c,'craft 1 widget','store 2 ore inventory',checks)[0],'store 2 ore inventory')
        checks=dict(llm=assess(c,'inspect ore'),bounded_controller=assess(c,'craft 1 widget'))
        self.assertEqual(choose(c,'inspect ore','craft 1 widget',checks)[0],'inspect ore')

    def test_json_memory(self):
        c=controller(); c.consequences.discards.append(dict(item='ore',risk_related=False,step=8))
        d=json.loads(json.dumps(c.to_dict())); restored=Controller18.from_dict(d)
        self.assertEqual(d,restored.to_dict())
        self.assertEqual(assess(c,'store 2 ore inventory'),assess(restored,'store 2 ore inventory'))


if __name__ == '__main__': unittest.main()
