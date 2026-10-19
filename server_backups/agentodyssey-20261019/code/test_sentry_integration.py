"""Offline tests against official Sentry; no API or environment rollout."""
import json
import unittest
from Sentry import SentryRunner,agent_step_from_parts
from Sentry.config import SentryConfig,ModelConfig

NO={'intervention_needed':False,'failure_type':'no_failure','retrieval_labels':[],
    'local_evidence':[],'diagnosis':'No local failure is established.'}
YES={'intervention_needed':True,'failure_type':'progress_failure',
     'retrieval_labels':['repetition_or_looping'],'local_evidence':['The same search repeats without new evidence.'],
     'diagnosis':'Repeated search does not advance the objective.'}
class Judge:
    model='deepseek-flash'
    def __init__(self,answers):self.answers=iter(answers);self.calls=[]
    def __call__(self,prompt,**kw):
        assert kw=={'temperature':0.0,'max_tokens':4096,'response_format':{'type':'json_object'}}
        self.calls.append(prompt)
        return json.dumps(next(self.answers))
def runner(answers):
    judge=Judge(answers)
    r=SentryRunner(judge,SentryConfig(model=ModelConfig(model='deepseek-flash')),capture_runtime_events=True)
    r.start_task(objective='Locate the requested resource.',action_schema='inspect <target>')
    return r,judge
def cycle(n,valid=True,accepted=True):
    return agent_step_from_parts(step_id=n,reasoning='Look for new information.',raw_action='inspect container',
        observation='A resource location is now visible.',schema_valid=valid,
        schema_error=None if valid else 'Expected exactly one target.',accepted_by_environment=accepted)
class OfficialTests(unittest.TestCase):
    def test_semantic_denial_not_routed_to_schema_failure(self):
        r,j=runner([NO]);result=r.step(cycle(0,accepted=False))
        self.assertIsNone(result);self.assertEqual(len(j.calls),1)
    def test_hard_repair_is_not_stored_as_lesson(self):
        r,j=runner([]);prompt=r.step(cycle(0,valid=False,accepted=False))
        self.assertEqual(prompt.route,'hard_repair');self.assertEqual(len(j.calls),0)
        r.step(cycle(1),terminal=True)
        self.assertTrue(r.guard.last_escape_result.escaped)
        self.assertEqual(r.guard.playbook.entries,[]);r.finalize()
    def test_soft_recovery_verified_at_exactly_ten_cycles(self):
        update={'failure_type':'progress_failure','retrieval_labels':['repetition_or_looping'],
                'subtype':'repeated search','trigger_pattern':'The same search yields no new evidence.',
                'repair_principle':'Use the observed resource location instead of repeating the search.'}
        r,j=runner([YES,{'status':'resolved','justification':'The agent used the discovered location.',
                          'evidence':['The recovery observations show a new resource.']},update])
        self.assertEqual(r.step(cycle(0)).route,'soft_repair')
        for n in range(1,10):
            self.assertIsNone(r.step(cycle(n)))
        self.assertEqual(len(j.calls),1);self.assertEqual(r.guard.playbook.entries,[])
        r.step(cycle(10),terminal=True)
        self.assertEqual(len(j.calls),3);self.assertEqual(len(r.guard.playbook.entries),1)
        r.finalize()
    def test_incomplete_recovery_cannot_update_playbook(self):
        r,j=runner([YES]);r.step(cycle(0));r.step(cycle(1),terminal=True);r.finalize()
        self.assertEqual(len(j.calls),1);self.assertEqual(r.guard.playbook.entries,[])
        self.assertTrue(any(e['type']=='verification_incomplete' for e in r.guard.drain_runtime_events()))
if __name__=='__main__':unittest.main(verbosity=2)
