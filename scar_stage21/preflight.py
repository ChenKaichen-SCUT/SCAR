"""Zero-network engineering acceptance. Historical states are fixtures only."""
from .common import *
deny_network()
import copy
import json
import tempfile
import unittest
from pathlib import Path
from collections import Counter
from .controller import Controller21
from .recovery import Recovery, blocker_id
from . import knowledge
from .public import shadow, public_route
from .evidence import check, render
from .planning import parse_response, InterfaceError
from scar.io import digest

AUDIT=ROOT/'results/stage20_audit'


def migrated(raw, rows=(), through=None):
    c=Controller21.from_dict(raw)
    c.etbr21=Recovery();c.probe21=None;c.probe_log21=[]
    if rows:
        first=Controller21.from_dict(rows[0]['decision']['decision']['controller_before'])
        first.table.observe(rows[0]['observation'])
        c.etbr21.ingest(knowledge.facts(first),None,0,initial=True)
        for row in rows:
            if through is not None and row['step']>through:break
            before=Controller21.from_dict(row['decision']['controller'])
            before.observe(row['observation'],row['action'],row['feedback'])
            c.etbr21.ingest(knowledge.facts(before),row['action'],row['step'])
    else:c.etbr21.ingest(knowledge.facts(c),None,c.step16,initial=True)
    c.initial_evidence21=True
    return c


def fixtures():
    return [p for p in read_gzip(AUDIT/'planning_states.jsonl.gz') if p['old_evidence_reason']=='evidence_unrelated_to_execution_entry']


def generic_fact(kind='production_relation',subject='required',obj='source'):
    return dict(knowledge_type=kind,subject=subject,relation='public_requires',object=obj,provenance={'source':'synthetic_public_fixture'})


def generic_block(subject='required'):
    return dict(kind='missing_public_condition',subject=subject,parent='goal',public_entities=[subject],unresolved=True)


def entry():return dict(legal=True,attempted=False,transit_steps=0,entry='public_object')


class Tests(unittest.TestCase):
    def test_44_typed_binding(self):
        counts=Counter()
        for p in fixtures():
            c=migrated(p['controller']);before=c.to_dict();r=check(c,p['plan']['proposal'],require_prompt_ids=False)
            self.assertEqual(r['category'],p['shadow']['category']);self.assertEqual(c.to_dict(),before)
            counts[r['category']]+=1
        self.assertEqual(counts,{'I':32,'II':5,'III':7})

    def test_264_negative_controls(self):
        controls=[]
        for p in fixtures():
            for mode in ('unknown_entry','isolated_entry','locked_only_route','unknown_target','unknown_ID','future_ID'):
                c=migrated(p['controller']);proposal=copy.deepcopy(p['plan']['proposal'])
                if mode=='unknown_entry':proposal['entry']='__not_a_public_entry__'
                elif mode=='isolated_entry':
                    proposal['entry']='__isolated_public_place__';c.table.places[proposal['entry']]={'objects':{},'step':c.table.state['step']}
                elif mode=='locked_only_route':
                    name='__locked_public_frontier__';proposal['entry']=name
                    c.table.links.setdefault(c.table.state['location'],[]).append(name)
                    c.table.guards[c.table.state['location']+'->'+name]={'locked':True};c.table.state['hands']={}
                elif mode=='unknown_target':proposal['target']='__not_a_public_object__'
                elif mode=='unknown_ID':proposal['evidence_ids']=['Eunknown']
                else:c.evidence20[proposal['evidence_ids'][0]]['first_seen_step']=c.table.state['step']+1
                result=check(c,proposal,require_prompt_ids=False)
                self.assertFalse(result['hypothesis_accept'],(p['id'],mode,result))
                controls.append(dict(source=p['id'],mutation=mode,result=result))
        self.assertEqual(len(controls),264);write(RESULTS/'negative_controls.json',controls)

    def test_content_dedup(self):
        r=Recovery();self.assertEqual(len(r.ingest([generic_fact()],'inspect source',1)),1)
        self.assertFalse(r.ingest([generic_fact()],'inspect source',50))
    def test_initial_not_new(self):
        r=Recovery();r.ingest([generic_fact()],None,0,initial=True)
        self.assertIsNone(r.offer(generic_block(),[entry()],step=20,risk=False))
    def test_unrelated_no_credit(self):
        r=Recovery();r.ingest([generic_fact(subject='unrelated')],'inspect source',1)
        self.assertIsNone(r.offer(generic_block(),[entry()],step=20,risk=False))
    def test_same_evidence_no_second_credit(self):
        r=Recovery();r.ingest([generic_fact()],'inspect source',1)
        self.assertIsNotNone(r.offer(generic_block(),[entry()],step=20,risk=False))
        self.assertIsNone(r.offer(generic_block(),[entry()],step=21,risk=False))
    def test_same_evidence_other_blocker_no_credit(self):
        r=Recovery();r.ingest([generic_fact()],'inspect source',1)
        r.offer(generic_block(),[entry()],step=20,risk=False)
        b=generic_block();b['kind']='another_blocker'
        self.assertIsNone(r.offer(b,[entry()],step=21,risk=False))
    def test_two_per_blocker(self):
        r=Recovery();r.ingest([generic_fact(obj=str(i)) for i in range(5)],'inspect source',1)
        self.assertIsNotNone(r.offer(generic_block(),[entry()],step=20,risk=False))
        self.assertIsNotNone(r.offer(generic_block(),[entry()],step=21,risk=False))
        self.assertIsNone(r.offer(generic_block(),[entry()],step=22,risk=False))
    def test_six_global(self):
        r=Recovery()
        for i in range(7):
            r.ingest([generic_fact(subject=str(i))],'inspect source',i+1)
            result=r.offer(generic_block(str(i)),[entry()],step=20+i,risk=False)
            self.assertEqual(result is not None,i<6)
    def test_risk_blocks_credit(self):
        r=Recovery();r.ingest([generic_fact()],'inspect source',1)
        self.assertIsNone(r.offer(generic_block(),[entry()],step=20,risk=True))
    def test_environment_cap(self):
        r=Recovery();r.ingest([generic_fact()],'inspect source',1)
        self.assertIsNone(r.offer(generic_block(),[entry()],step=100,risk=False))
    def test_bounded_transit(self):
        r=Recovery();r.ingest([generic_fact()],'inspect source',1)
        self.assertIsNone(r.offer(generic_block(),[dict(entry(),transit_steps=4)],step=20,risk=False))
    def test_cost_guard(self):
        r=Recovery();r.ingest([generic_fact()],'inspect source',1)
        self.assertIsNone(r.offer(generic_block(),[entry()],step=20,risk=False,budget_available=False))
    def test_resolved_blocker(self):
        r=Recovery();r.ingest([generic_fact()],'inspect source',1)
        self.assertIsNone(r.offer(dict(generic_block(),unresolved=False),[entry()],step=20,risk=False))
    def test_recovery_roundtrip(self):
        r=Recovery();r.ingest([generic_fact()],'inspect source',1);r.offer(generic_block(),[entry()],step=20,risk=False)
        restored=Recovery.from_dict(json.loads(json.dumps(r.to_dict())))
        self.assertEqual(r.to_dict(),restored.to_dict())
        self.assertIsNone(restored.offer(generic_block(),[entry()],step=21,risk=False))
    def test_public_map_interface(self):
        r=Recovery();r.ingest([generic_fact('map_connection','required','new_place')],'enter room',1)
        self.assertIsNotNone(r.offer(generic_block(),[entry()],step=20,risk=False))
    def test_dialogue_condition_interface(self):
        r=Recovery();f=generic_fact('task_condition');f['provenance']={'source':'public_NPC_dialogue','utterance':'The gate requires a permit.'}
        r.ingest([f],'talk to public_npc',1)
        self.assertIsNotNone(r.offer(generic_block(),[entry()],step=20,risk=False))
    def test_public_task_stage_interface(self):
        r=Recovery();r.ingest([generic_fact('task_stage')],'read public_journal',1)
        self.assertIsNotNone(r.offer(generic_block(),[entry()],step=20,risk=False))
    def test_unsupported_text_unknown(self):
        self.assertEqual(knowledge.unsupported_narrative('arbitrary text')['status'],'UNKNOWN')
        r=Recovery();self.assertFalse(r.ingest([generic_fact('unparsed_story')],'talk',1))
    def test_schema_no_material_chain(self):
        p=dict(type='TEST_PUBLIC_HYPOTHESIS',target='required',entry='object',evidence_ids=['E1'],direction='test',uncertainty=['UNKNOWN'])
        self.assertEqual(parse_response(json.dumps(p))[0],p)
        p['type']='ACQUIRE_MATERIAL'
        with self.assertRaises(InterfaceError):parse_response(json.dumps(p))
    def test_prompt_bound(self):
        for p in fixtures():
            c=migrated(p['controller']);obs={'step':c.table.state['step'],'text':''}
            prompt,meta=render(c,obs)
            self.assertLessEqual(len(prompt),8000);self.assertLessEqual(len(meta['records']),24)
    def test_no_future_prompt_reference(self):
        p=fixtures()[0];c=migrated(p['controller']);c.request_evidence20=[]
        self.assertEqual(check(c,p['plan']['proposal'])['reason'],'evidence_not_in_current_request')
    def test_network_guard(self):
        import socket
        with self.assertRaises(RuntimeError):socket.create_connection(('invalid.test',443))
        self.assertEqual(NETWORK_ATTEMPTS,['blocked']);NETWORK_ATTEMPTS.clear()


def main():
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    if not result.wasSuccessful():raise SystemExit(1)
    regression=[]
    for p in fixtures():
        c=migrated(p['controller']);regression.append(dict(id=p['id'],proposal=p['plan']['proposal'],result=check(c,p['plan']['proposal'],require_prompt_ids=False)))
    write(RESULTS/'evidence_regression.json',regression)
    stalls=[];transit_cases=[]
    audit={s['task_id']:s for s in load(AUDIT/'stall_audit.json')}
    for state in read_gzip(AUDIT/'terminal_states.jsonl.gz'):
        tid=state['task_id'];rows=read_gzip(ROOT/'results/stage20/runs'/f'{tid}__SCAR20/trajectory.jsonl.gz')
        c=migrated(state['controller'],rows);c.blocker_key21=blocker_id(knowledge.blocker(c))
        entries=c.probe_entries()
        if audit[tid]['nonquota_omission_witnesses']:
            repaired=sorted({e['action'] for e in entries}&set(audit[tid]['nonquota_omission_witnesses']))
            assert repaired,(tid,entries)
            transit_cases.append(dict(task_id=tid,repaired_actions=repaired,entries=entries))
        before=c.to_dict();restored=Controller21.from_dict(json.loads(json.dumps(before)))
        a=c.choose(state['public_observation'],allow_fallback=True)
        assert a==restored.choose(state['public_observation'],allow_fallback=True) and c.to_dict()==restored.to_dict()
        if state['task']['target_item']=='cog_crossbow':
            assert a in ('enter courtyard','enter watchtower') and not c.etbr21.grants
        stalls.append(dict(task_id=tid,old_category=audit[tid]['categories'],new_action=a,normal_exploration=c.exploration_spent,
            grant=copy.deepcopy(c.etbr21.grants),check=copy.deepcopy(c.etbr21.last_check),risk=c.risk16,
            stage21_source=c.audit20.get('source'),controller_before=before,controller_after=c.to_dict()))
    assert len(transit_cases)==7
    gzip_rows(RESULTS/'stalled_shadow.jsonl.gz',stalls);write(RESULTS/'transit_regression.json',transit_cases)
    # Actual previously recorded same-state feedback, not a synthetic outcome.
    reopen=[]
    for branch in read_gzip(AUDIT/'counterfactual_results.jsonl.gz'):
        if (branch['task_id'].endswith('repair_kit') and branch['action']=='inspect rubble') or (branch['task_id'].endswith('sharpened_blade') and branch['action']=='inspect iron_bar'):
            s=next(s for s in stalls if s['task_id']==branch['task_id'])
            c=Controller21.from_dict(s['controller_before']);item=c.blocker20['item'];prior=c._known_path(item)
            c.observe(branch['before_observation'],branch['action'],branch['after_observation'])
            next_action=c.known_step(parse_goal(c),c.amount)
            assert not prior and c._known_path(item) and next_action
            reopen.append(dict(task_id=branch['task_id'],action=branch['action'],new_evidence=c.transition21['new_evidence'],next_known_action=next_action,
                provenance='same-state native branch previously recorded in Stage20A; no full task success inferred'))
    assert len(reopen)==2;write(RESULTS/'reopened_paths.json',reopen)
    historical=historical_execution_checks()
    smoke=agent_native_smoke()
    native=shadow_native_checks(stalls)
    assert not NETWORK_ATTEMPTS
    prior=load(RESULTS/'prior_manifest.json')['files'];assert all(sha(ROOT/n)==h for n,h in prior.items())
    receipt=dict(passed=True,unit_tests=result.testsRun,api_calls=0,tokens=0,cost_usd=0,network_attempts=0,
        evidence_regression=Counter(r['result']['category'] for r in regression),negative_controls=264,
        repaired_nonquota_tasks=len(transit_cases),stalled_shadow_states=len(stalls),reopened_public_paths=len(reopen),
        historical_deterministic_checks=historical,agent_smoke=smoke,stalled_native_checks=native,
        source_hashes={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'scar_stage21').rglob('*.py')})
    write(RESULTS/'preflight_local.json',receipt)
    print(json.dumps({k:v for k,v in receipt.items() if k!='source_hashes'},ensure_ascii=False))


def parse_goal(c):
    from scar_v3.state import parse_action
    return parse_action(c.target).target


def shadow_native_checks(stalls):
    from scar.environment import restore,state_digest,AGENT_ID
    states={s['task_id']:s for s in read_gzip(AUDIT/'terminal_states.jsonl.gz')}
    checks=[]
    for r in stalls:
        if not r['new_action']:continue
        state=states[r['task_id']];cp=ROOT/state['checkpoint']
        assert sha(cp/'physical.pkl')==state['checkpoint_pickle_sha256']
        with tempfile.TemporaryDirectory(prefix='scar21-shadow-native-') as d:
            env=restore(cp/'physical.pkl',Path(d));assert state_digest(env)==state['physical_state_hash']
            c=Controller21.from_dict(r['controller_after']);normal=c.exploration_spent
            obs,reward,done,info=env.step({AGENT_ID:r['new_action']});env.update_scores(reward)
            c.observe(state['public_observation'],r['new_action'],obs[AGENT_ID])
            roundtrip=Controller21.from_dict(json.loads(json.dumps(c.to_dict())))
            assert c.to_dict()==roundtrip.to_dict() and c.exploration_spent==normal<=18
            if r['grant']:
                assert len(c.etbr21.grants[-1]['actions'])==1
                assert c.etbr21.grants[-1]['transit_used']+c.etbr21.grants[-1]['probe_used']==1
            checks.append(dict(task_id=r['task_id'],action=r['new_action'],before_hash=state['physical_state_hash'],
                after_hash=state_digest(env),feedback=obs[AGENT_ID],outcome=c.transition21,
                formal_task_outcome_not_inferred=True))
    gzip_rows(RESULTS/'stalled_native_branches.jsonl.gz',checks)
    return dict(native_single_actions=len(checks),saved_rng=True,new_model_calls=0,checks_passed=True)


def historical_execution_checks():
    checks=[]
    from scar_v3.state import parse_action
    for stage in (18,19,20):
        for task in load(RESULTS/'tasks.json'):
            folder=ROOT/f'results/stage{stage}/runs'/f"{task['task_id']}__SCAR{stage}"
            if not load(folder/'summary.json')['success']:continue
            rows=read_gzip(folder/'trajectory.jsonl.gz')
            for row in rows:
                if not (row['success'] or row['metrics']['actual_production']):continue
                c=migrated(row['decision']['decision']['controller_before']);saved=c.to_dict()
                action=c.choose(row['observation'])
                copy_c=Controller21.from_dict(json.loads(json.dumps(saved)))
                assert action==copy_c.choose(row['observation']) and c.to_dict()==copy_c.to_dict()
                if action:assert c.assess(action)['status']!='REJECT'
                if row['success']:assert action and parse_action(action).target==task['target_item'],(stage,task['task_id'],action)
                # Stage18 can craft exploratory products whose relation to the
                # goal is not yet public. Do not demand that Stage21 select the
                # same exploration policy; separately exercise its inherited
                # deterministic executor on that publicly known product.
                executor=Controller21.from_dict(saved);executor.table.observe(row['observation'])
                product=parse_action(row['action']).target
                demand=executor.ownership(product)['lower_bound']+1
                known_action=executor.known_step(product,demand)
                if row['metrics']['actual_production'] and executor.table.recipes.get(product,{}).get('ingredients'):
                    assert known_action,(stage,task['task_id'],row['step'],'known executor lost')
                checks.append(dict(stage=stage,task_id=task['task_id'],step=row['step'],old_action=row['action'],new_action=action,
                    final_collection=bool(row['success']),same_action=action==row['action'],source=c.audit20.get('source'),
                    known_executor_action=known_action,selection_blocker=copy.deepcopy(c.blocker20)))
    write(RESULTS/'historical_execution_regression.json',checks)
    return dict(states=len(checks),success_tasks={str(s):len({c['task_id'] for c in checks if c['stage']==s}) for s in (18,19,20)},
        same_actions=sum(c['same_action'] for c in checks),scope='public known-action and checkpoint contract, not new full runs')


def agent_native_smoke():
    from .agent import make_method,decision_state
    from scar.environment import snapshot,restore,state_digest,AGENT_ID
    from scar_stage17.environment import create_initial
    from scar_stage17.evaluate import physical,native_step,transition
    class NoProvider:
        def generate(self,**kw):raise AssertionError('No model allowed in initial-action smoke')
    checks=[]
    # Two initial transitions per game exercise complete Agent and logging APIs.
    for game in ('robot_kingdom','quarantine'):
        task=next(t for t in load(RESULTS/'tasks.json') if t['game_name']==game)
        with tempfile.TemporaryDirectory(prefix='scar21-smoke-') as d:
            env,history=create_initial(game,task['initial_seed'],Path(d)/'initial')
            assert state_digest(env)==task['initial_state_hash']
            agent=make_method('SCAR21',game,NoProvider(),task['objective_text'],task['target_item'],history,Path(d)/'memory')
            env=restore(snapshot(env),Path(d)/'world',agent=agent)
            target=env.world.auxiliary['obj_name_to_id'][task['target_item']]
            for index in range(2):
                before=copy.deepcopy(env.obs[AGENT_ID]);a,*_=agent.act(before);p0=physical(env,target)
                (obs,reward,done,info),effect=native_step(env,a,target);env.update_scores(reward)
                agent.observe_transition(before,a,obs[AGENT_ID]);transition(p0,physical(env,target),a,obs[AGENT_ID],env.world)
                json.dumps(decision_state(agent,'SCAR21'));json.dumps(agent.controller.outcome20)
                cp=Path(d)/f'cp{index}';cp.mkdir();agent.save_memory(cp)
                restored=make_method('SCAR21',game,NoProvider(),task['objective_text'],task['target_item'],history,Path(d)/'other')
                restored.load_memory(cp);assert restored.controller.to_dict()==agent.controller.to_dict()
                checks.append(dict(game=game,step=index+1,action=a,state_hash=state_digest(env)))
    write(RESULTS/'native_smoke.json',checks)
    return dict(native_actions=len(checks),games=2,model_requests=0,agent_checkpoint_roundtrips=len(checks))


if __name__=='__main__':main()
