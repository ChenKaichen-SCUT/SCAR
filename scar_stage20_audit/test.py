from .common import *
block_network=deny_network()
import unittest
from .public import shadow,public_route,enumerate_candidates,fields_support


class AuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plans=read_gzip(RESULTS/'planning_states.jsonl.gz')
        cls.rejects=[r for r in cls.plans if r['old_evidence_reason']=='evidence_unrelated_to_execution_entry']
        cls.terminals=read_gzip(RESULTS/'terminal_states.jsonl.gz');cls.controls=[]

    def test_network_guard(self):
        with self.assertRaisesRegex(RuntimeError,'prohibited'):socket.create_connection(('invalid.test',443))
        self.assertEqual(NETWORK_ATTEMPTS,['blocked_network_attempt']);NETWORK_ATTEMPTS.clear()

    def test_original_44_rederived_and_readonly(self):
        for r in self.rejects:
            c=controller(r['controller']);before=c.to_dict();self.assertEqual(shadow(c,r['plan']['proposal']),r['shadow']);self.assertEqual(c.to_dict(),before)

    def test_negative_controls_all_44(self):
        for r in self.rejects:
            for mode in ('unknown_entry','unreachable_logged_entry','known_locked_only_route','unknown_target','unknown_ID','future_ID'):
                c=controller(r['controller']);p=copy.deepcopy(r['plan']['proposal'])
                if mode=='unknown_entry':p['entry']='__invented_entry_21__'
                elif mode=='unreachable_logged_entry':
                    p['entry']='__isolated_observed_room__';c.table.places[p['entry']]={'objects':{},'step':c.table.state['step']}
                elif mode=='known_locked_only_route':
                    name='__public_locked_frontier__';p['entry']=name
                    c.table.links.setdefault(c.table.state['location'],[]).append(name)
                    c.table.guards[c.table.state['location']+'->'+name]={'locked':True}
                    c.table.state['hands']={}
                elif mode=='unknown_target':p['target']='__invented_target_21__'
                elif mode=='unknown_ID':p['evidence_ids']=['E_unregistered']
                else:
                    rec=c.evidence20[p['evidence_ids'][0]];rec['first_seen_step']=c.table.state['step']+1
                result=shadow(c,p);self.assertEqual(result['category'],'III',(r['id'],mode,result))
                self.assertFalse(result['hypothesis_accept']);self.controls.append(dict(source=r['id'],mutation=mode,result=result['reason'],rejected=True))

    def test_goal_mention_and_free_text_not_entry_evidence(self):
        self.assertEqual(fields_support(dict(kind='goal',key='x',names=['x'],value='x'),'x'),[])
        self.assertEqual(fields_support(dict(kind='recipe',key='r',names=['r'],value={'text':'hypothetical room x'}),'x'),[])

    def test_typed_from_location_and_nested_public_map(self):
        self.assertIn('from_location',fields_support(dict(kind='public_frontier',key='b',names=['b'],value={'from_location':'a','route':['b']}),'a'))
        self.assertIn('public_entries.reachable',fields_support(dict(kind='blocker',key='goal',names=['goal'],value={'public_entries':{'reachable':['a']}}),'a'))

    def test_cog_crossbow_transit_not_generated(self):
        s=next(s for s in self.terminals if s['task']['target_item']=='cog_crossbow');c=controller(s['controller'])
        self.assertEqual(c.exploration_spent,14);self.assertEqual(public_route(c,'cellar'),['courtyard','cellar'])
        candidate=next(r for r in s['candidates'] if r['action']=='enter courtyard')
        self.assertTrue(candidate['eligible_public_trial']);self.assertTrue(candidate['usable_by_frozen_predicate']);self.assertFalse(candidate['fallback_candidate_generated'])

    def test_enumeration_does_not_mutate_controller(self):
        for s in self.terminals:
            c=controller(s['controller']);before=c.to_dict();enumerate_candidates(c,read_gzip(folder(s['task_id'])/'trajectory.jsonl.gz'));self.assertEqual(before,c.to_dict())

    def test_native_branches_do_not_imply_success(self):
        records=read_gzip(RESULTS/'counterfactual_results.jsonl.gz')
        self.assertTrue(all(r['steps']==1 and r['model_calls']==0 for r in records))
        self.assertEqual(sum(not r['native_action_accepted'] for r in records),3)
        self.assertTrue(any(r['native_action_accepted'] and r['player_hp_loss']>0 for r in records))


def main():
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(AuditTests))
    assert result.wasSuccessful() and not NETWORK_ATTEMPTS
    write(RESULTS/'negative_controls.json',AuditTests.controls)
    write(RESULTS/'test_receipt.json',dict(passed=True,tests=result.testsRun,negative_controls=len(AuditTests.controls),false_acceptances=0,
        deliberate_blocked_network_self_test=1,external_network_connections=0,new_model_calls=0,tokens=0,cost_usd=0))


if __name__=='__main__':main()
