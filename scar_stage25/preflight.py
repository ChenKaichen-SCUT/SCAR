"""Synthetic contracts and historical offline threshold description."""
import copy
import json
import tempfile
import unittest
from .common import *
from .integration import make_agent
from agents.agc_v2.control import Control,THRESHOLD,INVALID_MESSAGE
from agents.agc.agent import DecisionUnavailable
from scar_stage24.preflight import obs,proposal,Fake

class Contracts(unittest.TestCase):
    def test_confidence_decay_and_recovery(self):
        c=Control();c.initialize(obs());c.accept_goal(proposal(),1,True)
        for n in range(1,9):c.progress(obs(n-1),'wait',obs(n,'I waited for a while.'),n)
        self.assertLess(c.goal.confidence,THRESHOLD);self.assertEqual(c.goal.status,'SUSPICIOUS')
        old=c.goal.confidence
        c.progress(obs(8),'inspect pebble',obs(9,'A new visible object detail.'),9)
        self.assertGreater(c.goal.confidence,old)

    def test_new_goals_not_forced_or_blocked(self):
        c=Control();c.initialize(obs());c.accept_goal(proposal(),1,True)
        result=c.assess(proposal(goal='Inspect a different visible surface'),obs(),True,2)
        self.assertFalse(result['hard']);self.assertFalse(result['goal_review'])
        self.assertEqual(c.goal.goal_description,proposal()['goal_description'])

    def test_unverified_quote_is_not_action_rejection_or_laundered(self):
        c=Control();c.initialize(obs());p=proposal(quote='An unsupported invented statement.')
        r=c.assess(p,obs(),True,1);self.assertFalse(r['hard']);self.assertFalse(r['evidence_verified'])
        c.accept_goal(p,1,False);self.assertLess(c.goal.confidence,THRESHOLD)
        self.assertFalse(c.evidence_verified(p['goal_evidence'],obs()))
        self.assertEqual(c.assess(p,obs(),True,2)['decision'],'RECONSIDER')

    def test_failed_action_requires_same_context(self):
        c=Control();c.initialize(obs())
        for n in [1,2]:c.progress(obs(n-1),'pick up pebble',obs(n,'Cannot pick up pebble, not enough space in hand.'),n)
        p=proposal('pick up pebble')
        self.assertTrue(c.assess(p,obs(),True,3)['hard'])
        self.assertFalse(c.assess(p,obs(hands='1 other'),True,3)['hard'])

    def test_retry_only_message_and_checkpoint(self):
        from games.base.agent import Agent
        with tempfile.TemporaryDirectory() as tmp:
            fake=Fake([proposal('write note on paper_7'),proposal('write note on paper_7'),proposal()])
            a=make_agent(None,42,fake,Path(tmp),base=Agent);a.initialize_official(obs())
            action,_,_,_=a.act(obs());self.assertEqual(action,'inspect pebble');self.assertEqual(len(fake.calls),3)
            self.assertEqual(fake.calls[1][1],fake.calls[0][1]+'\n\n'+INVALID_MESSAGE)
            self.assertEqual(fake.calls[2][1],fake.calls[1][1]);self.assertEqual(a.decision['action_retry_calls'],2)
            a.observe_transition(obs(),action,obs(1,'A new visible object detail.'));a.save_memory(tmp)
            b=make_agent(None,42,Fake([]),Path(tmp),base=Agent);b.load_memory(tmp)
            self.assertEqual(a.control.to_dict(),b.control.to_dict());self.assertEqual(a.short_term_memory,b.short_term_memory)

    def test_four_invalid_responses_terminate(self):
        from games.base.agent import Agent
        with tempfile.TemporaryDirectory() as tmp:
            fake=Fake(['bad']*4);a=make_agent(None,42,fake,Path(tmp),base=Agent);a.initialize_official(obs())
            with self.assertRaises(DecisionUnavailable):a.act(obs())
            self.assertEqual(len(fake.calls),4);self.assertIsNone(a.decision['executed_action'])

    def test_confidence_review_never_supplies_replacement(self):
        from games.base.agent import Agent
        with tempfile.TemporaryDirectory() as tmp:
            p=proposal(quote='An unsupported invented statement.');a=make_agent(None,42,Fake([p,p]),Path(tmp),base=Agent);a.initialize_official(obs())
            a.control.accept_goal(p,0,False);action,_,_,_=a.act(obs())
            self.assertEqual(action,p['action']);self.assertEqual(a.decision['confidence_review_calls'],1)
            self.assertTrue(a.decision['bounded_soft_release']);self.assertFalse(a.decision['controller_generated_action'])

    def test_combined_review_and_repairs_are_bounded(self):
        from games.base.agent import Agent
        with tempfile.TemporaryDirectory() as tmp:
            p=proposal(quote='An unsupported invented statement.')
            fake=Fake([p,'bad','bad','bad',p]);a=make_agent(None,42,fake,Path(tmp),base=Agent);a.initialize_official(obs())
            a.control.accept_goal(p,0,False);action,_,_,_=a.act(obs())
            self.assertEqual(action,p['action']);self.assertEqual(len(fake.calls),5)
            self.assertEqual(a.decision['confidence_review_calls'],1);self.assertEqual(a.decision['action_retry_calls'],3)

    def test_no_game_or_hidden_state_dependencies(self):
        import ast
        forbidden=['games.generated','reward','quest_progress','main_quest','remnant','metropolis','remy','oak_rod','copper_sword','page_gnawer']
        for p in (ROOT/'agents/agc_v2').glob('*.py'):
            text=p.read_text();ast.parse(text);self.assertFalse(any(s in text for s in forbidden),p)

def threshold_audit():
    """Feed saved v1 public observations, not alternate model trajectories."""
    import agents.agc_v2.control as module
    records=[]
    for threshold in [.2,.4,.6]:
        module.THRESHOLD=threshold
        for game in GAMES:
            folder=ROOT/'results/stage24'/('runs' if game=='metropolis' else 'resumed/runs')/f'{game}__AGC'
            rr=rows(folder/'trajectory.jsonl.gz');c=Control();c.initialize(read(folder/'initial_public.json')['observation']);low=[]
            for r in rr:
                p=r['decision']['attempts'][-1]['proposal'];verified=c.evidence_verified(p.get('goal_evidence'),r['observation'])
                check=c.assess(p,r['observation'],True,r['step'])
                if check['goal_review']:low.append(r['step'])
                c.accept_goal(p,r['step'],verified);c.progress(r['observation'],r['action'],r['feedback'],r['step']);c.events.clear()
            records.append(dict(threshold=threshold,game=game,review_steps=low,scope='Off-policy fixed-action pass only; no counterfactual performance estimate.'))
    module.THRESHOLD=THRESHOLD
    write(RESULTS/'offline_threshold_audit.json',dict(selected=.4,selection='Middle suggested value fixed before this audit, not chosen by reward or number of triggers.',rows=records,new_model_calls=0))

def main():
    offline();r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Contracts))
    write(RESULTS/'preflight.json',dict(passed=r.wasSuccessful(),tests=r.testsRun,failures=len(r.failures),errors=len(r.errors),new_model_calls=0))
    if not r.wasSuccessful():raise SystemExit(1)
    threshold_audit()

if __name__=='__main__':main()
