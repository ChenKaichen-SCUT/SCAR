"""Boundary tests for diagnostic evidence, not algorithm implementation tests."""
import unittest
from .common import coverage
from .analyze import context_facts, error_reason

class EvidenceTests(unittest.TestCase):
    def test_quantity_not_inferred_from_relation_or_model_guess(self):
        e=dict(product='brick',ingredients=['coal'],quantities=None,stations=None,
               raw_evidence='It can be used to craft: brick (made of coal).',evidence_id='past')
        q=dict(messages=[dict(role='user',content=e['raw_evidence']+' I think brick needs 3 coal.')])
        f,_,_=context_facts(q,[e])
        self.assertIsNone(f['brick']['quantities'])

    def test_late_quantity_does_not_leak_through_old_relation(self):
        old=dict(product='brick',ingredients=['coal'],quantities=None,stations=None,
            raw_evidence='It can be used to craft: brick (made of coal).',evidence_id='old')
        new=dict(old,quantities={'coal':3},raw_evidence='I have acquired a new item: coal. It can be used to craft: brick (3 coal)',evidence_id='new')
        q=dict(messages=[dict(role='user',content=old['raw_evidence'])])
        f,ids,_=context_facts(q,[old,new])
        self.assertIsNone(f['brick']['quantities']);self.assertEqual(ids,['old'])

    def test_system_summary_must_be_attested(self):
        q=dict(messages=[dict(role='system',content='{"kind":"recipe","id":"r","key":"brick","value":{"ingredients":["coal"],"quantities":{"coal":3}}}')])
        f,_,_=context_facts(q,[])
        self.assertIsNone(f['brick']['quantities'])

    def test_empty_station_truth_does_not_create_relation(self):
        c=coverage({},dict(x=dict(name='brick',ingredient_names={'coal':3},station_names=[])))
        self.assertEqual(c['relation'],[]);self.assertEqual(c['full_explicitly_confirmed'],[])
        self.assertEqual(c['station_requirement_disclosed'],[])

    def test_hidden_weights_and_stations_are_not_needed(self):
        facts={'brick':dict(ingredients=['coal'],quantities={'coal':3},stations=None)}
        c=coverage(facts,{'id':{'name':'brick'}})
        self.assertEqual(c['quantity'],['brick'])
        self.assertEqual(c['station_requirement_disclosed'],[])

    def test_output_length_is_not_input_overflow(self):
        q=dict(raw_response=dict(choices=[dict(finish_reason='length',message=dict(content='{"action":'))]),phase='action')
        self.assertTrue(error_reason(q,[]).startswith('JSON_decode; finish=length'))

if __name__=='__main__':unittest.main()
