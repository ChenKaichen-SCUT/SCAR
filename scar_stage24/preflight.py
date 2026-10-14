"""Synthetic behavioral contracts, not reward-driven development trials."""
import copy
import json
import tempfile
import unittest
from .common import *
from .integration import make_agent
from agents.agc.control import Control
from agents.agc.state import extract
from agents.agc.agent import DecisionUnavailable

def obs(step=0,feedback='',location='yard',hands='nothing'):
    return dict(step=step,text=f'Current Time: day {step}\nCurrent Location: test_site, {location}\n\n{feedback}\n\nI am holding {hands}.\nI have equipped nothing.\nI see 1 pebble near me.\nI see no one nearby.\nMy health is at {100-step}.\nNeighboring areas: workshop.')

def proposal(action='inspect pebble',goal='Learn about the visible object',quote='I see 1 pebble near me.'):
    return dict(action=action,reasoning='Choose from the public observations.',goal_description=goal,goal_evidence=quote)

class Fake:
    def __init__(self,values):self.values=iter(values);self.calls=[]
    def generate(self,user_prompt,system_prompt=None,**kw):
        self.calls.append([system_prompt,user_prompt]);r=next(self.values)
        return dict(response=json.dumps(r) if isinstance(r,dict) else r,num_input_tokens=5,num_output_tokens=7)

class Contracts(unittest.TestCase):
    def test_time_health_wait_are_not_progress(self):
        c=Control();c.initialize(obs())
        c.adopt('Learn about the visible object',[dict(quote='I see 1 pebble near me.')],0,'model')
        for n in range(1,10):r=c.progress(obs(n-1), 'wait',obs(n,'I waited for a while.'),n)
        self.assertFalse(r['informative']);self.assertTrue(c.stagnant());self.assertEqual(c.goal.status,'SUSPICIOUS')

    def test_failure_context_not_global_action_ban(self):
        c=Control();c.initialize(obs())
        for n in range(1,4):c.progress(obs(n-1),'pick up pebble',obs(n,'Cannot pick up pebble. Hands full.'),n)
        p=proposal('pick up pebble');a=c.assess(p,obs(),True,4)
        self.assertIn('repeated_failure_in_same_public_context',a[1])
        self.assertEqual(c.assess(p,obs(hands='1 pebble'),True,4)[0],'EXECUTE')
        self.assertLessEqual(len(c.failures),12)

    def test_explicit_replacement_and_reached_goal(self):
        c=Control();c.initialize(obs(feedback='Required action: `enter workshop`'))
        c.progress(obs(),'inspect pebble',obs(1,'Required action: `pick up pebble`'),1)
        self.assertTrue(any(e.get('after')=='INVALID' for e in c.events))
        c.adopt('enter yard',[dict(quote='Current Location: test_site, yard')],2,'model')
        c.ingest_goal(extract(obs()),2);self.assertEqual(c.goal.status,'COMPLETED')

    def test_grounding_and_invalid_goal(self):
        c=Control();c.initialize(obs());c.adopt('inspect pebble',[dict(quote='I see 1 pebble near me.')],0,'model')
        c.status('INVALID',1,'synthetic contradictory evidence')
        self.assertTrue(c.assess(proposal(goal='inspect pebble'),obs(),True,1)[2])
        self.assertTrue(c.assess(proposal(quote='A hidden recipe answer.'),obs(),True,1)[2])

    def test_only_model_action_and_bounded_reconsider(self):
        from games.base.agent import Agent
        with tempfile.TemporaryDirectory() as tmp:
            fake=Fake(['bad',proposal()]);agent=make_agent(None,fake,Path(tmp),base=Agent);agent.initialize_official(obs())
            action,tin,tout,_=agent.act(obs());self.assertEqual((action,tin,tout),('inspect pebble',10,14))
            self.assertEqual(len(fake.calls),2);self.assertFalse(agent.decision['controller_generated_action'])
            agent.observe_transition(obs(),action,obs(1,'A previously unknown surface marking.'))
            agent.save_memory(tmp);restored=make_agent(None,Fake([proposal()]),Path(tmp),base=Agent);restored.load_memory(tmp)
            self.assertEqual(agent.control.to_dict(),restored.control.to_dict());self.assertEqual(agent.short_term_memory,restored.short_term_memory)
            other=make_agent(None,Fake(['bad','bad']),Path(tmp),base=Agent);other.initialize_official(obs())
            with self.assertRaises(DecisionUnavailable):other.act(obs())
            self.assertEqual(len(other.llm.calls),2);self.assertIsNone(other.decision['executed_action'])

    def test_public_only_imports_and_no_game_literals(self):
        import ast
        forbidden=('games.generated','scar_stage18','scar_stage16','scar_stage23','reward','quest_progress')
        for path in (ROOT/'agents/agc').glob('*.py'):
            text=path.read_text();ast.parse(text)
            self.assertFalse(any(x in text for x in forbidden),path)
            self.assertFalse(any(x in text for x in ['remnant','metropolis','mark','remy','oak_rod','copper_sword','page_gnawer']),path)


def main():
    offline();result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Contracts))
    write(RESULTS/'preflight.json',dict(passed=result.wasSuccessful(),tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),new_model_calls=0,synthetic_only=True))
    if not result.wasSuccessful():raise SystemExit(1)

if __name__=='__main__':main()
