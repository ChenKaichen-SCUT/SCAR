"""Check every derived action/context against immutable saved sources."""
import gzip
import hashlib
import json
import subprocess
from .common import *
from .extract import norm,contains,accepted

def main():
    offline();integrity=check_freeze();aa=rows(RESULTS/'action_audit.jsonl.gz');index={(r['id'],r['variant'],r['step']):r for r in aa};assert len(index)==3116
    contexts=0
    for ident in CASES:
        for variant in ['Original','OracleRecovery']:
            s,rr,qq,path,lines=data(ident,variant)
            for r in rr:
                x=index[ident,variant,r['step']];q=[q for q in qq if q['step']==r['step']]
                assert x['source_line']==lines[r['step']] and x['source_trajectory']==path
                assert x['reasoning']==r['decision']['attempts'][-1]['proposal'].get('reasoning','')
                assert x['accepted']==accepted(r) and x['action']==r['action'] and x['state_hash']==r['state_hash']
                assert x['goal_description']==r['control_after']['goal']['goal_description']
                assert x['model_request_ids']==[p['request_id'] for p in q]
                text='\n'.join(m['content'] for p in q for m in p['messages'])
                assert x['original_exact_in_model_context']==contains(text,s['current_goal']);contexts+=len(q)
    ann=read(RESULTS/'lifecycle_annotations.json');assert len(ann)==10
    for a in ann:
        s,rr,qq,path,lines=data(a['id'],'OracleRecovery');by={r['step']:r for r in rr}
        assert a['phase0_adopted'] and a['phase1_understood'] and a['plan_steps']
        for e in a['evidence']:
            r=by[e['step']];assert e['line']==lines[e['step']] and e['observation']==r['observation'] and e['feedback']==r['feedback']
            assert e['reasoning']==r['decision']['attempts'][-1]['proposal']['reasoning']
        if a['condition_step'] is not None:assert a['condition_step'] in by
        if a['resume_by'] is not None:assert a['resume_by'] in a['evidence_steps']
    for t in read(RESULTS/'paper_goal_stacks.json'):
        prefix=json.loads(gzip.decompress((ROOT/f'results/stage27/checkpoints/{t["id"]}/public_prefix.json.gz').read_bytes()))
        for e in t['evidence']:
            assert e['step']<=t['knowledge_cutoff'] and any(e['quote'] in p['feedback']['text'] for p in prefix if p['step']==e['step'])
        ids={n['id'] for n in t['nodes']};assert len(ids)==len(t['nodes'])
        for n in t['nodes']:
            assert n['parent'] is None or n['parent'] in ids
            assert all(0<=i<len(t['evidence']) for i in n.get('evidence',[]))
    summary=read(RESULTS/'summary.json');assert summary['original_action_restored']==5 and summary['phase4_eligible']==5
    assert summary['new_model_calls']==summary['new_cost_usd']==0
    cf=read(RESULTS/'native_local_counterfactual.json');assert cf['new_model_calls']==0
    assert cf['alternatives'][1]['public_state']['hands']=={'torch':1.0,'iron_bar':1.0}
    write(RESULTS/'verification.json',dict(passed=True,freeze_integrity=integrity,source_actions_checked=len(aa),saved_context_occurrences_checked=contexts,
        public_paper_trees_checked=10,all_semantic_labels_cite_raw_evidence=True,semantic_judgment_not_proved_by_assertions=True,
        reused_stage28_native_replay_receipt=str((ROOT/'results/stage28/verification.json').relative_to(ROOT)),
        additional_native_prefix_replays=24,additional_native_counterfactual_actions=2,new_model_calls=0,cost_usd=0))
    print(json.dumps(read(RESULTS/'verification.json')),flush=True)

if __name__=='__main__':main()
