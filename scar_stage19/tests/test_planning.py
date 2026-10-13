import copy
import json
import unittest
from scar_stage19.controller import Controller19
from scar_stage19.acquisition import bound_store
from scar_stage19.planning import validate, COMPLETION
from scar_stage19.agent import make_agent


def obs(feedback='', location='room', hands='no objects', equipment='no objects',
        ground='no objects', neighbors='hall', step=0):
    return dict(step=step, text=f'Current Location: Test, {location}\nI am holding {hands}.\n'
        f'I have equipped {equipment}.\nI see {ground} near me.\nI see no one nearby.\n'
        f'Neighboring areas: {neighbors}\nMy health is at 100.\nFeedback:\n{feedback}')


def rule(c, text, step=1):
    o = obs('I have acquired a new item: ore. It can be used to craft: '+text, step=step)
    c.table.knowledge.observe(o, 'pick up ore')
    c.table.sync()


def controller():
    c = Controller19(); c.set_goal('craft 1 widget', 'Craft and obtain at least 1 widget.')
    c.table.observe(obs())
    return c


def proposal(kind, target, entry=None):
    return dict(type=kind, target=target, entry=entry or target, public_evidence=[target],
                direction='Resolve the public task blocker through this observed entry.',
                completion=COMPLETION[kind], uncertainty=['downstream recipe may remain unknown'])


class CaptureProvider:
    def __init__(self, reply=None): self.calls=[]; self.reply=reply
    def generate(self, **kwargs):
        if self.reply is None: raise AssertionError('Unexpected model call for known execution')
        self.calls.append(kwargs)
        kwargs['validator'](self.reply)
        return dict(parsed=copy.deepcopy(self.reply), response=json.dumps(self.reply),
                    num_input_tokens=0, num_output_tokens=0)


class PlanningTests(unittest.TestCase):
    def test_known_execution_has_zero_calls(self):
        provider=CaptureProvider(); agent=make_agent(provider, game='robot_kingdom')
        agent.initialize_episode([], 'craft 1 widget', 'Craft and obtain at least 1 widget.')
        rule(agent.controller, 'widget (2 ore)')
        action,*_=agent.act(obs(ground='2 ore'))
        self.assertEqual(action, 'pick up ore')
        self.assertFalse(agent.decision['llm_called']); self.assertEqual(provider.calls, [])

    def test_real_gap_uses_new_schema_and_only_one_call(self):
        provider=CaptureProvider(proposal('INSPECT_OBJECT','ore'))
        agent=make_agent(provider,game='robot_kingdom')
        agent.initialize_episode([], 'craft 1 widget', 'Craft and obtain at least 1 widget.')
        action,*_=agent.act(obs(ground='1 ore'))
        self.assertEqual(action,'inspect ore'); self.assertEqual(len(provider.calls),1)
        self.assertEqual(provider.calls[0]['phase'],'subgoal')
        self.assertNotIn('action',provider.calls[0]['required'])
        self.assertTrue(agent.decision['subgoal_acceptance']['accepted'])

    def test_persistent_remote_inspection_and_goal_retained(self):
        c=controller(); c.table.places['hall']={'objects':{'ore':1},'step':0}
        c.blocker19={'kind':'missing_recipe','item':'widget'}
        result=c.accept(proposal('INSPECT_OBJECT','ore'),'ore publicly observed in hall')
        self.assertTrue(result['accepted'])
        before=obs(); action=c.choose(before); self.assertEqual(action,'enter hall')
        after=obs('I entered hall.',location='hall',ground='1 ore',neighbors='room',step=1)
        c.observe(before,action,after)
        self.assertIsNotNone(c.intent19); self.assertEqual(c.target,'craft 1 widget')
        self.assertEqual(c.choose(after),'inspect ore')
        final=obs('I inspected ore:\nIt can be used to craft: widget (made of ore).',
                  location='hall',ground='1 ore',neighbors='room',step=2)
        c.observe(after,'inspect ore',final)
        self.assertIsNone(c.intent19); self.assertEqual(c.intent_log19[-1]['steps'],2)
        self.assertEqual(c.intent_log19[-1]['status'],'completed')
        self.assertEqual(c.target,'craft 1 widget')

    def test_missing_object_feedback_records_unknown_type(self):
        c=controller(); rule(c,'widget (1 ore)')
        before=obs(hands='1 ore'); c.table.observe(before)
        after=obs('Cannot craft widget. Missing necessary furnace in the current area.',hands='1 ore',step=2)
        c.observe(before,'craft 1 widget',after)
        self.assertEqual(c.preconditions19['widget:furnace']['object_type'],'UNKNOWN')
        self.assertFalse(c.retry_allowed('craft 1 widget'))
        self.assertNotIn('furnace',c.table.recipes)

    def test_known_prerequisite_location_is_executed_without_planning(self):
        c=controller(); rule(c,'widget (1 ore)')
        o=obs('Cannot craft widget. Missing necessary furnace in the current area.',hands='1 ore',step=2)
        c.observe(obs(hands='1 ore'),'craft 1 widget',o)
        c.table.places['hall']={'objects':{'furnace':1},'step':1}
        self.assertEqual(c.choose(o),'enter hall')
        after=obs('I entered hall.',location='hall',hands='1 ore',ground='1 furnace',neighbors='room',step=3)
        c.observe(o,'enter hall',after)
        self.assertTrue(c.retry_allowed('craft 1 widget'))
        self.assertEqual(c.choose(after),'craft 1 widget')
        self.assertEqual(c.preconditions19['widget:furnace']['first_satisfied_step'],2)

    def test_known_prerequisite_recipe_builds_object_on_ground(self):
        c=controller(); rule(c,'widget (1 ore), furnace (1 stone)')
        o=obs('Cannot craft widget. Missing necessary furnace in the current area.',hands='1 ore, 1 stone',step=2)
        c.observe(obs(hands='1 ore, 1 stone'),'craft 1 widget',o)
        self.assertEqual(c.choose(o),'craft 2 furnace')  # original S1 intermediate batch
        self.assertEqual(c.target,'craft 1 widget')

    def test_cyclic_prerequisites_and_inaccessible_material_bounded(self):
        c=controller(); rule(c,'widget (1 ore), furnace (1 widget)')
        c.table.knowledge.observe(obs('Cannot craft widget. Missing necessary furnace in the current area.',step=2),'craft 1 widget')
        c.table.sync(); c.table.state['hands']={'ore':1}
        self.assertIsNone(c.known_step('furnace',1,('widget',),ground=True))
        self.assertEqual(c.blocker19['kind'],'prerequisite_cycle_or_depth_limit')

    def test_unknown_not_rejected_and_no_hidden_recipe_filled(self):
        c=controller(); c.table.observe(obs(ground='1 ore'))
        c.blocker19={'kind':'unknown_recipe','item':'widget'}
        accepted=c.accept(proposal('INSPECT_OBJECT','ore'),'ore is visibly present')
        self.assertTrue(accepted['accepted']); self.assertEqual(c.table.recipes,{})
        self.assertEqual(c.assess('craft 1 widget')['status'],'UNKNOWN')

    def test_acceptance_preview_does_not_spend_probes(self):
        c=controller(); c.table.observe(obs(ground='1 ore'))
        c.blocker19={'kind':'unknown_recipe','item':'widget'}
        state=(c.exploration_spent,copy.deepcopy(c.trials),copy.deepcopy(c.probes),copy.deepcopy(c.queue))
        c.accept(proposal('INSPECT_OBJECT','ore'),'ore visible')
        self.assertEqual(state,(c.exploration_spent,c.trials,c.probes,c.queue))
        c.choose(obs(ground='1 ore'))
        self.assertEqual(c.exploration_spent,state[0]+1)

    def test_repeat_rejection_and_fixed_lifetime(self):
        c=controller(); c.table.observe(obs(ground='1 ore')); c.blocker19={'kind':'unknown_recipe','item':'widget'}
        p=proposal('INSPECT_OBJECT','ore'); self.assertTrue(c.accept(p,'ore visible')['accepted'])
        c.close_intent('failed','synthetic native failure fixture')
        self.assertFalse(c.accept(p,'ore visible')['accepted'])
        c.start_request(); self.assertFalse(c.can_request())
        c.table.state['step']+=1; self.assertFalse(c.can_request())

    def test_json_restore_next_action_and_intent_identical(self):
        c=controller(); c.table.observe(obs(ground='1 ore')); c.blocker19={'kind':'unknown_recipe','item':'widget'}
        c.accept(proposal('INSPECT_OBJECT','ore'),'ore visible')
        d=Controller19.from_dict(json.loads(json.dumps(c.to_dict())))
        self.assertEqual(c.choose(obs(ground='1 ore')),d.choose(obs(ground='1 ore')))
        self.assertEqual(c.to_dict(),d.to_dict())

    def test_demand_acquisition_and_P3_final_product(self):
        c=controller(); rule(c,'widget (2 ore)')
        c.table.observe(obs(ground='17 ore',equipment='1 bag'))
        c.table.inventory='bag'; c.table.containers['bag']=dict(counts={},load=0,capacity=20,location='room',step=0)
        self.assertEqual(bound_store(c,'store 17 ore inventory')[0],'store 2 ore inventory')
        self.assertEqual(c.choose(obs(ground='1 widget')),'pick up widget')
        self.assertEqual(c.audit19['source'],'P3_finish')

    def test_fake_action_wrapper_rejected(self):
        with self.assertRaises(ValueError): validate(dict(action='wait',reasoning='pretend plan'))


if __name__=='__main__': unittest.main()
