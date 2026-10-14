"""Verify derived source references, completeness and response anomaly accounting."""
from collections import Counter
from .common import *
from .analyze import data,accepted

def main():
    offline();entries=rows(RESULTS/'evidence_index.jsonl.gz');pairs=read(RESULTS/'paired_comparison.json');review=read(RESULTS/'semantic_review.json')
    assert len(entries)==3116 and len(review)==len(pairs)==10
    keyed={(e['id'],e['variant'],e['step']):e for e in entries};assert len(keyed)==len(entries)
    cases=[];anomalies=[];requests=[];all_attempts=[]
    for pair in pairs:
        ident=pair['id']
        for variant in ['OriginalRecovery','OracleGoalStack']:
            s,rr,qq,source,lines=data(ident,variant);source_hash=sha(source)
            assert len(rr)==300-s['step'] and rr[-1]['step']==300
            assert pair['variants'][variant]['actions']==len(rr)
            for r in rr:
                e=keyed[ident,variant,r['step']];prop=r['decision']['attempts'][-1]['proposal']
                assert e['line']==lines[r['step']] and e['source']==str(source.relative_to(ROOT)) and e['source_sha256']==source_hash
                assert e['action']==r['action']==prop['action'] and e['reasoning']==prop['reasoning']
                assert e['accepted']==bool(accepted(r)) and e['state_hash']==r['state_hash']
                assert not e['action_overridden']
                assert e['request_ids']==[q['request_id'] for q in qq if q['step']==r['step']]
            if variant=='OracleGoalStack':
                requests.extend(qq);all_attempts.extend(a for r in rr for a in r['decision']['attempts'])
                for q in qq:
                    if not q.get('parse_exception'):continue
                    content=q['raw_response']['choices'][0]['message']['content'];reason=None
                    try:json.loads(content)
                    except json.JSONDecodeError as exc:reason=dict(error=exc.msg,offset=exc.pos,near=content[max(0,exc.pos-90):exc.pos+90])
                    assert reason is not None
                    r=next(r for r in rr if r['step']==q['step'])
                    anomalies.append(dict(id=ident,step=q['step'],ordinal=q['ordinal'],request_id=q['request_id'],
                        finish_reason=q['raw_response']['choices'][0]['finish_reason'],parse_error=reason,
                        final_action=r['action'],native_attempts=len(r['decision']['attempts']),
                        resolution='unchanged native AGC-v2 syntax repair; no manual edit or experiment resampling'))
            cases.append(dict(id=ident,variant=variant,actions=len(rr),source_index_verified=True))
        note=next(r for r in review if r['id']==ident)
        for field,variant in [('evidence','OracleGoalStack'),('baseline_evidence','OriginalRecovery')]:
            _,rr,qq,source,lines=data(ident,variant);by={r['step']:r for r in rr}
            for text,e in note[field].items():
                r=by[int(text)];assert e['observation']==r['observation'] and e['feedback']==r['feedback']
                assert e['proposal']==r['decision']['attempts'][-1]['proposal']
    assert len(requests)==1716 and len(anomalies)==5
    hard=[a for a in all_attempts if not a.get('executed') and a.get('hard')]
    soft=[a for a in all_attempts if not a.get('executed') and not a.get('hard')]
    write(RESULTS/'response_anomalies.json',dict(total_requests=len(requests),statuses=dict(Counter(q['status'] for q in requests)),
        finish_reasons=dict(Counter(q['raw_response']['choices'][0]['finish_reason'] for q in requests)),json_anomalies=anomalies,
        hard_native_repair_attempts=len(hard),soft_native_reconsideration_attempts=len(soft),
        max_prompt_tokens=max(q['usage']['prompt_tokens'] for q in requests),
        unknown_billing=0,manual_response_repairs=0,rerun_branches=0))
    write(RESULTS/'analysis_verification.json',dict(passed=True,source_action_references=len(entries),semantic_case_evidence_verified=10,
        cases=cases,new_model_calls=0,all_model_proposals_executed_without_override=True))
    print(json.dumps(dict(passed=True,actions=len(entries),anomalies=len(anomalies),hard=len(hard),soft=len(soft))))

if __name__=='__main__':main()
