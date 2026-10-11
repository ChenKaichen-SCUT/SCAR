"""Re-index all 89 frozen families with action/state evidence, without API calls."""
import gzip
import json
from collections import Counter
from pathlib import Path
from scar.io import atomic_json
from scar_v3.state import parse_action


def main():
    root = Path('results/v3/attribution')
    old = json.loads((root/'case_classifications.json').read_text())
    cases = {c['id']:c for c in json.loads(Path('results/v3/dataset/cases.json').read_text())}
    with gzip.open(root/'audits.jsonl.gz','rt') as f:
        audits = {r['case_id']:r for r in map(json.loads,f)}
    rows = []
    for case in old:
        ident = case['case_id']; original = cases[ident]
        seq = case['sequences']['SCARV3Agent']; evidence = []
        transfers = {}
        for step in seq:
            p = parse_action(step['actual'])
            if p.verb in {'drop','pick up','store','take out'}:
                previous = transfers.setdefault(p.target,[])
                previous.append({'index':step['index'],'action':step['actual'],'rejected':step['rejected']})
            if step['actual'] != step['proposed']:
                evidence.append({'kind':'base_action_replaced','index':step['index'],
                    'proposed':step['proposed'],'actual':step['actual'],
                    'strength':'direct_action_record; harmfulness requires counterfactual'})
        for item, actions in transfers.items():
            if len(actions) >= 4:
                evidence.append({'kind':'repeated_resource_transfer','item':item,'actions':actions,
                    'strength':'direct_repetition; not automatically a pointless cycle'})
        for row in audits[ident]['rows']:
            if row.get('revisit_count',0):
                evidence.append({'kind':'physical_revisit','index':row['index'],
                    'physical_key':row['physical_key'],'state_digest':row['state_digest'],
                    'strength':'direct_evaluator_state; information gain not excluded'})
        witnesses = {'original_executed_witness':original['witness'],
                     'state_hash':original['state_hash'], 'source':'results/v3/dataset/cases.json#'+ident,
                     'verified':original['validated']}
        rows.append({'case_id':ident,'family':case['family'],'comparison_group':case['group'],
            'target_action':case['target_action'],'goal':original['goal'],
            'direct_evidence':evidence,'prior_graded_evidence':case['causes'],
            'initial_conditions':case['initial_blockers'],
            'hypotheses_to_test':['missing_intermediate_dependencies','failure_to_preserve_materials',
                'container_access_or_capacity','premature_plan_invalidation','scope_of_preconditions'],
            'dynamic_goal_switch_evidence':None,
            'hypothesis_status':'Not causal attribution: paired outcomes alone do not identify mechanism',
            'all_method_action_sequences':case['sequences'],'recovery_witness':witnesses,
            'audit_source':f'results/v3/attribution/audits.jsonl.gz#{ident}',
            'counterfactual_source':f'results/v3/attribution/branches.jsonl.gz#{ident}',
            'narrative_source':'reports/v3/机制级归因分析.md#9'} )
    atomic_json('results/sequence/old_family_audit.json',rows)
    atomic_json('results/sequence/old_audit_summary.json',{'families':len(rows),
        'groups':dict(Counter(r['comparison_group'] for r in rows)),
        'api_calls':0,'classification':'evidence table + explicitly unconfirmed causal hypotheses'})

if __name__ == '__main__':
    main()
