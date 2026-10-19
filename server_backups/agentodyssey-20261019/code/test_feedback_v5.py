"""Offline behavioral tests: independent transitions; no provider or game execution."""
import concurrent.futures,json,tempfile,unittest
from pathlib import Path
from api_budget_guard import BudgetGuard,BudgetStopped,guarded_generate
from feedback_v5_core import Ledger,ScreenStopped
from compact_decision_packet import packet_for,short_refs
from test_feedback_v3 import obs,goal

def kinds(s,a):return {x['kind'] for x in s.action_check(a)['blockers']}
def generous(calls=100):return dict(calls=calls,input_tokens=1_000_000,uncached_input_tokens=1_000_000,output_tokens=100_000)
PAYLOAD={'messages':[{'role':'user','content':'hello'}],'max_tokens':30}
USAGE={'prompt_tokens':20,'prompt_cache_miss_tokens':5,'completion_tokens':10}

class BudgetTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'budget.sqlite'
    def tearDown(self):self.tmp.cleanup()
    def test_rejects_before_upstream_and_keeps_settled_usage(self):
        g=BudgetGuard(self.path,generous(1));calls=[]
        def upstream(*a):calls.append(1);return {'usage':USAGE}
        guarded_generate(g,'a',PAYLOAD,upstream)
        with self.assertRaises(BudgetStopped):guarded_generate(g,'b',PAYLOAD,upstream)
        self.assertEqual(len(calls),1);self.assertEqual(g.usage(),dict(calls=1,input_tokens=20,uncached_input_tokens=5,output_tokens=10))
    def test_atomic_shared_reservations_under_concurrency(self):
        g=BudgetGuard(self.path,generous(7))
        def reserve(i):
            try:return BudgetGuard(self.path,generous(7)).reserve(str(i),PAYLOAD['messages'],30)
            except BudgetStopped:return None
        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:out=list(ex.map(reserve,range(32)))
        self.assertEqual(sum(x is not None for x in out),7);self.assertEqual(g.usage()['calls'],7)
    def test_per_run_and_batch_limits_both_enforced(self):
        g=BudgetGuard(self.path,generous(3),generous(1));g.reserve('a',PAYLOAD['messages'],30)
        with self.assertRaises(BudgetStopped):g.reserve('a',PAYLOAD['messages'],30)
        g.reserve('b',PAYLOAD['messages'],30);g.reserve('c',PAYLOAD['messages'],30)
        with self.assertRaises(BudgetStopped):g.reserve('d',PAYLOAD['messages'],30)
    def test_each_token_budget_checked_before_call(self):
        for field in ['input_tokens','uncached_input_tokens','output_tokens']:
            limits=generous();limits[field]=1;g=BudgetGuard(Path(self.tmp.name)/(field+'.sqlite'),limits);calls=[]
            with self.assertRaises(BudgetStopped):guarded_generate(g,'a',PAYLOAD,lambda *a:calls.append(1))
            self.assertFalse(calls);self.assertEqual(g.usage()['calls'],0)
    def test_timeout_retains_reservation_and_prevents_retry(self):
        g=BudgetGuard(self.path,generous());calls=[]
        def timeout(*a):calls.append(1);raise TimeoutError()
        with self.assertRaises(BudgetStopped):guarded_generate(g,'a',PAYLOAD,timeout)
        used=g.usage();self.assertGreater(used['input_tokens'],20)
        with self.assertRaises(BudgetStopped):guarded_generate(g,'a',PAYLOAD,timeout)
        self.assertEqual(len(calls),1);self.assertEqual(g.usage(),used)
    def test_missing_usage_halts_batch(self):
        g=BudgetGuard(self.path,generous())
        with self.assertRaises(BudgetStopped):guarded_generate(g,'a',PAYLOAD,lambda *a:{})
        with self.assertRaises(BudgetStopped):g.reserve('b',PAYLOAD['messages'],30)
    def test_null_or_malformed_response_halts_batch(self):
        for i,result in enumerate([None,[],{'usage':None},{'usage':{'prompt_tokens':True,'completion_tokens':2}}]):
            g=BudgetGuard(Path(self.tmp.name)/('malformed'+str(i)+'.sqlite'),generous())
            with self.assertRaises(BudgetStopped):guarded_generate(g,'a',PAYLOAD,lambda *a:result)
            with self.assertRaises(BudgetStopped):g.reserve('b',PAYLOAD['messages'],30)
    def test_missing_cache_usage_charges_all_input(self):
        g=BudgetGuard(self.path,generous());r=g.reserve('a',PAYLOAD['messages'],30)
        self.assertTrue(g.complete(r,dict(prompt_tokens=20,completion_tokens=10)))
        self.assertEqual(g.usage()['uncached_input_tokens'],20)
    def test_reservation_violation_halts_future_requests(self):
        g=BudgetGuard(self.path,generous());r=g.reserve('a',PAYLOAD['messages'],30)
        self.assertFalse(g.complete(r,dict(prompt_tokens=20,completion_tokens=31)))
        with self.assertRaises(BudgetStopped):g.reserve('a',PAYLOAD['messages'],30)
    def test_restart_cannot_silently_increase_limits(self):
        BudgetGuard(self.path,generous(1))
        with self.assertRaises(AssertionError):BudgetGuard(self.path,generous(2))
    def test_single_prompt_bound(self):
        g=BudgetGuard(self.path,generous())
        with self.assertRaises(BudgetStopped):g.reserve('a',[{'role':'user','content':'x'*160_000}],30)
        self.assertEqual(g.usage()['calls'],0)

class ConditionalRepeatTests(unittest.TestCase):
    def test_health_time_rationale_do_not_reopen_failed_door(self):
        s=Ledger();s.advance(obs());s.choose('enter corridor','first');s.advance(obs(feedback='Cannot enter corridor, the door is locked.\nHP: 98. Time: 2'))
        self.assertIn('unchanged_failed_preconditions',kinds(s,'enter corridor'))
        s.advance(obs(feedback='HP: 92. Time: 3'));s.focus='a new explanation'
        self.assertIn('unchanged_failed_preconditions',kinds(s,'enter corridor'))
    def test_observed_key_or_rule_change_reopens_probe(self):
        for changed in [obs({'key':1}),obs(feedback='THE LAWS REWRITE')]:
            s=Ledger();s.advance(obs());s.choose('enter corridor','first');s.advance(obs(feedback='Cannot enter corridor, the door is locked.'))
            s.advance(changed);self.assertNotIn('unchanged_failed_preconditions',kinds(s,'enter corridor'))
    def test_public_unlock_reopens_but_repeated_notice_does_not(self):
        s=Ledger();s.advance(obs());s.choose('enter corridor','first');s.advance(obs(feedback='Cannot enter corridor, the door is locked.'))
        s.advance(obs(feedback='The corridor door is now unlocked.'));self.assertNotIn('unchanged_failed_preconditions',kinds(s,'enter corridor'))
        s.choose('enter corridor','try newly unlocked');s.advance(obs(feedback='Cannot enter corridor, it is still obstructed.'))
        s.advance(obs(feedback='The corridor door is now unlocked.'));self.assertIn('unchanged_failed_preconditions',kinds(s,'enter corridor'))
    def test_negated_unlock_does_not_reopen(self):
        s=Ledger();s.advance(obs());s.choose('enter corridor','first');s.advance(obs(feedback='Cannot enter corridor, the door is locked.'))
        s.advance(obs(feedback='The corridor door is not unlocked.'));self.assertIn('unchanged_failed_preconditions',kinds(s,'enter corridor'))
    def test_net_cycle_detected_without_banning_useful_return(self):
        s=Ledger();s.advance(obs(loc='Workshop, room'))
        for _ in range(4):
            s.choose('enter corridor','travel');s.advance(obs(loc='Workshop, corridor'))
            s.choose('enter room','return');s.advance(obs(loc='Workshop, room'))
        self.assertIn('net_cycle_without_gain',kinds(s,'enter corridor'))
        s.advance(obs({'wire':1},loc='Workshop, room'));self.assertNotIn('net_cycle_without_gain',kinds(s,'enter corridor'))
    def test_cycle_never_traps_darkness_exit_but_blocks_blind_reentry(self):
        s=Ledger();s.advance(obs(loc='Workshop, room'))
        for _ in range(4):
            s.choose('enter corridor','travel');s.advance(obs(loc='Workshop, corridor',dark=True))
            self.assertNotIn('net_cycle_without_gain',kinds(s,'enter room'))
            s.choose('enter room','escape');s.advance(obs(loc='Workshop, room'))
        self.assertIn('net_cycle_without_gain',kinds(s,'enter corridor'))
    def test_changed_materials_allow_return_to_workstation(self):
        s=Ledger();s.advance(obs(loc='Workshop, room'))
        for i in range(4):
            s.choose('enter corridor','collect');s.advance(obs({'wire':i+1},loc='Workshop, corridor'))
            self.assertNotIn('net_cycle_without_gain',kinds(s,'enter room'))
            s.choose('enter room','return');s.advance(obs({'wire':i+1},loc='Workshop, room'))
    def test_repeat_combat_not_generic_cycle_veto(self):
        s=Ledger();s.advance(obs())
        for _ in range(5):s.choose('attack enemy','fight');s.advance(obs(feedback='I attacked enemy for 2 damage.'))
        self.assertNotIn('net_cycle_without_gain',kinds(s,'attack enemy'))
    def test_non_equippable_objective_invalidated(self):
        s=Ledger();s.advance(obs({'material':1}));g=goal(s);s.install_objective('equip material',g)
        s.choose('equip material','try',g);s.advance(obs({'material':1},feedback='Cannot equip material, it is not equippable.'))
        self.assertEqual(s.objective['status'],'contradicted_by_observation');self.assertIn('observed_non_equippable',kinds(s,'equip material'))
        self.assertFalse(s.install_objective('equip material',g));self.assertIsNone(s.local_candidate(g))
    def test_fresh_model_replaces_old_queue(self):
        s=Ledger();s.advance(obs({'ore':1},near={'wire':1},feedback='It can be used to craft: device (1 ore, 1 wire)'));g=goal(s);s.install_objective('craft 1 device',g)
        s.queue=['pick up wire'];action,_,record=s.dispatch_fresh([{'actions':['enter corridor']}],g)
        self.assertEqual(action,'enter corridor');self.assertEqual(record['source'],'fresh_model')
    def test_written_effect_persists_then_invalidates(self):
        s=Ledger();s.advance(obs({'page':1,'pen':1}));s.choose('write HELLO page','write');s.advance(obs({'page':1,'pen':1},feedback='I wrote on page: HELLO'))
        s.choose('wait','wait');s.advance(obs({'page':1,'pen':1}));self.assertIn('already_observed_write_effect',kinds(s,'write HELLO page'))
        s.advance(obs({'page':1,'pen':1},feedback='THE LAWS REWRITE'));self.assertNotIn('already_observed_write_effect',kinds(s,'write HELLO page'))
    def test_drop_and_reacquire_does_not_keep_resetting_progress(self):
        s=Ledger();s.advance(obs(near={'wire':1},feedback='It can be used to craft: device (1 wire)'));g=goal(s);s.install_objective('craft 1 device',g)
        s.choose('pick up wire','prepare',g);s.advance(obs({'wire':1}));best=s.last_useful_step
        for _ in range(3):
            s.choose('drop wire','release',g);s.advance(obs(near={'wire':1}))
            s.choose('pick up wire','prepare again',g);s.advance(obs({'wire':1}))
        self.assertEqual(s.last_useful_step,best)
    def test_one_recovery_then_bounded_stop_without_novel_gain(self):
        s=Ledger();s.advance(obs());requested=0;stopped=None
        for i in range(70):
            try:requested+=bool(s.request_replan_if_needed())
            except ScreenStopped:stopped=s.step;break
            s.choose('wait','new explanation '+str(i));s.advance(obs())
        self.assertEqual(requested,1);self.assertIsNotNone(stopped);self.assertLessEqual(stopped,53)
    def test_real_gain_resets_recovery_grace(self):
        s=Ledger();s.advance(obs())
        for _ in range(5):s.choose('wait','wait');s.advance(obs())
        self.assertTrue(s.request_replan_if_needed());s.choose('enter corridor','new route');s.advance(obs(loc='Workshop, corridor'))
        self.assertIsNone(s.replan_at);self.assertEqual(s.last_useful_step,s.step)
    def test_recovery_releases_stale_objective_without_erasing_task(self):
        s=Ledger();s.advance(obs(feedback='It can be used to craft: device (1 wire)'));g=goal(s);s.install_objective('craft 1 device',g)
        for _ in range(4):s.choose('wait','stalled',g);s.advance(obs())
        self.assertTrue(s.request_replan_if_needed());self.assertEqual(s.objective['status'],'requires_replan')
        self.assertTrue(s.install_objective('enter corridor',g));self.assertEqual(s.tasks[g]['status'],'open')
    def test_local_first_requires_current_evidence_and_bounded_streak(self):
        s=Ledger();s.advance(obs(near={'ore':1}));g=goal(s);s.advance(obs(near={'ore':1}));s.queue=['pick up ore']
        self.assertEqual(s.local_candidate(g)[0],'pick up ore')
        s.local_streak=3;self.assertIsNone(s.local_candidate(g));s.local_streak=0
        s.advance(obs(dark=True));self.assertIsNone(s.local_candidate(g))
    def test_compact_packet_bounds_and_keeps_exact_literal(self):
        s=Ledger();s.advance(obs());g=goal(s,'Write `SIGMA-42` on the page.');s.focus=g
        s.negative_capabilities={str(i):{'evidence':{'step':1,'quote':'x'*1000}} for i in range(1000)}
        p=packet_for(s);encoded=json.dumps(p,ensure_ascii=False,separators=(',',':'))
        self.assertLessEqual(len(encoded),6000);self.assertIn('SIGMA-42',encoded);self.assertNotIn('x'*100,encoded)
        self.assertIn('negative_capabilities',p['omitted_projection_fields'])
    def test_evidence_is_reference_only_in_projection(self):
        self.assertEqual(short_refs({'detail':{'step':4,'quote':'a long observation'}}),{'detail':{'observation_step':4}})

if __name__=='__main__':unittest.main(verbosity=2)
