"""Offline synthetic tests; no game rollout or API request."""
import json
import unittest
from feedback_control_core import ControlState, schema_error

def observation(items='nothing', feedback='', location='workroom'):
    return f'Current Time: 0001-01-01 00:00:00\nCurrent Location: facility, {location}\n\n{feedback}\n\nI am holding {items}.\nI see a device near me.\nMy health is at 10.\n'

class ControlTests(unittest.TestCase):
    def test_provenance_rejects_fabricated_quote(self):
        c=ControlState(); c.advance(observation())
        self.assertEqual(c.evidence([{'step':1,'quote':'A nonexistent observation.'}]), [])
        self.assertEqual(c.evidence([{'step':9,'quote':'I am holding nothing.'}]), [])
        self.assertEqual(len(c.evidence([{'step':1,'quote':'I am holding nothing.'}])),1)

    def test_result_not_committed_before_feedback(self):
        c=ControlState(); text=observation();c.advance(text);c.choose(text,'activate device','try it')
        self.assertEqual(c.transitions,[])
        after=observation(feedback='Cannot activate device, missing authorization.')
        c.advance(after)
        self.assertEqual(c.transitions[0]['action'],'activate device')
        self.assertEqual(c.transitions[0]['after_step'],2)
        self.assertEqual(c.transitions[0]['denials'],['Cannot activate device, missing authorization.'])

    def denied_twice(self):
        c=ControlState(); text=observation();c.advance(text)
        for _ in range(2):
            c.choose(text,'activate device','try')
            text=observation(feedback='Cannot activate device, missing authorization.')
            c.advance(text)
        return c,text

    def test_repeat_warning_clears_after_state_change(self):
        c,text=self.denied_twice()
        self.assertTrue(c.repeated_denial('activate device',text))
        self.assertIsNone(c.repeated_denial('activate device',observation(items='access_card')))
        self.assertIsNone(c.repeated_denial('activate device',observation(location='hallway')))
        self.assertIsNone(c.repeated_denial('inspect device',text))

    def test_successful_repetition_not_hard_blocked(self):
        c=ControlState();text=observation();c.advance(text)
        for _ in range(4):
            c.choose(text,'operate device','continue process')
            text=observation(feedback='The process advances by one unit.')
            c.advance(text)
        self.assertIsNone(c.repeated_denial('operate device',text))
        self.assertEqual(c.trigger(),'repeated_action_and_feedback_candidate')

    def test_rule_withdrawal_requires_new_evidence(self):
        c=ControlState();c.advance(observation(feedback='The device requires authorization.'))
        r={'id':'authorization','condition':'in this state','lesson':'obtain authorization',
           'status':'supported','evidence':[{'step':1,'quote':'The device requires authorization.'}]}
        c.apply_review({'rules':[r]},'test')
        self.assertEqual(c.rules['authorization']['status'],'supported')
        r['status']='retired';c.apply_review({'rules':[r]},'test')
        self.assertEqual(c.rules['authorization']['status'],'supported')
        c.advance(observation(feedback='The authorization requirement has been removed.'))
        r['evidence']=[{'step':2,'quote':'The authorization requirement has been removed.'}]
        c.apply_review({'rules':[r]},'test')
        self.assertEqual(c.rules['authorization']['status'],'retired')
        self.assertEqual(c.select_rules(observation()),[])

    def test_malformed_nested_outputs_do_not_crash(self):
        c=ControlState();c.advance(observation());c.apply_review(None,'test')
        c.apply_review({'rules':None,'evidence':None,'applicable_rules':None},'test')
        self.assertIsNone(c.guidance)

    def test_schema_uses_declared_interface_only(self):
        schema=[('pick up',['object_name']),('write',['text','writable_name']),('wait',[])]
        self.assertIsNotNone(schema_error('pick up 5 coin',schema))
        self.assertIsNone(schema_error('pick up coin',schema))
        self.assertIsNone(schema_error('write a long message note',schema))
        self.assertIsNone(schema_error('wait',schema))
        self.assertIsNotNone(schema_error('invent tool',schema))

    def test_review_budget_and_cooldown(self):
        c,text=self.denied_twice();self.assertEqual(c.trigger(),'explicit_environment_denial')
        c.last_review=c.step;self.assertIsNone(c.trigger())
        c.last_review=-100;c.reviews=80;self.assertIsNone(c.trigger())

    def test_applicability_requires_current_evidence(self):
        c=ControlState();c.advance(observation(feedback='The device requires authorization.'))
        c.advance(observation(items='access_card'))
        rule={'id':'access','condition':'access absent','lesson':'obtain access','status':'tentative',
              'evidence':[{'step':1,'quote':'The device requires authorization.'}]}
        result={'rules':[rule],'evidence':[{'step':2,'quote':'I am holding access_card.'}],
                'applicable_rules':[{'id':'access','applicability':'true','evidence':rule['evidence']}]}
        c.apply_review(result,'test')
        self.assertEqual(c.guidance['applicable_rules'],[])

if __name__=='__main__': unittest.main(verbosity=2)
