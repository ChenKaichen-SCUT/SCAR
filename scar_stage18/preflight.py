"""Zero-API historical states: six terminal harms plus all positive controls.

Only historical actions are replayed end-to-end. New decisions are ONE-step
branches; they are never reported as new episode success estimates.
"""
import argparse
import contextlib
import copy
import io
import json
import random
import tempfile
import unittest
import numpy as np
from pathlib import Path
from scar.environment import AGENT_ID, state_digest, restore, snapshot
from scar_stage17.environment import create_initial
from scar_stage17.evaluate import physical
from scar_stage14.knowledge import Knowledge
from scar_stage16.controller import restore_controller
from scar_stage17.preflight import MockProvider
from .controller import Controller18
from .agent import make_method
from .common import ROOT, RESULTS, load, write, read_gzip, gzip_rows, deny_network, sha
from .consequences import ConsequenceMemory, public_frame


def historical_controller(row, memory):
    legacy=restore_controller(row['decision']['decision']['controller_before'])
    c=Controller18()
    c.__dict__.update(copy.deepcopy(legacy.__dict__))
    c.consequences=copy.deepcopy(memory)
    return c


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--site',choices=['local','server'],default='local');args=parser.parse_args()
    deny_network()
    suite=unittest.defaultTestLoader.discover(str(ROOT/'scar_stage18/tests'))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    assert result.wasSuccessful()
    cf=read_gzip(ROOT/'results/stage17/diagnostics/counterfactual_local.jsonl.gz')
    lookup={(r['task_id'],r['step']):r for r in cf}
    tasks=load(RESULTS/'tasks.json');branches=[]; factual_steps=0; integration=[]
    for task in tasks:
        rows=read_gzip(ROOT/'results/stage17/runs'/f"{task['task_id']}__A0/trajectory.jsonl.gz")
        with tempfile.TemporaryDirectory(prefix='scar18-preflight-') as tmp:
            path=Path(tmp)
            with contextlib.redirect_stdout(io.StringIO()):
                env,history=create_initial(task['game_name'],task['initial_seed'],path/'initial')
            assert state_digest(env)==task['initial_state_hash']
            observer=Controller18()
            for h in history:observer.observe(h['before'],h['action'],h['after'])
            observer.set_goal('craft 1 '+task['target_item'],task['objective_text'])
            target=env.world.auxiliary['obj_name_to_id'][task['target_item']]
            for row in rows:
                assert state_digest(env)==row['physical_before']['state_hash']
                historical=lookup[(task['task_id'],row['step'])]
                harm='proposal_avoids_immediate_terminal_failure' in historical['local_dimensions']
                positive=bool(historical['actual_advantages'])
                if harm or positive:
                    c=historical_controller(row,observer.consequences)
                    proposal=row['decision']['decision']['proposed_action']
                    serialized=json.loads(json.dumps(c.to_dict()))
                    action=c.choose(row['observation'],proposal)
                    recovered=Controller18.from_dict(serialized)
                    assert recovered.choose(row['observation'],proposal)==action
                    assert recovered.to_dict()==c.to_dict()
                    audit=c.audit18
                    assert audit['transaction']['attempt_history_unchanged'] and audit['transaction']['failures_unchanged']
                    assert c.exploration_spent-serialized['exploration_spent']==int(bool(audit['transaction']['executed_probe']))
                    if not audit['transaction']['executed_probe']:
                        assert c.pending_probe is None and c.explore_pending is None
                        assert c.trials==serialized['trials'] and c.probes==serialized['probes']
                    prng,nrng=random.getstate(),np.random.get_state()
                    clone=restore(snapshot(env))
                    obs,reward,done,info=clone.step({AGENT_ID:action});clone.update_scores(reward)
                    after=physical(clone,target)
                    kb=Knowledge.from_dict(dict(facts=row['public_knowledge_before']))
                    delta=kb.observe(obs[AGENT_ID],action)
                    failed=bool(done or getattr(reward[AGENT_ID],'death',False) or after['health']<=0)
                    random.setstate(prng);np.random.set_state(nrng)
                    record=dict(task_id=task['task_id'],step=row['step'],before_hash=row['physical_before']['state_hash'],
                        kind='verified_terminal_harm' if harm else 'positive_controller_control',
                        old_action=row['action'],proposal=proposal,new_action=action,audit=audit,
                        old_feedback=row['feedback'],new_feedback=obs[AGENT_ID],new_physical_after=after,
                        old_advantages=historical['actual_advantages'],new_knowledge_delta=delta,
                        new_terminal_failure=failed,originally_harmful=harm,source='one-step native branch; no alternate episode')
                    if harm:assert not failed, (task['task_id'],action,obs[AGENT_ID])
                    # Preserve the tested positive dimension, not necessarily the
                    # exact action or a wastefully large amount of material.
                    retained=[];lost=[]
                    for advantage in historical['actual_advantages']:
                        ok=True
                        if advantage=='actual_extra_closure_relation':
                            extra=set(row['knowledge_delta']['new_relations'])-set(historical['alternate']['knowledge_delta']['new_relations'])
                            ok=extra.issubset(set(delta['new_relations']))
                        elif advantage=='actual_extra_closure_production':
                            extra=set(historical['actual_gains']['production'])-set(historical['alternate']['gains']['production'])
                            ok=all(after['crafted'].get(n,0)>row['physical_before']['crafted'].get(n,0) for n in extra)
                        elif advantage=='actual_extra_relevant_material_type':
                            extra=set(historical['actual_gains']['material_gains'])-set(historical['alternate']['gains']['material_gains'])
                            ok=all(after['possessed'].get(n,0)>row['physical_before']['possessed'].get(n,0) for n in extra)
                        elif advantage=='actual_avoids_immediate_terminal_failure':ok=not failed
                        elif advantage=='actual_preserves_more_health':ok=after['health']>=row['physical_after']['health']
                        elif advantage=='actual_more_target_owned_after_craft':ok=after['target_owned']>=row['physical_after']['target_owned']
                        (retained if ok else lost).append(advantage)
                    # Acquisition of an extra type can be a positive CF label
                    # even when the type is ALREADY owned above known demand.
                    # Keep that loss visible; acceptance permits precisely a
                    # surplus clip that preserves possession and releases hands.
                    surplus_clip=False
                    if lost==['actual_extra_relevant_material_type']:
                        from scar_v3.state import parse_action
                        p=parse_action(action)
                        logs=[v for v in audit['acquisition_decisions'] if v['item']==p.target]
                        surplus_clip=bool(p.verb=='store' and logs and all(
                            v['demand'] is not None and v['owned']['lower_bound']>=v['demand'] for v in logs)
                            and after['health']>=row['physical_after']['health']
                            and all(after['possessed'].get(n,0)>=v for n,v in row['physical_before']['possessed'].items()))
                    record.update(positive_dimensions_retained=retained,positive_dimensions_lost=lost,
                        explicit_surplus_acquisition_tradeoff=surplus_clip)
                    branches.append(record)
                # Sole observer ingests actual historical public transitions.
                observer.observe(row['observation'],row['action'],row['feedback'])
                obs,reward,done,info=env.step({AGENT_ID:row['action']});env.update_scores(reward)
                assert state_digest(env)==row['state_hash'] and obs[AGENT_ID]==row['feedback']
                factual_steps+=1
            if len(integration)<2 and task['game_name'] not in {r['game'] for r in integration}:
                # Real agent factory and checkpoint contract with a capture-only
                # provider at an old state; no new episode rollout.
                provider=MockProvider()
                with contextlib.redirect_stdout(io.StringIO()):
                    agent=make_method('SCAR18',task['game_name'],provider,task['objective_text'],task['target_item'],history,path/'agent')
                    obs0=rows[0]['observation']
                    action,*_=agent.act(obs0)
                    cp=path/'cp';agent.save_memory(str(cp))
                    other=make_method('SCAR18',task['game_name'],MockProvider(),task['objective_text'],task['target_item'],history,path/'other')
                    other.load_memory(str(cp))
                assert len(provider.calls)==1 and len(agent.short_term_memory)<=5
                assert agent.controller.to_dict()==other.controller.to_dict()
                summary=agent.decision['fact_summary']
                assert len(summary['records'])<=48 and summary['characters']<=6000
                assert all(json.dumps(r,ensure_ascii=False,separators=(',',':')) in provider.calls[0]['system'] for r in summary['records'])
                assert agent.controller.choose(obs0,'wait')==other.controller.choose(obs0,'wait')
                integration.append(dict(game=task['game_name'],action=action,one_mock_request=True,
                    checkpoint_equivalent=True,summary_characters=summary['characters'],summary_records=len(summary['records']),
                    public_knowledge_in_actual_request=True,api_calls=0))
        print(task['task_id'],'historical replay and selected local branches checked',flush=True)
    harms=[r for r in branches if r['originally_harmful']]
    lost=[dict(task_id=r['task_id'],step=r['step'],dimensions=r['positive_dimensions_lost'],
        explicit_surplus_acquisition_tradeoff=r['explicit_surplus_acquisition_tradeoff']) for r in branches if r['positive_dimensions_lost']]
    gzip_rows(RESULTS/f'preflight_branches_{args.site}.jsonl.gz',branches)
    receipt=dict(passed=len(harms)==6 and all(r['explicit_surplus_acquisition_tradeoff'] for r in lost),unit_tests=result.testsRun,api_calls=0,network_guard=True,
        historical_replay_steps=factual_steps,one_step_branches=len(branches),
        terminal_harm_states=len(harms),terminal_harms_avoided=sum(not r['new_terminal_failure'] for r in harms),
        positive_states=sum(r['kind']=='positive_controller_control' for r in branches),positive_dimensions_lost=lost,
        integration=integration,source_hashes={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'scar_stage18').rglob('*.py')},
        scope='engineering acceptance only; not new full-episode success rates')
    write(RESULTS/f'preflight_{args.site}.json',receipt)
    assert receipt['passed'], lost
    print(json.dumps(receipt,ensure_ascii=False))


if __name__=='__main__':main()
