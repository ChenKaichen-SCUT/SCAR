"""Independent native replay and accounting/provenance verification process."""
from .common import *
deny_network()
import re
import subprocess
import tempfile
from collections import Counter,defaultdict
from datetime import datetime,timezone
from scar.environment import AGENT_ID,restore,snapshot,state_digest
from scar_stage17.environment import create_initial
from scar_stage14.knowledge import Knowledge
from scar.io import digest
from scar_v3.state import PublicState,parse_action
from scar_stage20.evidence import check


def native_verify(spec,expected,data):
    with tempfile.TemporaryDirectory(prefix='scar20audit-verify-',dir=RUNTIME) as directory:
        env=restore(data,Path(directory));assert state_digest(env)==spec['state_hash']==expected['initial_state_hash']
        assert env.obs[AGENT_ID]==expected['before_observation']
        out,reward,done,info=env.step({AGENT_ID:spec['action']});env.update_scores(reward)
        assert out[AGENT_ID]==expected['after_observation'] and state_digest(env)==expected['final_state_hash']
        assert bool(done)==expected['done'] and info==expected['info']
        assert {k:vars(v) for k,v in reward.items()}==expected['reward']
        assert expected['steps']==1 and expected['model_calls']==expected['tokens']==expected['cost_usd']==0
        before=PublicState.observe(expected['before_observation']);after=PublicState.observe(expected['after_observation'])
        assert after.feedback==expected['feedback']
        reject=bool(info.get('step_invalid_action',{}).get(AGENT_ID,False)) or bool(re.search(r'Cannot |Invalid ',after.feedback))
        assert not reject==expected['native_action_accepted']


def main():
    protected=load(RESULTS/'protected_manifest.json')
    assert protected['base_commit']==BASE
    for p,h in protected['files'].items():assert sha(ROOT/p)==h,p
    ledger=ROOT/'runtime/stage20/budget.sqlite'
    assert sha(ledger)==protected['runtime_ledger_sha256']
    engine=Path(os.environ['AGENTODYSSEY_ROOT']);freeze=load(SOURCE/'freeze.json')
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=engine,text=True).strip()==freeze['engine_commit']
    assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=engine,text=True).strip()
    plans=read_gzip(RESULTS/'planning_states.jsonl.gz');terminals=read_gzip(RESULTS/'terminal_states.jsonl.gz')
    summary=load(RESULTS/'summary.json');rejects=load(RESULTS/'rejection_audit.json');stalls=load(RESULTS/'stall_audit.json')
    intents=load(RESULTS/'intent_audit.json');crafts=load(RESULTS/'craft_proposal_audit.json')
    branches={b['id']:b for b in read_gzip(RESULTS/'counterfactual_results.jsonl.gz')};specs=load(RESULTS/'counterfactual_plan.json')
    tests=load(RESULTS/'test_receipt.json');assert tests['passed'] and tests['negative_controls']==264 and tests['false_acceptances']==0
    controls=load(RESULTS/'negative_controls.json');assert len(controls)==264 and all(c['rejected'] for c in controls)
    assert Counter(c['mutation'] for c in controls)==dict.fromkeys(('unknown_entry','unreachable_logged_entry','known_locked_only_route','unknown_target','unknown_ID','future_ID'),44)
    tasks={t['task_id']:t for t in load(SOURCE/'tasks.json')};traces={tid:read_gzip(folder(tid)/'trajectory.jsonl.gz') for tid in tasks}
    request_lookup={q['request_id']:q for tid in tasks for q in read_gzip(folder(tid)/'requests.jsonl.gz')}
    assert len(plans)==len(request_lookup)==191 and {p['request_id'] for p in plans}==set(request_lookup)
    for p in plans:
        q=request_lookup[p['request_id']];proposal=p['plan']['proposal'];c=controller(p['controller'])
        assert q['parsed']==proposal and q['step']==p['decision_step'] and q['ordinal']==p['ordinal']
        assert q['signature']==p['request_signature']
        prompt=q['messages'][-1]['content'];literal=[json.loads(s) for s in prompt.split('PUBLIC EVIDENCE (cite IDs):\n',1)[1].splitlines()]
        assert literal==p['plan']['evidence_snapshot']['records']
        assert check(c,proposal)[0]==p['old_evidence_reason']
        for ident in proposal['evidence_ids']:
            rec=c.evidence20[ident];assert rec['observed_step']<=c.table.state['step'] and rec['first_seen_step']<=c.table.state['step']
        n=p['decision_step']-1;rows=traces[p['task_id']]
        assert p['physical_state_hash']==(rows[n]['physical_before']['state_hash'] if n<len(rows) else rows[-1]['state_hash'])
    expected_rejects={p['id'] for p in plans if p['old_evidence_reason']=='evidence_unrelated_to_execution_entry'}
    assert len(expected_rejects)==44 and {p['id'] for p in rejects}==expected_rejects
    assert {k:sum(r['shadow']['category']==k for r in rejects) for k in ('I','II','III','IV')}==summary['rejection_counts']
    assert len(stalls)==len(terminals)==11
    for s in stalls:
        state=next(t for t in terminals if t['task_id']==s['task_id']);rows=traces[s['task_id']]
        raw=load(folder(s['task_id'])/'terminal_decision.json')
        assert raw['decision']['controller']==state['controller'] and raw['public_observation']==state['public_observation']
        assert len(rows)==s['steps'] and s['remaining_actions']==100-len(rows)
        assert state['physical_state_hash']==rows[-1]['state_hash']
        assert state['candidates']==s['candidates']
        assert all(r['action']==rows[r['step']-1]['action'] and r['feedback']==rows[r['step']-1]['mechanism_outcome']['feedback'] for r in s['last_15_actions'])
        for r in s['relevant_evidence']:
            row=rows[r['step']-1];assert set(r['new_related_relations'])<=set(row['knowledge_delta']['new_relations'])
            assert set(r['new_related_relations'])<=set(s['public_dependencies'])
        assert s['categories']['C']==(s['exploration_spent']==18 and bool(s['relevant_evidence']) and bool(s['positive_native_witnesses']))
        assert s['categories']['D']==bool(s['direct_D_witnesses'])
        for ident in s['direct_D_witnesses']:
            p=next(p for p in plans if p['id']==ident)
            assert p['plan']['acceptance']['reason']=='not_a_current_dependency_or_blocker' and p['shadow']['category']=='II'
    assert {k:sum(s['categories'][k] is True for s in stalls) for k in ('A','B','C','D')}==summary['stall_counts']
    original_intents={(r['task_id'],r['id']):r for r in load(SOURCE/'subgoal_outcomes.json')}
    assert len(intents)==61 and Counter(i['type'] for i in intents)=={'LOCATE_PRECONDITION':59,'ACQUIRE_MATERIAL':2}
    for i in intents:
        source=original_intents[i['task_id'],i['intent_id']]
        for k in ('type','target','entry','status','termination_reason','start_step','end_step','steps'):assert i[k]==source[k]
        assert [(r['step'],r['action']) for r in i['timeline']]==[(r['step'],r['action']) for r in source['actions']]
        for r in i['timeline']:
            row=traces[i['task_id']][r['step']-1]
            assert r['feedback']==row['mechanism_outcome']['feedback'] and r['new_relations']==row['knowledge_delta']['new_relations']
        f=i['first_failure_node']
        if f:
            assert i['status']!='completed' and f['event'] in i['lifecycle']
            early=next(e for e in i['lifecycle'] if e['event'] in ('blocked','execution_blocked','expired','cancelled'))
            assert f['event']==early and f['first_observable_node']==early['step']
        for r in i['parent_attempts']:
            row=traces[i['task_id']][r['step']-1];action=parse_action(row['action'])
            assert action.verb=='craft' and action.target==i['parent'] and r['success']==bool(row['metrics']['actual_production'])
    assert len(crafts)==2 and not any(c['acceptance']['accepted'] for c in crafts)
    # Independently rerun the exact SAME archived one-step branches for hashes;
    # no new candidate and no policy choose/act is called in this phase.
    by_task=defaultdict(list);verified=0;factual=0;prefixes=[]
    for spec in specs:
        expected=branches[spec['id']]
        if spec['source']=='terminal_public_candidate':
            terminal=next(t for t in terminals if t['task_id']==spec['task_id']);cp=ROOT/spec['checkpoint']
            assert sha(cp/'physical.pkl')==terminal['checkpoint_pickle_sha256'] and sha(cp/'meta.json')==terminal['checkpoint_meta_sha256']
            native_verify(spec,expected,(cp/'physical.pkl').read_bytes());verified+=1
        else:by_task[spec['task_id']].append(spec)
    for tid,items in by_task.items():
        task=tasks[tid];last=max(s['at_completed_step'] for s in items)
        with tempfile.TemporaryDirectory(prefix='scar20audit-verify-prefix-',dir=RUNTIME) as directory:
            env,history=create_initial(task['game_name'],task['initial_seed'],Path(directory))
            assert state_digest(env)==task['initial_state_hash'] and digest(history)==task['initial_public_history_hash']
            for n in range(last+1):
                data=snapshot(env)
                for spec in items:
                    if spec['at_completed_step']==n:
                        native_verify(spec,branches[spec['id']],data);verified+=1;env=restore(data,Path(directory)/'resume')
                if n==last:break
                row=traces[tid][n];assert state_digest(env)==row['physical_before']['state_hash']
                out,reward,done,info=env.step({AGENT_ID:row['action']});env.update_scores(reward);factual+=1
                assert state_digest(env)==row['state_hash'] and out[AGENT_ID]==row['feedback']
            prefixes.append(dict(task_id=tid,factual_actions=last,tutorial_actions=len(history)))
    assert verified==len(branches)==len(specs)==37
    assert Counter(b['native_action_accepted'] for b in branches.values())=={True:34,False:3}
    assert sha(RESULTS/'counterfactual_plan.json')==load(RESULTS/'counterfactual_receipt.json')['selection_plan_sha256']
    assert all(b['factual_same_before_hash'] for b in load(RESULTS/'branch_analysis.json'))
    for p,h in protected['files'].items():assert sha(ROOT/p)==h,p
    assert sha(ledger)==protected['runtime_ledger_sha256'] and not NETWORK_ATTEMPTS
    assert len(list(REPORTS.glob('*.md')))>=5
    published=[p for d in (ROOT/'scar_stage20_audit',RESULTS,REPORTS) for p in d.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc']
    for p in published:
        data=gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes()
        assert not re.search(rb'(?i)Bearer\s+sk-[A-Za-z0-9_-]{16,}',data),str(p)
        assert not re.search(rb'\bsk-[A-Za-z0-9_-]{24,}\b',data),str(p)
        assert p.stat().st_size<100*1024*1024,str(p)
    receipt=dict(passed=True,verified_at_utc=datetime.now(timezone.utc).isoformat(),independent_process=True,
        network_disabled=True,network_attempts=0,new_model_calls=0,new_embedding_calls=0,tokens=0,cost_usd=0,
        protected_historical_files=len(protected['files']),private_formal_cost_ledger_unchanged=True,
        original_planning_requests_verified=191,stalled_states_verified=11,rejections_verified=44,intents_verified=61,craft_proposals_verified=2,
        repeated_same_native_branch_verifications=verified,additional_unique_counterfactuals=0,
        repeated_factual_prefix_actions=factual,repeated_prefixes=prefixes,full_closed_loop_runs=0,policy_decisions_executed_in_verifier=0,
        engine_commit=freeze['engine_commit'],secrets_pattern_scan_passed=True,research_decision=summary['research_decision'])
    write(RESULTS/'verification.json',receipt)
    write(RESULTS/'research_state.json',dict(phase='complete_verified',model_calls=0,tokens=0,cost_usd=0,old_files_unchanged=True,stage21_not_developed=True,
        research_decision=summary['research_decision'],no_further_experiments=True))
    published += [RESULTS/'verification.json',RESULTS/'research_state.json']
    write(RESULTS/'artifact_manifest.json',dict(files={str(p.relative_to(ROOT)):sha(p) for p in sorted(set(published)) if p.name!='artifact_manifest.json'},
        excludes=['manifest itself','downloaded dependencies','private runtime and native checkpoints','credentials']))
    print(json.dumps(receipt,ensure_ascii=False))


if __name__=='__main__':main()
