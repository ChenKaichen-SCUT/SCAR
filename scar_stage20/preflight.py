"""No-network engineering gate using archived replies/states, never new samples."""
import copy
from collections import Counter
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from .common import ROOT, RESULTS, load, write, read_gzip, gzip_rows, sha, deny_network
from .controller import Controller20
from .evidence import snapshot
from .planning import parse_response, InterfaceError
from .agent import make_method
from .run_errors import MethodStalled
from .tests.test_mechanisms import CaptureProvider


def historical_controller(row, after=False):
    c=Controller20.from_dict(row['decision']['controller'] if after else row['decision']['decision']['controller_before'])
    for name in list(c.__dict__):
        if name.endswith('19'):del c.__dict__[name]
    if after:c.observe(row['observation'],row['action'],row['feedback'])
    else:c.table.observe(row['observation'])
    return c


def legacy_adapter(raw,c,observation):
    """Offline migration witness, not the formal parser or a guessed model ID.

    Old requests did not contain evidence IDs. Rebind the *named entry* only to
    an actually public snapshot record, preserving type/target/entry/direction.
    Old quoted claims are discarded, never asserted. Decision gates still apply.
    This measures migration potential, not new-model JSON success or causality.
    """
    text=raw.strip()
    if text.startswith('```json\n') and text.endswith('```'):text=text[8:-3].strip()
    try:p=json.loads(text)
    except json.JSONDecodeError as exc:return dict(schema_restored=False,accepted=False,reason='invalid_JSON',detail=str(exc))
    if not isinstance(p,dict):return dict(schema_restored=False,accepted=False,reason='not_object')
    records=snapshot(c,observation)
    refs=[r for r in records if r['kind'] not in ('goal','blocker') and p.get('entry') in r['names']]
    if not refs:return dict(schema_restored=False,accepted=False,reason='no_public_evidence_binding_for_entry')
    candidate={k:v for k,v in p.items() if k not in ('public_evidence','completion')}
    candidate['evidence_ids']=[refs[0]['id']]
    try:parsed,events=parse_response(json.dumps(candidate))
    except InterfaceError as exc:return dict(schema_restored=False,accepted=False,reason=exc.category,detail=str(exc))
    for key in ('type','target','entry','direction'):assert parsed[key]==p[key]
    result=c.accept(parsed)
    return dict(schema_restored=True,accepted=result['accepted'],reason=result['reason'],
        rebound_public_record=refs[0],proposal=parsed,normalizations=events,
        acceptance=result,legacy_quoted_claims_promoted=False,
        scope='offline public-entry rebinding; not an observed new-model response')


def interface_regression():
    evidence=[];negative_checks=0
    expected={r['request_id']:r for r in load(ROOT/'results/stage19/response_errors.json')}
    for task in load(RESULTS/'tasks.json'):
        tid=task['task_id'];folder=ROOT/'results/stage19/runs'/f'{tid}__SCAR19'
        rows=read_gzip(folder/'trajectory.jsonl.gz');requests=read_gzip(folder/'requests.jsonl.gz')
        for request in requests:
            step=request['step'];row=rows[min(step,len(rows))-1]
            rejection=row['decision']['decision']['subgoal_acceptance'] if step<=len(rows) else None
            group='invalid_response' if request['status']!='ok' else ('exact_quote_rejection'
                if rejection and rejection['reason']=='evidence_not_quoted_from_public_prompt' else None)
            if group is None:continue
            c=historical_controller(row,after=step>len(rows));obs=row['observation'] if step<=len(rows) else row['feedback']
            c.blocker20=dict(kind='missing_target_recipe',item=task['target_item'])
            # Restore the original concrete blocker when it exists; translating
            # the broad Stage19 gap does not import any evaluator knowledge.
            if step<=len(rows) and row['decision']['decision'].get('planning_trigger'):
                c.blocker20=copy.deepcopy(row['decision']['decision']['planning_trigger'])
            raw=request['raw_response']['choices'][0]['message']['content']
            converted=legacy_adapter(raw,c,obs)
            evidence.append(dict(task_id=tid,request_id=request['request_id'],step=step,group=group,
                old_cause=expected.get(request['request_id'],{}).get('offline_detail'),**converted))
            if converted['schema_restored']:
                c.intent20=None;c.acceptance20=[]
                forged=copy.deepcopy(converted['proposal']);forged['target']='unobserved_invented_object_xyz'
                assert c.accept(forged)['reason']=='target_not_publicly_named';negative_checks+=1
                forged=copy.deepcopy(converted['proposal']);forged['evidence_ids']=['Edoes_not_exist']
                assert c.accept(forged)['reason']=='unknown_evidence_id';negative_checks+=1
    assert sum(r['group']=='invalid_response' for r in evidence)==72
    assert sum(r['group']=='exact_quote_rejection' for r in evidence)==69
    gzip_rows(RESULTS/'interface_regression.jsonl.gz',evidence)
    summary={g:dict(total=sum(r['group']==g for r in evidence),
        schema_restored=sum(r['group']==g and r['schema_restored'] for r in evidence),
        public_decision_accepted=sum(r['group']==g and r['accepted'] for r in evidence),
        reasons=dict(Counter(r['reason'] for r in evidence if r['group']==g))) for g in ('invalid_response','exact_quote_rejection')}
    conflicts=[r for r in evidence if r.get('old_cause')=='Completion does not match subgoal type']
    summary['completion_conflicts']=dict(total=len(conflicts),schema_restored=sum(r['schema_restored'] for r in conflicts),
        public_decision_accepted=sum(r['accepted'] for r in conflicts))
    summary.update(negative_mutations_rejected=negative_checks,wrong_acceptances_in_negative_controls=0,
        caveat='Old logs have no IDs. Controlled public-entry rebinding is separately labeled, never sold as direct parsing of nonexistent historical IDs. Native path feasibility does not prove exploration hypothesis utility.')
    write(RESULTS/'interface_regression.json',summary)
    return summary


def main():
    deny_network()
    suite=unittest.defaultTestLoader.discover(str(ROOT/'scar_stage20/tests'))
    result=unittest.TextTestRunner(verbosity=2).run(suite);assert result.wasSuccessful()
    interfaces=interface_regression()
    from scar.environment import AGENT_ID, snapshot as native_snapshot, restore, state_digest
    from scar_stage17.environment import create_initial
    from scar_stage17.evaluate import physical
    cases=[];stalls=[];factual=0;native_branches=0;restore_checks=0
    tasks=load(RESULTS/'tasks.json')
    for task in tasks:
        tid=task['task_id'];folder=ROOT/'results/stage19/runs'/f'{tid}__SCAR19'
        summary=load(folder/'summary.json');rows=read_gzip(folder/'trajectory.jsonl.gz')
        stagnation=task['target_item'] in ('oil_bomb','ruin_spear')
        if not summary['success'] and not stagnation:continue
        selected={r['step'] for r in rows if r['success'] or r['metrics']['craft_failed'] or r['metrics']['actual_production']}
        if stagnation:selected={next(r['step'] for r in rows if r['action']=='wait')}
        with tempfile.TemporaryDirectory(prefix='scar20-preflight-') as directory:
            root=Path(directory)
            with contextlib.redirect_stdout(io.StringIO()):env,history=create_initial(task['game_name'],task['initial_seed'],root/'initial')
            assert state_digest(env)==task['initial_state_hash']
            for row in rows:
                assert state_digest(env)==row['physical_before']['state_hash']
                if row['step'] in selected:
                    c=historical_controller(row);saved=copy.deepcopy(c.to_dict())
                    recovered=Controller20.from_dict(json.loads(json.dumps(saved)))
                    action=c.choose(row['observation']);assert action==recovered.choose(row['observation'])
                    assert c.to_dict()==recovered.to_dict();restore_checks+=1
                    case=dict(task_id=tid,step=row['step'],old_action=row['action'],new_action=action,
                        blocker=c.blocker20,old_state_hash=state_digest(env),goal_preserved=c.target=='craft 1 '+task['target_item'])
                    if action:
                        branch=restore(native_snapshot(env));out,reward,done,info=branch.step({AGENT_ID:action});branch.update_scores(reward)
                        c.observe(row['observation'],action,out[AGENT_ID]);native_branches+=1
                        case.update(feedback=out[AGENT_ID],state_hash=state_digest(branch))
                        if row['success']:
                            target=branch.world.auxiliary['obj_name_to_id'][task['target_item']]
                            assert physical(branch,target)['target_owned']>=task['target_amount']
                    if row['success']:assert action is not None
                    cases.append(case)
                    if stagnation:
                        provider=CaptureProvider(fail=True)
                        with contextlib.redirect_stdout(io.StringIO()):
                            agent=make_method('SCAR20',task['game_name'],provider,task['objective_text'],task['target_item'],history,root/'agent')
                        provider.agent=agent;agent.controller=Controller20.from_dict(saved)
                        branch=restore(native_snapshot(env),root/'branch',agent=agent);steps=[];status='bounded_branch_limit'
                        for index in range(6):
                            before=copy.deepcopy(branch.obs[AGENT_ID])
                            try:action,*_=agent.act(before)
                            except MethodStalled:status='method_stalled';break
                            assert action!='wait'
                            out,reward,done,info=branch.step({AGENT_ID:action});branch.update_scores(reward)
                            agent.observe_transition(before,action,out[AGENT_ID]);native_branches+=1
                            steps.append(dict(action=action,feedback=out[AGENT_ID],state_hash=state_digest(branch)))
                            if done or bool(getattr(reward[AGENT_ID],'death',0)):status='native_failure';break
                        assert len(provider.calls)<=12
                        stalls.append(dict(task_id=tid,start_step=row['step'],steps=steps,branch_status=status,
                            mock_failed_logical_requests=len(provider.calls),no_purposeless_wait=True,task_level_recovery_not_claimed=True))
                        break
                out,reward,done,info=env.step({AGENT_ID:row['action']});env.update_scores(reward);factual+=1
                assert state_digest(env)==row['state_hash'] and out[AGENT_ID]==row['feedback']
            # Full Agent JSON checkpoint contract, no provider execution.
            provider=CaptureProvider(fail=True)
            with contextlib.redirect_stdout(io.StringIO()):
                a=make_method('SCAR20',task['game_name'],provider,task['objective_text'],task['target_item'],history,root/'a')
                b=make_method('SCAR20',task['game_name'],provider,task['objective_text'],task['target_item'],history,root/'b')
            a.controller=c;a.save_memory(root/'saved');b.load_memory(root/'saved')
            assert a.controller.to_dict()==b.controller.to_dict();restore_checks+=1
    assert len(stalls)==2 and len({c['task_id'] for c in cases})==14
    gzip_rows(RESULTS/'preflight_branches.jsonl.gz',cases);write(RESULTS/'stagnation_regression.json',stalls)
    receipt=dict(passed=True,unit_tests=result.testsRun,api_calls=0,network_disabled=True,
        historical_factual_steps=factual,selected_states=len(cases),native_branch_actions=native_branches,
        old_success_tasks_checked=12,stagnation_states_checked=2,serialization_checks=restore_checks,
        interfaces=interfaces,source_hashes={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'scar_stage20').rglob('*.py')},
        scope='Engineering fixtures and short branches only; not formal task scores or new model sampling')
    write(RESULTS/'preflight_local.json',receipt)
    print(json.dumps({k:v for k,v in receipt.items() if k!='source_hashes'},ensure_ascii=False))


if __name__=='__main__':main()
