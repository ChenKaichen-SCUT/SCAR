"""Check the final diagnostic package against frozen, original evidence."""
import csv
import re
from pathlib import Path
from .common import *
from .native import differences


def main():
    forbid_network();integrity=check_freeze()
    from scar.io import digest
    expected={'Stage18-Fixed':300,'ShortTermMemoryAgent':224,'LongContextAgent':300}
    total=0;native_total=0
    for method in METHODS:
        original=rows(source(method)/'trajectory.jsonl.gz')
        agent=rows(RESULTS/'agent_audit'/f'{method}.jsonl.gz')
        public=rows(RESULTS/'step_audit'/f'{method}.jsonl.gz')
        native=rows(RESULTS/'native'/f'{method}.jsonl.gz')
        initial=read(RESULTS/'native'/f'{method}.initial.json')
        receipt=read(RESULTS/'agent_audit'/f'{method}.receipt.json')
        assert receipt['exact_contexts']==receipt['exact_actions']==300
        assert receipt['exact_saved_final_memory'] and receipt['save_load_roundtrip_exact']
        assert len(agent)==len(public)==len(original)==300
        assert len(native)==expected[method]
        history=[]
        for n,(o,a,p) in enumerate(zip(original,agent,public),1):
            assert o['step']==a['step']==p['step']==n
            assert o['action']==a['selected_action']==p['selected_action']
            assert o['observation']==a['observation']==p['observation']
            assert o['feedback']==a['feedback']==p['feedback']
            assert o['scores']==a['scores']==p['scores']
            assert a['history_actions']==p['history_actions']==history
            assert p['hidden_world_available']==(n<=len(native))
            assert p['public_world_delta']==differences(p['public_before'],p['public_after'])
            if n>1:assert agent[n-2]['internal_after']==a['internal_before']
            history.append(o['action']);total+=1
        before=initial
        for n,r in enumerate(native,1):
            assert r['step']==n and r['after_hash']==original[n-1]['state_hash']
            assert r['before_hash']==original[n-1]['state_hash_before']
            assert digest(r['physical_after'])==r['stored_frame_digest']
            assert r['world_delta']==differences(before,r['physical_after'])
            assert public[n-1]['native_world_delta']==r['world_delta']
            before=r['physical_after'];native_total+=1
    with (RESULTS/'evidence_index.csv').open() as f:assert len(list(csv.DictReader(f)))==900
    with (RESULTS/'step_ledger.csv').open() as f:ledger=list(csv.DictReader(f))
    assert len(ledger)==900
    for method in METHODS:
        original=rows(source(method)/'trajectory.jsonl.gz')
        for row in [r for r in ledger if r['method']==method]:
            o=original[int(row['step'])-1]
            assert json.loads(row['observation_json'])==o['observation']
            assert json.loads(row['feedback_json'])==o['feedback']
    q=rows(RESULTS/'request_audit.jsonl.gz');assert len(q)==900
    assert all(r['observation_complete'] and r['saved_history_included'] for r in q)
    sc=rows(RESULTS/'agent_audit'/'Stage18-Fixed.jsonl.gz')
    w=rows(RESULTS/'public_recovery_witnesses.jsonl.gz')
    assert [r['start_before_action'] for r in w]==read(RESULTS/'protocol.json')['manual_witness_steps']
    for r in w:
        assert r['clone_initial_hash']==r['actual_before_hash']==sc[r['start_before_action']-1]['original_state_hash_before']
        assert r['branch_actions']==len(r['actions']) and r['first_stage_reward_gained']
        assert r['within_original_budget']==(r['branch_actions']<=301-r['start_before_action'])
        last=r['actual_before_hash']
        for n,a in enumerate(r['actions'],1):
            assert a['before_hash']==last and a['index']==n and a['public_basis']
            last=a['after_hash']
        assert r['new_quest_reward']==1 and not r['full_main_quest_complete']
    assert sum(r['within_original_budget'] for r in w)==6
    cf=rows(RESULTS/'mark_controller_contrasts.jsonl.gz')
    assert len(cf)==sum(r['decision']['intercepted'] for r in sc)==214
    assert {r['step'] for r in cf if r['proposal_additional_public_disclosures']}=={33,35}
    for r in cf:
        a=sc[r['step']-1]
        assert r['same_state_hash']==a['original_state_hash_before'] and r['actual_feedback']==a['feedback']
    c=read(RESULTS/'classification.json')
    assert len(c['A_steps'])==96 and len(c['B_steps'])==141
    assert set(c['A_steps']).isdisjoint(c['B_steps'])
    assert set(c['A_steps'])|set(c['B_steps'])==set(range(64,301))
    assert len(c['B_saved_but_not_in_prompt_steps'])==87 and len(c['C_not_obtained_core_facts'])==6
    assert sc[63]['internal_before']['controller']['target']=='enter hall'
    assert 'Craft an oak rod.' in sc[63]['observation']['text']
    assert sc[67]['decision']['stage18']['assessments']['llm']['status']=='UNKNOWN'
    assert sc[67]['internal_after']['controller']['decision10']['reason']=='no_public_candidate'
    assert all(r['internal_before']['controller']['exploration_spent']==0 and not r['internal_before']['controller']['queue'] for r in sc)
    eng=read(RESULTS/'engineering_checks.json');assert eng['passed'] and len(eng['reproductions'])==14
    conclusion=read(RESULTS/'diagnostic_conclusion.json')
    assert conclusion['verdict']=='DESIGN_LIMIT' and not conclusion['proceed_to_500_steps']
    assert conclusion['native_verified_steps']==native_total==824
    assert conclusion['manual_witness_actions']==43
    assert conclusion['new_model_requests']==conclusion['new_model_tokens']==conclusion['new_model_cost_usd']==0
    assert not conclusion['algorithm_changes'] and not conclusion['patches'] and not conclusion['patched_ab_runs']
    reports=list(REPORTS.glob('*.md'));assert len(reports)==7
    expected_outputs={RESULTS/'verification.json',RESULTS/'artifact_manifest.json'}
    links=0
    for path in reports:
        for link in re.findall(r'\]\(([^)]+)\)',path.read_text()):
            if '://' in link:continue
            target=link.split('#')[0]
            if not target:continue
            target=(path.parent/target).resolve()
            assert target.exists() or target in expected_outputs,(path.name,link)
            links+=1
    # Scan only newly produced files, including decompressed raw evidence.
    # Never print a matching secret if validation fails.
    suspect=re.compile(rb'(?:sk-[A-Za-z0-9_-]{20,}|Authorization\s*:\s*Bearer\s+[A-Za-z0-9_.-]{16,})')
    scan_files=0
    for directory in (RESULTS,REPORTS,ROOT/'scar_stage22b'):
        for path in directory.rglob('*'):
            if not path.is_file() or '__pycache__' in str(path):continue
            if path.suffix in {'.png','.pdf'}:continue
            if path.suffix=='.gz':
                with gzip.open(path,'rb') as f:
                    assert not any(suspect.search(line) for line in f),f'Sensitive pattern detected in {path.name}'
            else:assert not suspect.search(path.read_bytes()),f'Sensitive pattern detected in {path.name}'
            scan_files+=1
    receipt=dict(passed=True,original_evidence_linked_steps=total,native_immutable_frames=native_total,
        independent_delta_checks=native_total+total,evidence_index_rows=900,report_local_links_valid=links,
        native_witnesses=7,native_witness_actions=43,within_budget_first_stage_witnesses=6,
        same_state_original_overrides_checked=214,engineering_reproductions=14,
        new_model_requests=0,new_model_cost_usd=0,secret_pattern_scan_files=scan_files,
        frozen_files_check=integrity,source_files={str(p.relative_to(ROOT)):sha(p) for p in sorted((ROOT/'scar_stage22b').glob('*.py'))})
    write(RESULTS/'verification.json',receipt)
    manifest={str(p.relative_to(ROOT)):dict(sha256=sha(p),bytes=p.stat().st_size)
              for base in (ROOT/'scar_stage22b',RESULTS,REPORTS) for p in sorted(base.rglob('*'))
              if p.is_file() and '__pycache__' not in str(p) and p.name!='artifact_manifest.json'}
    write(RESULTS/'artifact_manifest.json',dict(files=manifest,scope='Generated implementation, reports, and analysis evidence only; excludes downloaded engine/dependencies and this manifest itself'))
    print(json.dumps(receipt),flush=True)


if __name__=='__main__':main()
