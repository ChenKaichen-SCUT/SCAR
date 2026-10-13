import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scar_stage19.tests.test_planning import obs, rule
from scar_stage20.controller import Controller20
from scar_stage20.agent import make_agent
from scar_stage20.evidence import snapshot, render
from scar_stage20.planning import parse_response, validate, FIELDS, SYSTEM, InterfaceError
from scar_stage20.run_errors import MethodStalled
from scar_stage20.acquisition import bound_store


def controller(observation=None):
    c=Controller20();c.set_goal('craft 1 widget','Craft and obtain at least 1 widget.')
    c.table.observe(observation or obs());c.blocker20=dict(kind='missing_target_recipe',item='widget')
    return c


def proposal(c,kind,target,entry=None):
    entry=entry or target
    records=snapshot(c,dict(step=c.table.state.get('step',0),text='fixture observation'))
    evidence=next(r['id'] for r in records if entry in r['names'] and r['kind'] not in ('goal','blocker'))
    return dict(type=kind,target=target,entry=entry,evidence_ids=[evidence],
        direction='Resolve the named public blocker through this public entry.',uncertainty=['unpublished conditions remain unknown'])


class CaptureProvider:
    def __init__(self,agent=None,fail=False):self.calls=[];self.agent=agent;self.fail=fail
    def generate(self,**kwargs):
        from scar.providers.deepseek import ModelResponseError
        self.calls.append(kwargs)
        if self.fail:raise ModelResponseError('Three audited API/parse attempts failed')
        c=self.agent.controller
        names=[n for n in sorted(c.visible()) if n not in c.table.inspected]
        p=proposal(c,'INSPECT_OBJECT',names[0])
        return dict(parsed=p,response=json.dumps(p),num_input_tokens=0,num_output_tokens=0)


class MechanismTests(unittest.TestCase):
    def test_schema_has_no_completion(self):
        c=controller(obs(ground='1 ore'));p=proposal(c,'INSPECT_OBJECT','ore')
        out,events=parse_response(json.dumps(p));self.assertEqual(out,p);self.assertEqual(events,[])
        self.assertNotIn('completion',FIELDS)

    def test_normalization_does_not_change_target_or_reason(self):
        c=controller(obs(ground='1 ore'));p=proposal(c,'INSPECT_OBJECT','ore');raw=copy.deepcopy(p)
        raw['subgoal_type']=raw.pop('type');raw['completion']='ARRIVED';raw['uncertainty']='unknown'
        out,events=parse_response('```json\n'+json.dumps(raw)+'\n```')
        self.assertEqual(out['target'],p['target']);self.assertEqual(out['direction'],p['direction'])
        self.assertEqual(len(events),4)

    def test_ambiguous_json_duplicate_alias_and_fake_action_rejected(self):
        for text in ['{"target":"a","target":"b"}','{"action":"wait"}',
                     '{"type":"INSPECT_OBJECT","subgoal_type":"EXPLORE_FRONTIER"}',
                     '{"direction":"copy "unescaped" map"}']:
            with self.assertRaises(InterfaceError):parse_response(text)

    def test_unknown_evidence_is_decision_rejection_not_parse_error(self):
        c=controller(obs(ground='1 ore'));p=proposal(c,'INSPECT_OBJECT','ore');p['evidence_ids']=['Eunknown']
        validate(p);r=c.accept(p);self.assertFalse(r['accepted']);self.assertEqual(r['reason'],'unknown_evidence_id')

    def test_future_unrelated_and_inaccessible_evidence(self):
        c=controller(obs(ground='1 ore, 1 cloth'));p=proposal(c,'INSPECT_OBJECT','ore')
        c.evidence20[p['evidence_ids'][0]]['observed_step']=99
        self.assertEqual(c.accept(p)['reason'],'future_evidence_id')
        p=proposal(c,'INSPECT_OBJECT','cloth');p['entry']=p['target']='ore'
        self.assertEqual(c.accept(p)['reason'],'evidence_unrelated_to_execution_entry')
        c=controller();c.table.places['island']={'objects':{'ore':1},'step':0}
        c.evidence20['Eold']=dict(id='Eold',kind='public_location',names=['ore'],observed_step=0,first_seen_step=0)
        p=dict(type='INSPECT_OBJECT',target='ore',entry='ore',evidence_ids=['Eold'],direction='inspect',uncertainty=[])
        self.assertFalse(c.accept(p)['accepted'])

    def test_snapshot_stable_ids_and_deep_copy(self):
        c=controller(obs(ground='1 ore'));rule(c,'widget (1 ore)');c.table.observe(obs(ground='1 ore',step=2))
        text,a=render(c,obs(ground='1 ore',step=2),[]);_,b=render(c,obs(ground='1 ore',step=2),[])
        self.assertEqual(a,b);saved=copy.deepcopy(a)
        c.table.recipes['widget']['source']='changed';self.assertEqual(a,saved)

    def test_known_execution_no_llm(self):
        p=CaptureProvider(fail=True);a=make_agent(p,game='robot_kingdom');p.agent=a
        a.initialize_episode([],'craft 1 widget','Craft widget.');rule(a.controller,'widget (2 ore)')
        action,*_=a.act(obs(ground='2 ore',step=2));self.assertEqual(action,'pick up ore');self.assertEqual(p.calls,[])

    def test_gap_actual_new_schema(self):
        p=CaptureProvider();a=make_agent(p,game='robot_kingdom');p.agent=a
        a.initialize_episode([],'craft 1 widget','Craft widget.')
        action,*_=a.act(obs(ground='1 ore'));self.assertEqual(action,'inspect ore')
        self.assertEqual(len(p.calls),1);self.assertNotIn('completion',p.calls[0]['required'])

    def test_three_bad_replies_fallback_to_actual_exploration(self):
        p=CaptureProvider(fail=True);a=make_agent(p,game='robot_kingdom');p.agent=a
        a.initialize_episode([],'craft 1 widget','Craft widget.')
        action,*_=a.act(obs(ground='1 ore'));self.assertEqual(action,'inspect ore')
        self.assertEqual(a.decision['planning_calls'][0]['status'],'interface_unavailable')
        self.assertEqual(a.controller.plan_calls20,1)

    def test_explicit_stall_has_no_wait_action(self):
        p=CaptureProvider(fail=True);a=make_agent(p,game='robot_kingdom');p.agent=a
        a.initialize_episode([],'craft 1 widget','Craft widget.')
        o=obs(neighbors='no neighboring areas')
        with self.assertRaises(MethodStalled):a.act(o)
        self.assertEqual(len(p.calls),2);self.assertIsNone(a.decision['executed_action'])
        self.assertEqual(a.controller.exploration_spent,0)

    def test_context_replanning_bounded_and_time_alone_does_not_reset(self):
        c=controller();c.start_request();self.assertTrue(c.can_request());c.start_request()
        self.assertFalse(c.can_request());c.table.state['step']+=1;self.assertFalse(c.can_request())
        c.table.state['ground']={'ore':1};self.assertTrue(c.can_request())

    def test_acquire_multistep_until_real_demand(self):
        c=controller();rule(c,'widget (2 ore)');c.table.observe(obs(step=2))
        c.table.places['hall']={'objects':{'ore':2},'step':1}
        self.assertTrue(c.accept(proposal(c,'ACQUIRE_MATERIAL','ore'))['accepted'])
        a=c.choose(obs(step=2));self.assertEqual(a,'enter hall')
        o=obs('I entered hall.',location='hall',ground='2 ore',neighbors='room',step=3)
        c.observe(obs(step=2),a,o);self.assertIsNotNone(c.intent20)
        a=c.choose(o);self.assertEqual(a,'pick up ore')
        o2=obs('I picked up ore.',location='hall',ground='1 ore',hands='1 ore',neighbors='room',step=4)
        c.observe(o,a,o2);self.assertIsNotNone(c.intent20)
        a=c.choose(o2);self.assertEqual(a,'pick up ore')
        o3=obs('I picked up ore.',location='hall',hands='2 ore',neighbors='room',step=5)
        c.observe(o2,a,o3);self.assertIsNone(c.intent20)
        self.assertEqual(c.intent_log20[-1]['steps'],3);self.assertEqual(c.target,'craft 1 widget')

    def test_locate_arrival_not_completion_then_native_discovery(self):
        c=controller();rule(c,'widget (1 ore)');c.table.observe(obs(step=2))
        c.table.knowledge.observe(obs('Cannot craft widget. Missing necessary furnace in the current area.',step=2),'craft 1 widget')
        c.table.sync();c.blocker20=dict(kind='missing_area_object_path',item='furnace')
        self.assertTrue(c.accept(proposal(c,'LOCATE_PRECONDITION','furnace','hall'))['accepted'])
        a=c.choose(obs(step=2));self.assertEqual(a,'enter hall')
        o=obs('I entered hall.',location='hall',ground='1 stone',neighbors='room',step=3)
        c.observe(obs(step=2),a,o);self.assertIsNotNone(c.intent20)
        a=c.choose(o);self.assertEqual(a,'inspect stone')
        after=obs('I inspected stone:\nIt can be used to craft: furnace (made of stone).',location='hall',ground='1 stone',step=4)
        c.observe(o,a,after);self.assertEqual(c.intent_log20[-1]['status'],'completed')

    def test_craft_prerequisite_multistep_and_actual_feedback(self):
        c=controller();rule(c,'widget (1 ore), furnace (1 stone)');c.table.observe(obs(step=2))
        c.table.knowledge.observe(obs('Cannot craft widget. Missing necessary furnace in the current area.',step=2),'craft 1 widget');c.table.sync()
        c.table.places['hall']={'objects':{'stone':1},'step':1};c.blocker20=dict(kind='missing_area_object_path',item='furnace')
        self.assertTrue(c.accept(proposal(c,'CRAFT_PRECONDITION','furnace','stone'))['accepted'])
        a=c.choose(obs(step=2));self.assertEqual(a,'enter hall')
        o=obs('I entered hall.',location='hall',ground='1 stone',step=3);c.observe(obs(step=2),a,o)
        a=c.choose(o);self.assertEqual(a,'pick up stone')
        after=obs('I picked up stone.',location='hall',hands='1 stone',step=4);c.observe(o,a,after)
        a=c.choose(after);self.assertTrue(a.startswith('craft '))
        last=obs('I successfully crafted 1 furnace. It is now on the ground.',location='hall',ground='1 furnace',step=5)
        c.observe(after,a,last);self.assertEqual(c.intent_log20[-1]['status'],'completed')

    def test_suspend_resume_serialize_and_original_goal(self):
        c=controller(obs(ground='1 ore'));rule(c,'widget (2 ore)');c.table.observe(obs(ground='1 ore',step=2))
        c.accept(proposal(c,'ACQUIRE_MATERIAL','ore'));ident=c.intent20['id'];c.suspend_intent('fixture blocked')
        d=Controller20.from_dict(json.loads(json.dumps(c.to_dict())))
        o=obs(ground='2 ore',step=3)
        self.assertEqual(c.choose(o),d.choose(o));self.assertEqual(c.to_dict(),d.to_dict())
        self.assertEqual(c.intent20['id'],ident);self.assertIn('resumed',[x['event'] for x in c.lifecycle20])
        self.assertEqual(c.target,'craft 1 widget')

    def test_missing_area_object_retains_unknown_type_and_no_leak(self):
        c=controller();rule(c,'widget (1 ore)');o=obs(hands='1 ore',step=2);c.table.observe(o)
        after=obs('Cannot craft widget. Missing necessary furnace in the current area.',hands='1 ore',step=3)
        c.observe(o,'craft 1 widget',after)
        self.assertEqual(c.preconditions20['widget:furnace']['object_type'],'UNKNOWN');self.assertNotIn('furnace',c.table.recipes)
        self.assertFalse(c.retry_allowed('craft 1 widget'))

    def test_known_station_and_cycle_guard(self):
        c=controller();rule(c,'widget (1 ore), furnace (1 widget)');c.table.observe(obs(hands='1 ore',step=2))
        c.table.knowledge.observe(obs('Cannot craft widget. Missing necessary furnace in the current area.',step=2),'craft 1 widget');c.table.sync()
        self.assertIsNone(c.known_step('furnace',1,('widget',),ground=True))
        c.table.places['hall']={'objects':{'furnace':1},'step':1}
        self.assertEqual(c.choose(obs(hands='1 ore',step=2)),'enter hall')

    def test_unexecuted_preview_no_probe_or_fifo_pollution(self):
        c=controller(obs(ground='1 ore'));p=proposal(c,'INSPECT_OBJECT','ore')
        before=(c.exploration_spent,copy.deepcopy(c.probes),copy.deepcopy(c.queue))
        c.accept(p);self.assertEqual(before,(c.exploration_spent,c.probes,c.queue))
        c.choose(obs(ground='1 ore'));self.assertEqual(c.exploration_spent,1)
        self.assertTrue(c.audit20['transaction']['attempts_unchanged'])

    def test_bounded_acquisition_P3_and_no_goal_reset(self):
        c=controller();rule(c,'widget (2 ore)');c.table.observe(obs(ground='17 ore',equipment='1 bag',step=2))
        c.table.inventory='bag';c.table.containers['bag']=dict(counts={},load=0,capacity=20,location='room',step=2)
        self.assertEqual(bound_store(c,'store 17 ore inventory')[0],'store 2 ore inventory')
        self.assertEqual(c.choose(obs(ground='1 widget',step=3)),'pick up widget')
        self.assertEqual(c.audit20['internal_horizon'],100)

    def test_paid_response_cache_and_failed_attempts_not_resampled(self):
        from scar_stage20.provider import SharedDeepSeekProvider
        from scar_stage20.config import PROVIDER
        from scar.providers.deepseek import ModelResponseError
        c=controller(obs(ground='1 ore'));p=proposal(c,'INSPECT_OBJECT','ore')
        class Response:
            def model_dump(self):return dict(choices=[dict(message=dict(content=json.dumps(p)),finish_reason='stop')],
                usage=dict(prompt_tokens=10,completion_tokens=10,prompt_cache_hit_tokens=0,total_tokens=20))
        with tempfile.TemporaryDirectory() as directory, patch('openai.OpenAI') as client:
            root=Path(directory);key=root/'key';key.write_text('sk-'+'x'*32)
            client.return_value.chat.completions.create.return_value=Response()
            provider=SharedDeepSeekProvider(root/'run',root/'budget.sqlite',key,PROVIDER)
            kwargs=dict(user_prompt='fixture',system_prompt=SYSTEM,required=FIELDS,phase='subgoal',validator=validate)
            provider.begin_step(1);first=provider.generate(**kwargs)
            reloaded=SharedDeepSeekProvider(root/'run',root/'budget.sqlite',key,PROVIDER);reloaded.begin_step(1)
            self.assertEqual(reloaded.generate(**kwargs),first);self.assertEqual(client.return_value.chat.completions.create.call_count,1)
            with self.assertRaises(RuntimeError):reloaded.begin_step(1);reloaded.generate(**dict(kwargs,user_prompt='changed'))
            class Invalid(Response):
                def model_dump(self):
                    v=super().model_dump();v['choices'][0]['message']['content']='{broken';return v
            client.return_value.chat.completions.create.return_value=Invalid()
            with patch('scar_stage20.provider.time.sleep'):
                provider.begin_step(2)
                with self.assertRaises(ModelResponseError):provider.generate(**kwargs)
                again=SharedDeepSeekProvider(root/'run',root/'budget.sqlite',key,PROVIDER);again.begin_step(2)
                with self.assertRaises(ModelResponseError):again.generate(**kwargs)
            self.assertEqual(client.return_value.chat.completions.create.call_count,4)
            self.assertEqual(len((root/'run/requests.jsonl').read_text().splitlines()),4)


if __name__=='__main__':unittest.main()
